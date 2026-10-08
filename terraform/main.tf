terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # Required for reading EKS OIDC certificate thumbprint (used in IRSA)
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Using local backend for Pluralsight sandbox
  # State file saved locally on the EC2 instance running Terraform
}

provider "aws" {
  region = var.aws_region
}
