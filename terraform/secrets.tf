# ── AWS SECRETS MANAGER ───────────────────────────────────────────────────────
# Replaces your .env file and secret.yaml — no credentials stored in files
# Your Flask app reads these at runtime via IRSA (no AWS keys needed in pods)
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.project_name}/app-secrets"
  description             = "App config and credentials for GenAI Study Coach"
  recovery_window_in_days = 0

  tags = { Name = "${var.project_name}-secrets" }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id

  secret_string = jsonencode({
    AWS_REGION     = var.aws_region
    MODEL_ID       = "anthropic.claude-3-sonnet-20240229-v1:0"
    SECRET_KEY     = "genai-study-coach-secret-2024"
  })
}
