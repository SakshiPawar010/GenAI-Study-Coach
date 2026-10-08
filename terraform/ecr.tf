# ── ECR REPOSITORY ────────────────────────────────────────────────────────────
# Private Docker registry — Jenkins pushes here, EKS pulls from here
resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  # DevSecOps: automatically scan every pushed image for vulnerabilities
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = var.project_name }
}

# ── LIFECYCLE POLICY ──────────────────────────────────────────────────────────
# Keep only last 10 images — older ones are deleted automatically to save cost
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
