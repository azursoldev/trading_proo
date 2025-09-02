# 🚀 Manual Azure Deployment Steps

Since Azure CLI is not installed, follow these manual steps to deploy Trading Pro to Azure:

## 📋 Prerequisites
- Azure account with active subscription
- Access to Azure Portal (https://portal.azure.com)

## 🏗️ Step 1: Create Azure Resources

### 1.1 Create Resource Group
1. Go to https://portal.azure.com
2. Click "Create a resource" → "Resource group"
3. **Name**: `trading-pro-rg`
4. **Region**: `East US`
5. Click "Review + create" → "Create"

### 1.2 Create App Service Plan
1. Click "Create a resource" → "App Service Plan"
2. **Name**: `trading-pro-plan`
3. **Resource Group**: `trading-pro-rg`
4. **Operating System**: `Linux`
5. **Region**: `East US`
6. **Pricing Tier**: `B1 (Basic) - $13.14/month`
7. Click "Review + create" → "Create"

### 1.3 Create Web App
1. Click "Create a resource" → "Web App"
2. **Name**: `trading-pro-app` (this becomes your URL)
3. **Resource Group**: `trading-pro-rg`
4. **Runtime Stack**: `Python 3.11`
5. **Operating System**: `Linux`
6. **Region**: `East US`
7. **App Service Plan**: `trading-pro-plan`
8. Click "Review + create" → "Create"

### 1.4 Create PostgreSQL Database
1. Click "Create a resource" → "Azure Database for PostgreSQL"
2. Choose "Flexible server"
3. **Name**: `trading-pro-server`
4. **Resource Group**: `trading-pro-rg`
5. **Region**: `East US`
6. **Admin username**: `tradingadmin`
7. **Password**: Create a strong password (save this!)
8. **Compute + storage**: `Burstable, Standard_B1ms`
9. Click "Review + create" → "Create"

## ⚙️ Step 2: Configure Web App

### 2.1 Set Application Settings
1. Go to your Web App: `trading-pro-app`
2. Navigate to "Configuration" → "Application settings"
3. Add these settings:

| Name | Value | Description |
|------|-------|-------------|
| `SECRET_KEY` | `django-insecure-vjkw1a)_d6!ru96#3^&p8rcll6!tkwrgcqdo7w!qmz421(h1mn` | Django secret key |
| `DEBUG` | `False` | Production mode |
| `DATABASE_URL` | `postgresql://psql_admin:NqBHWBE9EhVltj16fjuq@newstradingapplication.postgres.database.azure.com:5432/postgres` | Database connection |
| `OPENAI_API_KEY` | `your-openai-api-key` | OpenAI API key (optional) |
| `IB_HOST` | `127.0.0.1` | Interactive Brokers host |
| `IB_PORT` | `7497` | Interactive Brokers port |
| `IB_CLIENT_ID` | `1` | Interactive Brokers client ID |

**Important**: Replace `YOUR_PASSWORD` with the actual password you created for the PostgreSQL database.

### 2.2 Configure Startup Command
1. In your Web App, go to "Configuration" → "General settings"
2. Set **Startup Command**: `gunicorn trading_project.wsgi:application --bind 0.0.0.0:8000`

## 📦 Step 3: Deploy Code

### 3.1 Upload Deployment Package
1. Go to your Web App: `trading-pro-app`
2. Navigate to "Deployment Center"
3. Choose "Local Git" or "ZIP Deploy"
4. Upload the `trading-pro-deploy.zip` file created earlier

### 3.2 Alternative: Use FTP
1. In your Web App, go to "Deployment Center"
2. Click "FTPS credentials" to get FTP details
3. Use an FTP client to upload all project files

## 🗄️ Step 4: Configure Database

### 4.1 Allow Azure Services
1. Go to your PostgreSQL server: `trading-pro-server`
2. Navigate to "Connection security"
3. Enable "Allow access to Azure services"
4. Add your IP address to firewall rules

### 4.2 Create Database
1. Go to your PostgreSQL server
2. Navigate to "Databases"
3. Click "Add database"
4. **Name**: `trading_pro_db`
5. Click "Save"

## 🚀 Step 5: Run Migrations

### 5.1 Access SSH
1. Go to your Web App: `trading-pro-app`
2. Navigate to "SSH" (in the left menu)
3. Click "Go" to open SSH console

### 5.2 Run Commands
```bash
# Activate virtual environment
source /home/site/wwwroot/antenv/bin/activate

# Run migrations
python manage.py migrate --settings=trading_project.settings_production

# Create superuser
python manage.py createsuperuser --settings=trading_project.settings_production

# Collect static files
python manage.py collectstatic --noinput --settings=trading_project.settings_production
```

## ✅ Step 6: Test Deployment

1. Go to your Web App URL: `https://trading-pro-app.azurewebsites.net`
2. You should see the Trading Pro home page
3. Test all functionality:
   - News dashboard
   - Market data
   - Tickers
   - IB connections
   - Trading signals
   - API subscribers

## 🔧 Troubleshooting

### Common Issues:

1. **502 Bad Gateway**
   - Check startup command is set correctly
   - Verify all environment variables are set
   - Check application logs in "Log stream"

2. **Database Connection Error**
   - Verify DATABASE_URL format
   - Check firewall rules for PostgreSQL
   - Ensure database server is running

3. **Static Files Not Loading**
   - Run collectstatic command via SSH
   - Check STATIC_ROOT setting

4. **Environment Variables Not Working**
   - Restart the app after adding variables
   - Check variable names (case-sensitive)

## 📊 Monitoring

1. **Application Logs**: Go to "Log stream" in your Web App
2. **Metrics**: Check "Metrics" for performance data
3. **Application Insights**: Enable for detailed monitoring

## 💰 Cost Estimation

- **App Service Plan (B1)**: ~$13/month
- **PostgreSQL (Standard_B1ms)**: ~$25/month
- **Total**: ~$38/month

## 🎯 Next Steps

After successful deployment:
1. Test all functionality
2. Set up monitoring and alerts
3. Configure custom domain (optional)
4. Set up automated backups
5. Configure SSL certificate (handled automatically by Azure)

---

**🌐 Your app will be available at:**
`https://trading-pro-app.azurewebsites.net`

**🔑 Admin access:**
- Username: `admin`
- Password: `admin123` (change this immediately!)

---

*Happy Trading! 📈*
