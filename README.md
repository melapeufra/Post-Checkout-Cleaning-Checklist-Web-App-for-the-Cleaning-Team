# Post-Checkout-Cleaning-Checklist-Web-App-for-the-Cleaning-Team
A bilingual (French 🇫🇷 / Ukrainian 🇺🇦) Flask-based web app that allows the cleaning team to complete a structured post-checkout checklist for Neybor houses by uploading pictures before and after.
I first started with google form, and then got inspired: https://docs.google.com/forms/d/e/1FAIpQLSd-7EjwkE6XWHTYjP0yhdyWn4zt3Q-l38EV9MpS9wFyAIy-kA/viewform?usp=dialog

---

## Features

- Structured checklist per room (Bedrooms 1-4, Kitchen, Dishes, Oven, Microwave, Shower, Toilet)
- Photo upload (before/after) per section + extra photo/comment
- Stores submissions in **SQLite** (no external DB needed)
- Optional **Google Drive** upload for all photos (via Service Account)
- (Optional) Map pin via Leaflet — can be disabled
- Admin page to review submissions with image previews or Drive links
- Sleek pink UI (Bootstrap 5 + custom CSS)

---

## Project Structure


---

## Requirements

- Python 3.10+ (tested with 3.11)
- Windows PowerShell, macOS Terminal, or Linux shell

---

## Quick Start
### 1) Clone and enter the project
```
# if you already have the folder, skip cloning and cd into it
git clone <your-repo-url> neybor-cleaning-checklist
cd neybor-cleaning-checklist
```
---
## Create virtual env and install deps
## Windows (PowerShell):
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## macOS / Linux:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
---
## Configure environment
```
cp .env.example .env

SECRET_KEY=change-this
ADMIN_TOKEN=choose-a-strong-token
FLASK_ENV=development
# Optional Drive (see “Google Drive uploads” below)
# GOOGLE_APPLICATION_CREDENTIALS=service-account.json
# DRIVE_FOLDER_ID=xxxxxxxxxxxxxxxxxxxxxxxxx

```

---
## Run the server
```
# Windows PowerShell
. .\.venv\Scripts\Activate.ps1
python -m flask run --port 5050

# macOS / Linux
source .venv/bin/activate
python -m flask run --port 5050
```
---
Open: http://127.0.0.1:5050

Admin page: http://127.0.0.1:5050/admin?token=YOUR_ADMIN_TOKEN

---

## Google Drive Uploads (optional)
Upload each photo to a Drive folder instead of (or in addition to) local uploads/.
In Google Cloud Console:
Create a project, enable Google Drive API.
Create a Service Account, generate a JSON key → save as service-account.json at project root.
In Google Drive:
Create a folder for uploads, copy its Folder ID from the URL.
Share this folder with the Service Account email (Editor access).
Add the following to .env:
```
GOOGLE_APPLICATION_CREDENTIALS=service-account.json
DRIVE_FOLDER_ID=YOUR_FOLDER_ID
```
---
## Troubleshooting

PowerShell refuses to activate .venv:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\.venv\Scripts\Activate.ps1
```

To make it persistent for your user:
```
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

“ModuleNotFoundError: No module named 'dotenv' / 'flask'”
Your venv isn’t active or deps not installed. Activate and reinstall:
```
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

“Could not locate a Flask application”
Set the app module before running:
```
$env:FLASK_APP="app.py"
python -m flask run --port 5050
```

Port already in use
Run on another port:
```
python -m flask run --port 5051
```
---
## Deployment Notes (optional)

Any provider that supports Python/Flask works: Fly.io, Railway, Render, etc.

Use a production WSGI server (e.g., gunicorn) behind a reverse proxy.

Persist or externalize storage:

Keep SQLite on a persistent volume or migrate to PostgreSQL.

For images, prefer Google Drive or object storage (S3/GCS).
---
## Scripts (copy/paste)

Windows (PowerShell) quick run:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
cd "C:\path\to\neybor-cleaning-checklist"
. .\.venv\Scripts\Activate.ps1
$env:FLASK_APP="app.py"
$env:FLASK_ENV="development"
python -m flask run --port 5050
```

macOS/Linux quick run:
```
cd /path/to/neybor-cleaning-checklist
source .venv/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=development
python -m flask run --port 5050
```
---
## License

MIT. See LICENSE.
---
## Acknowledgements

Flask, Jinja2, Bootstrap 5

Optional: Leaflet (if you keep location)

Google Drive API (optional uploads)
