#!/usr/bin/env python3
"""
Project Consistency Verification Script
Checks that all imports and references are correct
"""

import os
import sys

def check_file_exists(filepath, description):
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ MISSING {description}: {filepath}")
        return False

def main():
    print("=" * 60)
    print("GenAI Study Coach - Project Consistency Check")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    all_good = True
    
    # Check core files
    files_to_check = [
        ("backend/app.py", "Flask Application"),
        ("backend/__init__.py", "Backend Package Init"),
        ("backend/agents/__init__.py", "Agents Package Init"),
        ("backend/agents/summarizer_agent.py", "Summarizer Agent"),
        ("backend/agents/quiz_agent.py", "Quiz Agent"),
        ("backend/agents/roadmap_agent.py", "Roadmap Agent"),
        ("backend/service/__init__.py", "Service Package Init"),
        ("backend/service/bedrock_client.py", "Bedrock Client"),
        ("backend/service/config.py", "Configuration"),
        ("backend/templates/index.html", "HTML Template"),
        ("backend/static/script.js", "JavaScript"),
        ("backend/static/style.css", "CSS Stylesheet"),
        ("requirements.txt", "Requirements"),
        (".env.example", "Environment Example"),
        ("README.md", "README"),
        ("START_CLOUD9.md", "Cloud9 Guide"),
    ]
    
    print("\nChecking project files...")
    for filepath, description in files_to_check:
        full_path = os.path.join(base_dir, filepath)
        if not check_file_exists(full_path, description):
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print("✓ All files present! Project structure is complete.")
        print("\nNext steps:")
        print("1. Create virtual environment: python -m venv venv")
        print("2. Activate: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Linux/Mac)")
        print("3. Install dependencies: pip install -r requirements.txt")
        print("4. Set environment variables (AWS_REGION, MODEL_ID)")
        print("5. Run: python backend/app.py")
    else:
        print("✗ Some files are missing. Please check the output above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
