# 🚀 Trading Pro Azure Deployment Guide

This guide will help you deploy the Trading Pro application to Microsoft Azure using [Azure My Applications](https://myapplications.microsoft.com/).

## 📋 Prerequisites

1. **Azure Account**: Access to [Azure Portal](https://portal.azure.com)
2. **Azure CLI**: Install from [Microsoft Docs](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
3. **Git**: For version control
4. **Python 3.11**: For local development

## 🏗️ Azure Resources Required

- **App Service Plan**: B1 (Basic) tier minimum
- **Web App**: Linux-based Python 3.11
- **PostgreSQL Database**: Flexible Server
- **Storage Account**: For file uploads (optional)
- **Redis Cache**: For caching (optional)

## 🚀 Quick Deployment Steps

### Step 1: Prepare Your Environment

```bash
# Clone your repository
git clone <your-repo-url>
cd trading_pro

# Install Azure CLI (if not already installed)
# Windows: winget install Microsoft.AzureCLI
# macOS: brew install azure-cli
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login
```

### Step 2: Run Deployment Script

**For Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**For Linux/macOS (Bash):**
```bash
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Configure Environment Variables

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your App Service: `trading-pro-app`
3. Go to **Configuration** > **Application settings**
4. Add the following variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `SECRET_KEY` | `your-secret-key` | Django secret key |
| `DEBUG` | `False` | Production mode |
| `DATABASE_URL` | `postgresql://...` | Database connection string |
| `OPENAI_API_KEY` | `sk-...` | OpenAI API key |
| `IB_HOST` | `127.0.0.1` | Interactive Brokers host |
| `IB_PORT` | `7497` | Interactive Brokers port |
| `IB_CLIENT_ID` | `1` | Interactive Brokers client ID |

### Step 4: Deploy Your Code

**Option A: Using Azure DevOps (Recommended)**
1. Create a new Azure DevOps project
2. Upload the `azure-deploy.yml` pipeline
3. Configure the pipeline variables
4. Run the pipeline

**Option B: Using Azure CLI**
```bash
# Create deployment package
zip -r trading-pro.zip . -x "*.git*" "*.pyc" "__pycache__/*"

# Deploy to Azure
az webapp deployment source config-zip \
    --resource-group trading-pro-rg \
    --name trading-pro-app \
    --src trading-pro.zip
```

**Option C: Using Git Deployment**
```bash
# Add Azure remote
az webapp deployment source config \
    --resource-group trading-pro-rg \
    --name trading-pro-app \
    --repo-url https://github.com/yourusername/trading-pro.git \
    --branch main \
    --manual-integration
```

### Step 5: Run Database Migrations

1. Go to Azure Portal > App Service > SSH
2. Run the following commands:

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

## 🔧 Configuration Details

### Database Configuration

The application uses PostgreSQL on Azure. The connection string is automatically configured:

```python
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}
```

### Static Files

Static files are served using WhiteNoise:

```python
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### Security Settings

Production security settings are enabled:

- HTTPS redirect
- Secure cookies
- HSTS headers
- XSS protection
- Content type sniffing protection

## 📊 Monitoring and Logging

### Application Insights

1. Enable Application Insights in Azure Portal
2. Add the connection string to app settings
3. Monitor performance and errors

### Log Streaming

```bash
# Stream logs in real-time
az webapp log tail --resource-group trading-pro-rg --name trading-pro-app
```

## 🔄 CI/CD Pipeline

The `azure-deploy.yml` file provides a complete CI/CD pipeline:

1. **Build Stage**: Install dependencies, run tests, collect static files
2. **Deploy Stage**: Deploy to Azure App Service with environment variables

### Pipeline Variables

Configure these variables in Azure DevOps:

- `SECRET_KEY`: Django secret key
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key
- `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`: Interactive Brokers settings

## 🚨 Troubleshooting

### Common Issues

1. **Deployment Fails**
   - Check Python version (3.11 required)
   - Verify all dependencies in requirements.txt
   - Check build logs in Azure Portal

2. **Database Connection Issues**
   - Verify DATABASE_URL format
   - Check firewall rules for PostgreSQL
   - Ensure database server is running

3. **Static Files Not Loading**
   - Run `collectstatic` command
   - Check STATIC_ROOT setting
   - Verify WhiteNoise configuration

4. **Environment Variables Not Working**
   - Restart the app after adding variables
   - Check variable names (case-sensitive)
   - Verify no extra spaces in values

### Debug Mode

To enable debug mode temporarily:

1. Set `DEBUG=True` in app settings
2. Add your IP to `ALLOWED_HOSTS`
3. Restart the app

## 📈 Scaling

### Vertical Scaling

Upgrade your App Service plan:
- B1 → B2 → B3 (Basic)
- S1 → S2 → S3 (Standard)
- P1 → P2 → P3 (Premium)

### Horizontal Scaling

Enable auto-scaling:
1. Go to App Service > Scale out
2. Configure auto-scale rules
3. Set minimum/maximum instances

## 🔐 Security Best Practices

1. **Use Azure Key Vault** for sensitive data
2. **Enable Managed Identity** for Azure services
3. **Configure WAF** (Web Application Firewall)
4. **Regular security updates** for dependencies
5. **Monitor access logs** and failed attempts

## 📞 Support

- **Azure Documentation**: [docs.microsoft.com/azure](https://docs.microsoft.com/azure)
- **Django on Azure**: [docs.microsoft.com/azure/app-service/configure-language-python](https://docs.microsoft.com/azure/app-service/configure-language-python)
- **Trading Pro Issues**: Create an issue in the repository

## 🎯 Next Steps

After successful deployment:

1. **Test all functionality** on the live site
2. **Set up monitoring** and alerts
3. **Configure backup** for the database
4. **Set up SSL certificate** (Azure handles this automatically)
5. **Configure custom domain** (optional)

---

**🌐 Your Trading Pro application will be available at:**
`https://trading-pro-app.azurewebsites.net`

**🔑 Admin access:**
- Username: `admin`
- Password: `admin123` (change this immediately!)

---

*Happy Trading! 📈*
