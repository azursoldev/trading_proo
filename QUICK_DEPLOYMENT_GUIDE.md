# 🚀 Quick Azure Deployment Guide

## ⚡ **5-Minute Deployment to Azure**

### **Step 1: Create Azure Web App**
1. Go to **https://portal.azure.com**
2. Click **"Create a resource"** → **"Web App"**
3. Fill in these details:
   - **Name**: `trading-pro-app` (this becomes your URL)
   - **Resource Group**: Create new `trading-pro-rg`
   - **Runtime Stack**: `Python 3.11`
   - **Operating System**: `Linux`
   - **Region**: `East US`
   - **Pricing Plan**: `B1 (Basic) - $13/month`
4. Click **"Review + create"** → **"Create"**

### **Step 2: Deploy Your Code**
1. After Web App is created, go to **"Deployment Center"**
2. Choose **"ZIP Deploy"**
3. Upload the file: `trading-pro-deploy.zip`
4. Click **"Deploy"**

### **Step 3: Configure Settings**
1. Go to **"Configuration"** → **"Application settings"**
2. Add these settings:

| Name | Value |
|------|-------|
| `SECRET_KEY` | `django-insecure-vjkw1a)_d6!ru96#3^&p8rcll6!tkwrgcqdo7w!qmz421(h1mn` |
| `DEBUG` | `False` |
| `WEBSITES_ENABLE_APP_SERVICE_STORAGE` | `true` |

### **Step 4: Set Startup Command**
1. Go to **"Configuration"** → **"General settings"**
2. Set **Startup Command**: `gunicorn trading_project.wsgi:application --bind 0.0.0.0:8000`

### **Step 5: Test Your App**
1. Go to: `https://trading-pro-app.azurewebsites.net`
2. You should see your Trading Pro application!

---

**🎉 That's it! Your app will be live in 5 minutes!**
