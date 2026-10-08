@echo off
echo ============================================================
echo GenAI Study Coach - Quick Setup for Windows
echo ============================================================
echo.

echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [4/5] Setting environment variables...
set AWS_REGION=us-east-1
set MODEL_ID=anthropic.claude-sonnet-4-6
set AWS_ACCESS_KEY_ID=<your-access-key>
set AWS_SECRET_ACCESS_KEY=<your-secret-key>

echo [5/5] Starting Flask application...
echo.
echo ============================================================
echo Application will start on http://localhost:5000
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python backend\app.py
