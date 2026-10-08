#!/bin/bash

echo "============================================================"
echo "GenAI Study Coach - Quick Setup for Linux/Mac"
echo "============================================================"
echo ""

echo "[1/5] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    exit 1
fi

echo "[2/5] Activating virtual environment..."
source venv/bin/activate

echo "[3/5] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo "[4/5] Setting environment variables..."
export AWS_REGION=us-east-1
export MODEL_ID=anthropic.claude-sonnet-4-6
export AWS_ACCESS_KEY_ID=<your-access-key-id>
export AWS_SECRET_ACCESS_KEY=<your-secret-access-key>

echo "[5/5] Starting Flask application..."
echo ""
echo "============================================================"
echo "Application will start on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

python backend/app.py
