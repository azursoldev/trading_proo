#!/bin/bash

# Trading Pro Azure App Service Startup Script
# This script runs when the Azure App Service starts

echo "🚀 Starting Trading Pro Application..."

# Set environment variables
export DJANGO_SETTINGS_MODULE=trading_project.settings_production

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --settings=trading_project.settings_production

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --settings=trading_project.settings_production

# Create superuser if it doesn't exist
echo "👤 Creating superuser..."
python manage.py shell --settings=trading_project.settings_production << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@tradingpro.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Start the application
echo "🌐 Starting Gunicorn server..."
gunicorn trading_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
