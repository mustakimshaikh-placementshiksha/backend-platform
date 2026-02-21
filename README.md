# 🏆 Backend Django Online Judge — Complete Setup Guide

> **Project by:** Mustakim Shaikh (mustakim.shaikh@placementshiksha.com)  
> **Stack:** Django 4.2 · Django REST Framework · PostgreSQL · Redis · drf-yasg (Swagger)

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & Architecture](#2-tech-stack--architecture)
3. [Folder Structure](#3-folder-structure)
4. [Prerequisites](#4-prerequisites)
5. [Step-by-Step: Run Locally (First Time)](#5-step-by-step-run-locally-first-time)
6. [Step-by-Step: Run Every Time After Setup](#6-step-by-step-run-every-time-after-setup)
7. [API Endpoints & Swagger UI](#7-api-endpoints--swagger-ui)
8. [Key Settings & Configuration](#8-key-settings--configuration)
9. [Common Issues & Fixes](#9-common-issues--fixes)
10. [Django Management Commands](#10-django-management-commands)

---

## 1. Project Overview

This is a **full-featured Online Judge backend** (like Codeforces / LeetCode) built with Django. It handles:

- 👤 **User accounts** – register, login, profile, 2FA, API keys
- 📢 **Announcements** – system-wide public announcements
- 🧩 **Problems** – create/edit/delete coding problems with test cases
- 🏅 **Contests** – create time-bound competitive contests
- 📤 **Submissions** – submit code, track results (Accepted, Wrong Answer, etc.)
- ⚙️ **System Config** – judge server setup, SMTP, site settings
- 📘 **Swagger UI** – interactive API documentation at `/swagger/`

---

## 2. Tech Stack & Architecture

| Layer | Technology |
|-------|------------|
| **Web Framework** | Django 4.2.28 |
| **REST API** | Django REST Framework 3.14 |
| **Database** | PostgreSQL 14 |
| **Cache / Sessions** | Redis 6+ |
| **Task Queue** | Dramatiq (via Redis broker) |
| **API Docs** | drf-yasg (Swagger / ReDoc) |
| **Auth** | Custom `AbstractBaseUser` + Session + API Key |
| **Python** | 3.10.x |

### Architecture Flow

```
Client (Browser / Mobile)
        │
        ▼
Django Dev Server (port 8000)
        │
       ┌┴──────────────────────┐
       │  REST API Endpoints   │
       │  /api/account/        │
       │  /api/problem/        │
       │  /api/contest/        │
       │  /api/submission/     │
       │  /swagger/ (docs)     │
       └──────────┬────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
   PostgreSQL              Redis
   (user, problem,       (sessions,
    contest, etc.)        cache, tasks)
```

---

## 3. Folder Structure

```
Backend Django oj/
├── .venv/                      ← outer venv (Python 3.13, NOT used for project)
└── Onlinejudge/                ← main project root
    ├── manage.py               ← Django management entry point
    ├── requirements.txt        ← Python dependencies
    ├── SETUP_GUIDE.md          ← this file
    ├── init_db.sh              ← Docker-based DB init script (optional)
    ├── Dockerfile              ← for production Docker deployment
    │
    ├── venv/                   ← ✅ Project venv (Python 3.10) — USE THIS
    │
    ├── config/
    │   └── secret.key          ← Django SECRET_KEY (auto-generated)
    │
    ├── oj/                     ← Django project config
    │   ├── settings.py         ← Main settings (DB, Redis, apps, etc.)
    │   ├── urls.py             ← Root URL routing
    │   ├── wsgi.py
    │   └── dev_settings.py     ← Dev overrides (not used currently)
    │
    ├── account/                ← User auth, profile, 2FA, API keys
    ├── announcement/           ← System announcements
    ├── conf/                   ← Site configuration (SMTP, judge servers)
    ├── contest/                ← Contests
    ├── problem/                ← Problems + test cases
    ├── submission/             ← Code submissions + results
    ├── judge/                  ← Judge dispatcher
    ├── utils/                  ← Shared utilities, shortcuts
    ├── options/                ← Dynamic site options
    ├── fps/                    ← FPS problem import format
    ├── templates/              ← Custom HTML templates (Swagger overrides)
    ├── deploy/                 ← Production deployment (nginx, supervisord)
    ├── data/                   ← Runtime data (test cases, logs, uploads)
    └── public/                 ← Static files
```

---

## 4. Prerequisites

Make sure the following are installed on your Mac before starting:

| Tool | Check Command | Install |
|------|--------------|---------|
| **Python 3.10** | `python3.10 --version` | `brew install python@3.10` |
| **PostgreSQL 14** | `psql --version` | `brew install postgresql@14` |
| **Redis** | `redis-cli ping` | `brew install redis` |
| **pip** | `pip --version` | comes with Python |

---

## 5. Step-by-Step: Run Locally (First Time)

### Step 1 — Navigate to the project directory

```bash
cd "/Users/mustakimshaikh/Downloads/Backend Django oj/Onlinejudge"
```

---

### Step 2 — Start PostgreSQL and Redis services

```bash
# Start PostgreSQL
brew services start postgresql@14

# Start Redis
brew services start redis

# Verify both are running
brew services list
```

✅ Both should show **started** status.

---

### Step 3 — Create the PostgreSQL database and user (only needed once)

```bash
# Connect as the postgres superuser
psql -h 127.0.0.1 -U postgres

# Inside psql, run these commands:
CREATE USER onlinejudge WITH PASSWORD 'onlinejudge';
CREATE DATABASE onlinejudge OWNER onlinejudge;
GRANT ALL PRIVILEGES ON DATABASE onlinejudge TO onlinejudge;
\q
```

> **Note:** If the database already exists (as in this project), skip this step.

---

### Step 4 — Activate the project virtual environment

```bash
# Always use the venv INSIDE the Onlinejudge folder
source venv/bin/activate

# Verify Python version is 3.10
venv/bin/python3.10 --version
```

> ⚠️ **Important:** Use `venv/bin/python3.10` not just `python` — the venv has Python 3.10 with all packages installed.

---

### Step 5 — Install dependencies (if not already installed)

```bash
venv/bin/pip install -r requirements.txt
```

> If you see `psycopg2` errors, install: `brew install libpq` first.

---

### Step 6 — Generate a Secret Key (if config/secret.key is missing)

```bash
mkdir -p config
python3 -c "import secrets; print(secrets.token_hex(32))" > config/secret.key
```

---

### Step 7 — Run Database Migrations

```bash
venv/bin/python3.10 manage.py migrate
```

Expected output:
```
Django VERSION (4, 2, 28, 'final', 0)
Operations to perform:
  Apply all migrations: account, announcement, auth, ...
Running migrations:
  No migrations to apply.   ← or it runs pending ones
```

---

### Step 8 — Create a Super Admin User (first time only)

```bash
venv/bin/python3.10 manage.py inituser --username root --password rootroot --action create_super_admin
```

This creates a super admin user with:
- **Username:** `root`
- **Password:** `rootroot`

---

### Step 9 — Start the Django Development Server

```bash
venv/bin/python3.10 manage.py runserver 0.0.0.0:8000
```

You should see:
```
Django version 4.2.28, using settings 'oj.settings'
Starting development server at http://0.0.0.0:8000/
```

---

### Step 10 — Open in Browser

| Page | URL |
|------|-----|
| 📘 **Swagger UI** (interactive docs) | http://localhost:8000/swagger/ |
| 📄 **ReDoc** (clean docs) | http://localhost:8000/redoc/ |
| 🔑 **Login API** | POST http://localhost:8000/api/account/login/ |
| Raw JSON schema | http://localhost:8000/swagger.json |

---

## 6. Step-by-Step: Run Every Time After Setup

Once the project is already set up, you only need these steps each time:

```bash
# 1. Go to project folder
cd "/Users/mustakimshaikh/Downloads/Backend Django oj/Onlinejudge"

# 2. Start services (if not already running)
brew services start postgresql@14
brew services start redis

# 3. Run the server
venv/bin/python3.10 manage.py runserver 0.0.0.0:8000

# 4. Open browser → http://localhost:8000/swagger/
```

That's it! 🎉

---

## 7. API Endpoints & Swagger UI

### Full Endpoint Map

| Group | Public URL | Admin URL |
|-------|-----------|-----------|
| **Account** | `/api/account/` | `/api/account/admin/` |
| **Announcement** | `/api/announcement/` | `/api/announcement/admin/` |
| **System Config** | `/api/conf/` | `/api/conf/admin/` |
| **Problems** | `/api/problem/` | `/api/problem/admin/` |
| **Contests** | `/api/contest/` | `/api/contest/admin/` |
| **Submissions** | `/api/submission/` | `/api/submission/admin/` |
| **Utils/Upload** | — | `/api/utils/admin/` |
| **Swagger UI** | `/swagger/` | — |
| **ReDoc** | `/redoc/` | — |

### How to Authenticate in Swagger

1. Go to http://localhost:8000/swagger/
2. Click **"Login to API"** button at the top
3. POST to `/api/account/login/` with:
   ```json
   { "username": "root", "password": "rootroot" }
   ```
4. Click **Authorize** (🔒) and enter your `sessionid` cookie value
5. Now you can use all endpoints from the Swagger UI

---

## 8. Key Settings & Configuration

All settings live in `oj/settings.py`. Key values:

| Setting | Value | Purpose |
|---------|-------|---------|
| `DEBUG` | `True` | Dev mode — shows full errors |
| `ALLOWED_HOSTS` | `["*"]` | Accepts all hosts for local dev |
| `SECRET_KEY` | from `config/secret.key` | Django encryption key |
| `DATABASES.HOST` | `127.0.0.1` | PostgreSQL host |
| `DATABASES.PORT` | `5432` | PostgreSQL port |
| `DATABASES.NAME` | `onlinejudge` | Database name |
| `DATABASES.USER` | `onlinejudge` | DB username |
| `DATABASES.PASSWORD` | `onlinejudge` | DB password |
| `REDIS_CONF.host` | `127.0.0.1` | Redis host |
| `REDIS_CONF.port` | `6379` | Redis port |
| `AUTH_USER_MODEL` | `account.User` | Custom user model |

---

## 9. Common Issues & Fixes

### ❌ `ModuleNotFoundError: No module named 'django'`

**Cause:** You're using the wrong Python / not inside the venv.

**Fix:**
```bash
# Always use the full path to venv Python
venv/bin/python3.10 manage.py runserver
```

---

### ❌ `psycopg2` connection error / `FATAL: role does not exist`

**Cause:** PostgreSQL is not running or the DB/user doesn't exist.

**Fix:**
```bash
# Restart PostgreSQL
brew services restart postgresql@14

# Check if it's accepting connections
pg_isready -h 127.0.0.1 -p 5432
```

---

### ❌ `Redis connection refused`

**Cause:** Redis is not running.

**Fix:**
```bash
brew services start redis
redis-cli ping   # should return PONG
```

---

### ❌ `FATAL: database "onlinejudge" does not exist`

**Fix:** Create the database (Step 3 above):
```bash
psql -U postgres -c "CREATE DATABASE onlinejudge OWNER onlinejudge;"
```

---

### ❌ Swagger shows blank or 500 error

**Cause:** Usually a missing or broken Redis/PostgreSQL connection.

**Fix:** Make sure both services are running, then restart the dev server.

---

### ❌ `Secret key file not found`

**Fix:**
```bash
mkdir -p config
python3 -c "import secrets; print(secrets.token_hex(32))" > config/secret.key
```

---

## 10. Django Management Commands

| Command | Purpose |
|---------|---------|
| `venv/bin/python3.10 manage.py check` | Verify config — no errors |
| `venv/bin/python3.10 manage.py migrate` | Apply DB migrations |
| `venv/bin/python3.10 manage.py makemigrations` | Create new migration files |
| `venv/bin/python3.10 manage.py runserver 0.0.0.0:8000` | Start dev server |
| `venv/bin/python3.10 manage.py shell` | Open Django Python shell |
| `venv/bin/python3.10 manage.py createsuperuser` | Create Django admin user |
| `venv/bin/python3.10 manage.py inituser --username root --password rootroot --action create_super_admin` | Create OJ super admin |
| `venv/bin/python3.10 manage.py test` | Run all tests |

---

## ✅ Quick Start Summary

```bash
# Navigate to project
cd "/Users/mustakimshaikh/Downloads/Backend Django oj/Onlinejudge"

# Start services
brew services start postgresql@14 && brew services start redis

# Run Django server
venv/bin/python3.10 manage.py runserver 0.0.0.0:8000

# Open Swagger UI in browser
open http://localhost:8000/swagger/
```

---

> 💡 **Pro Tip:** The project uses a custom **venv inside the Onlinejudge folder** with Python 3.10. Always use `venv/bin/python3.10` instead of the system `python3` to avoid package-not-found errors.
