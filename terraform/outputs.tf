# ── OUTPUTS ───────────────────────────────────────────────────────────────────
# These values are printed after terraform apply
# You will need these to SSH into Jenkins, configure kubectl, and update Jenkinsfile

output "jenkins_public_ip" {
  description = "Public IP of Jenkins EC2 — use this to SSH and access Jenkins UI"
  value       = aws_instance.jenkins.public_ip
}

output "jenkins_url" {
  description = "Jenkins web UI URL"
  value       = "http://${aws_instance.jenkins.public_ip}:8080"
}

output "ecr_repository_url" {
  description = "ECR repository URL — put this in your Jenkinsfile as ECR_REGISTRY"
  value       = aws_ecr_repository.app.repository_url
}

output "eks_cluster_name" {
  description = "EKS cluster name — used in: aws eks update-kubeconfig --name <this>"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "app_bedrock_role_arn" {
  description = "IRSA role ARN — annotate your Kubernetes Service Account with this"
  value       = aws_iam_role.app_bedrock.arn
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN — used by app to fetch config at runtime"
  value       = aws_secretsmanager_secret.app_secrets.arn
}
