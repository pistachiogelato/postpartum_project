# Postpartum Emotional Management Platform Deployment Guide

## Project Overview
This is a support platform helping postpartum mothers and family members manage emotions and health status together. Through task allocation, emotion tracking, and health knowledge pushing, it creates a warm interactive space for postpartum families. The platform uses Google Gemini API for intelligent services.

## Environment Setup

### 1. Python Installation
1. Visit [Python Official Website](https://www.python.org/downloads/)
2. Download and install Python 3.9 or higher
3. Must check "Add Python to PATH" during installation

Verify installation: 

bash
python --version # Should display Python 3.9.x or higher

### 2. Proxy Setup (Required)
The project uses Google Gemini API and requires proxy settings.

#### For Windows:
1. Open Settings -> Network & Internet -> Proxy
2. Enable "Use a proxy server"
3. Address: 127.0.0.1
4. Port: 10809

#### For Mac/Linux:
Run in terminal:

bash
export HTTP_PROXY="http://127.0.0.1:10809"
export HTTPS_PROXY="http://127.0.0.1:10809"


### 3. Detailed Deployment Steps

1. **Download Project**
   - Download project zip file
   - Extract to any directory

2. **Create Virtual Environment**
   Open command line/terminal, navigate to project directory:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   If installation is slow, use alternative mirror:
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

4. **Configure Gemini API**
   - Create `.env` file in project root directory
   - Add following content (replace with your API key):
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Initialize Database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Start Project**
   ```bash
   python manage.py runserver
   ```
   Visit http://127.0.0.1:8000 in browser to see project homepage

## Troubleshooting

### 1. Dependency Installation Failure

bash
Try clearing pip cache and reinstalling
pip cache purge
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

### 2. Database Errors

bash
Delete old database and recreate
rm db.sqlite3
python manage.py makemigrations
python manage.py migrate


### 3. Proxy Connection Issues
- Ensure proxy software (e.g., V2Ray) is running
- Verify proxy port is correct
- Try alternative proxy ports

### 4. Missing Page Styles
- Check static directory structure:
  ```
  static/
  ├── css/
  ├── images/
  │   ├── bg.jpg
  │   └── feifei.png
  └── js/
  ```

## Project Structure

postpartum_project/
├── emotional_management/ # Main application directory
├── static/ # Static files directory
├── templates/ # Template files directory
├── .env # Environment variables
├── manage.py # Django management script
└── requirements.txt # Project dependencies


## Usage Guide

1. **Registration/Login**
   - First-time users need to register
   - Only one administrator (postpartum mother) per family
   - Login requires only nickname and family name

2. **Main Features**
   - Emotion Progress Bar: Administrator can adjust current emotional state
   - Daily Tasks: System automatically generates personalized tasks
   - Knowledge Cards: Daily health knowledge updates
   - Leaderboard: Shows family members' task completion status

## Important Notes
- Do not modify static directory structure
- Ensure proxy connection remains stable
- Recommend regular database backups
- Keep .env file and API key secure

## Technical Support
If deployment issues occur, check:
1. Python version correctness
2. Virtual environment activation
3. Complete dependency installation
4. Proper proxy configuration
5. Correct API key setup
