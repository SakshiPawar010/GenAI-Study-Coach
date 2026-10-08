# ── DYNAMIC AMI LOOKUP ────────────────────────────────────────────────────────
# Always fetches the latest Amazon Linux 2 AMI — works in any sandbox account
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# ── JENKINS SECURITY GROUP ────────────────────────────────────────────────────
resource "aws_security_group" "jenkins" {
  name        = "${var.project_name}-jenkins-sg"
  description = "Allow Jenkins UI and SSH access"
  vpc_id      = aws_vpc.main.id

  # Jenkins web UI
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Jenkins agent communication port
  ingress {
    from_port   = 50000
    to_port     = 50000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH — for EC2 Instance Connect from browser
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound — needed to pull images, call AWS APIs, etc.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-jenkins-sg" }
}

# ── JENKINS EC2 INSTANCE ──────────────────────────────────────────────────────
resource "aws_instance" "jenkins" {
  ami                    = data.aws_ami.amazon_linux_2.id
  instance_type          = var.ec2_instance_type
  subnet_id              = aws_subnet.public_a.id
  vpc_security_group_ids = [aws_security_group.jenkins.id]
  iam_instance_profile   = aws_iam_instance_profile.jenkins.name

  # Runs automatically on first boot
  # Installs all tools then starts Jenkins via docker-compose
  user_data = <<-EOF
#!/bin/bash
set -e

# Update system and install base tools
yum update -y
yum install -y docker unzip
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm -f kubectl

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

# Create jenkins working directory
mkdir -p /home/ec2-user/jenkins

# Write docker-compose.yml — no leading spaces so YAML parses correctly
cat > /home/ec2-user/jenkins/docker-compose.yml << 'COMPOSE'
version: '3.8'
services:
  jenkins:
    image: jenkins/jenkins:lts
    container_name: jenkins
    user: root
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker
      - /usr/local/bin/kubectl:/usr/local/bin/kubectl
      - /usr/local/bin/aws:/usr/local/bin/aws
      - /usr/local/aws-cli:/usr/local/aws-cli
      - /home/ec2-user/.kube:/root/.kube:ro
volumes:
  jenkins_home:
COMPOSE

chown -R ec2-user:ec2-user /home/ec2-user/jenkins

# Start Jenkins
cd /home/ec2-user/jenkins
docker-compose up -d
EOF

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  tags = { Name = "${var.project_name}-jenkins" }
}
