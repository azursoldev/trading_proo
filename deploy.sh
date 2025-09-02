#!/bin/bash

# Trading Pro Azure Deployment Script
# This script helps deploy the Trading Pro application to Azure App Service

set -e

echo "🚀 Starting Trading Pro Azure Deployment..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in to Azure
if ! az account show &> /dev/null; then
    echo "🔐 Please log in to Azure CLI:"
    az login
fi

# Configuration variables
RESOURCE_GROUP="trading-pro-rg"
APP_NAME="trading-pro-app"
LOCATION="eastus"
PLAN_NAME="trading-pro-plan"
DATABASE_NAME="trading-pro-db"
DATABASE_SERVER="trading-pro-server"

echo "📋 Configuration:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   App Name: $APP_NAME"
echo "   Location: $LOCATION"
echo "   Database: $DATABASE_NAME"

# Create resource group
echo "🏗️  Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create App Service plan
echo "📦 Creating App Service plan..."
az appservice plan create \
    --name $PLAN_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku B1 \
    --is-linux

# Create PostgreSQL database
echo "🗄️  Creating PostgreSQL database..."
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $DATABASE_SERVER \
    --location $LOCATION \
    --admin-user tradingadmin \
    --admin-password $(openssl rand -base64 32) \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --public-access 0.0.0.0 \
    --storage-size 32

# Create database
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $DATABASE_SERVER \
    --database-name $DATABASE_NAME

# Create web app
echo "🌐 Creating web app..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $PLAN_NAME \
    --name $APP_NAME \
    --runtime "PYTHON|3.11"

# Configure app settings
echo "⚙️  Configuring app settings..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
        WEBSITES_ENABLE_APP_SERVICE_STORAGE=true \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
        ENABLE_ORYX_BUILD=true

# Get database connection string
echo "🔗 Getting database connection string..."
DB_CONNECTION_STRING=$(az postgres flexible-server show-connection-string \
    --server-name $DATABASE_SERVER \
    --admin-user tradingadmin \
    --admin-password $(az postgres flexible-server show \
        --resource-group $RESOURCE_GROUP \
        --name $DATABASE_SERVER \
        --query administratorLoginPassword -o tsv) \
    --database-name $DATABASE_NAME \
    --query connectionStrings.psql -o tsv)

# Set database URL
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings DATABASE_URL="$DB_CONNECTION_STRING"

echo "✅ Deployment configuration completed!"
echo ""
echo "📝 Next steps:"
echo "1. Set your environment variables in Azure Portal:"
echo "   - Go to https://portal.azure.com"
echo "   - Navigate to your App Service: $APP_NAME"
echo "   - Go to Configuration > Application settings"
echo "   - Add the following variables:"
echo "     * SECRET_KEY: $(openssl rand -base64 32)"
echo "     * OPENAI_API_KEY: your-openai-api-key"
echo "     * IB_HOST: your-ib-host"
echo "     * IB_PORT: your-ib-port"
echo "     * IB_CLIENT_ID: your-ib-client-id"
echo ""
echo "2. Deploy your code:"
echo "   - Use Azure DevOps pipeline (azure-deploy.yml)"
echo "   - Or use Azure CLI: az webapp deployment source config-zip"
echo ""
echo "3. Run database migrations:"
echo "   - Go to SSH in Azure Portal"
echo "   - Run: python manage.py migrate --settings=trading_project.settings_production"
echo ""
echo "🌐 Your app will be available at: https://$APP_NAME.azurewebsites.net"
