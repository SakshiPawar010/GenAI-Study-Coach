variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for naming all AWS resources"
  type        = string
  default     = "genai-study-coach"
}

variable "ec2_instance_type" {
  description = "EC2 instance type for Jenkins server"
  type        = string
  default     = "t3.medium"
}

variable "eks_node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t3.medium"
}

variable "eks_node_count" {
  description = "Number of worker nodes in EKS cluster"
  type        = number
  default     = 2
}

# AMI is fetched dynamically — always gets latest Amazon Linux 2 in any sandbox
# No hardcoded AMI ID needed
