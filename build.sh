#!/usr/bin/env bash
# ============================================================
# build.sh — Render build script
# Runs once during every deployment on Render
# ============================================================
set -o errexit   # exit on any error

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Creating runtime directories..."
mkdir -p test_case public/avatar public/upload data/log config

echo "🔑 Generating secret key if not present..."
if [ -z "$DJANGO_SECRET_KEY" ] && [ ! -f "config/secret.key" ]; then
    python -c "import secrets; print(secrets.token_hex(32))" > config/secret.key
    echo "   secret.key generated."
fi

echo "🗄️  Running database migrations..."
python manage.py migrate --no-input

echo "👤 Creating super admin user..."
python manage.py inituser \
    --username "${ADMIN_USERNAME:-root}" \
    --password "${ADMIN_PASSWORD:-rootroot}" \
    --action create_super_admin || echo "   Super admin already exists — skipped."

echo "📂 Collecting static files..."
python manage.py collectstatic --no-input 2>/dev/null || echo "   No static files to collect."

echo "✅ Build complete!"
