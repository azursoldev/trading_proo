# 🚀 Heroku Deployment Guide

## Quick Heroku Deployment (Free)

### Step 1: Create Heroku Account
1. Go to https://heroku.com
2. Sign up for free account
3. Install Heroku CLI

### Step 2: Deploy to Heroku
```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create trading-pro-app

# Deploy code
git add .
git commit -m "Deploy Trading Pro"
git push heroku main

# Set environment variables
heroku config:set SECRET_KEY="django-insecure-vjkw1a)_d6!ru96#3^&p8rcll6!tkwrgcqdo7w!qmz421(h1mn"
heroku config:set DEBUG=False

# Run migrations
heroku run python manage.py migrate
```

### Step 3: Access Your App
Your app will be available at: `https://trading-pro-app.herokuapp.com`
