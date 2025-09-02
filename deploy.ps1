# Trading Pro Azure Deployment Script (PowerShell)
# This script helps deploy the Trading Pro application to Azure App Service

param(
    [string]$ResourceGroup = "trading-pro-rg",
    [string]$AppName = "trading-pro-app",
    [string]$Location = "eastus",
    [string]$PlanName = "trading-pro-plan",
    [string]$DatabaseName = "trading-pro-db",
    [string]$DatabaseServer = "trading-pro-server"
)

Write-Host "🚀 Starting Trading Pro Azure Deployment..." -ForegroundColor Green

# Check if Azure CLI is installed
try {
    $azVersion = az version 2>$null
    Write-Host "✅ Azure CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure CLI is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Check if user is logged in to Azure
try {
    $account = az account show 2>$null
    Write-Host "✅ Azure CLI authenticated" -ForegroundColor Green
} catch {
    Write-Host "🔐 Please log in to Azure CLI:" -ForegroundColor Yellow
    az login
}

Write-Host "📋 Configuration:" -ForegroundColor Cyan
Write-Host "   Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "   App Name: $AppName" -ForegroundColor White
Write-Host "   Location: $Location" -ForegroundColor White
Write-Host "   Database: $DatabaseName" -ForegroundColor White

# Create resource group
Write-Host "🏗️  Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Create App Service plan
Write-Host "📦 Creating App Service plan..." -ForegroundColor Yellow
az appservice plan create `
    --name $PlanName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku B1 `
    --is-linux

# Create PostgreSQL database
Write-Host "🗄️  Creating PostgreSQL database..." -ForegroundColor Yellow
$adminPassword = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})

az postgres flexible-server create `
    --resource-group $ResourceGroup `
    --name $DatabaseServer `
    --location $Location `
    --admin-user tradingadmin `
    --admin-password $adminPassword `
    --sku-name Standard_B1ms `
    --tier Burstable `
    --public-access 0.0.0.0 `
    --storage-size 32

# Create database
az postgres flexible-server db create `
    --resource-group $ResourceGroup `
    --server-name $DatabaseServer `
    --database-name $DatabaseName

# Create web app
Write-Host "🌐 Creating web app..." -ForegroundColor Yellow
az webapp create `
    --resource-group $ResourceGroup `
    --plan $PlanName `
    --name $AppName `
    --runtime "PYTHON|3.11"

# Configure app settings
Write-Host "⚙️  Configuring app settings..." -ForegroundColor Yellow
az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --settings `
        WEBSITES_ENABLE_APP_SERVICE_STORAGE=true `
        SCM_DO_BUILD_DURING_DEPLOYMENT=true `
        ENABLE_ORYX_BUILD=true

# Set database URL (using provided Azure PostgreSQL)
Write-Host "🔗 Setting database connection..." -ForegroundColor Yellow
$dbConnectionString = "postgresql://psql_admin:NqBHWBE9EhVltj16fjuq@newstradingapplication.postgres.database.azure.com:5432/postgres"

az webapp config appsettings set `
    --resource-group $ResourceGroup `
    --name $AppName `
    --settings DATABASE_URL="$dbConnectionString"

Write-Host "✅ Deployment configuration completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Set your environment variables in Azure Portal:" -ForegroundColor White
Write-Host "   - Go to https://portal.azure.com" -ForegroundColor White
Write-Host "   - Navigate to your App Service: $AppName" -ForegroundColor White
Write-Host "   - Go to Configuration > Application settings" -ForegroundColor White
Write-Host "   - Add the following variables:" -ForegroundColor White
Write-Host "     * SECRET_KEY: $(-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_}))" -ForegroundColor Yellow
Write-Host "     * OPENAI_API_KEY: your-openai-api-key" -ForegroundColor Yellow
Write-Host "     * IB_HOST: your-ib-host" -ForegroundColor Yellow
Write-Host "     * IB_PORT: your-ib-port" -ForegroundColor Yellow
Write-Host "     * IB_CLIENT_ID: your-ib-client-id" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Deploy your code:" -ForegroundColor White
Write-Host "   - Use Azure DevOps pipeline (azure-deploy.yml)" -ForegroundColor White
Write-Host "   - Or use Azure CLI: az webapp deployment source config-zip" -ForegroundColor White
Write-Host ""
Write-Host "3. Run database migrations:" -ForegroundColor White
Write-Host "   - Go to SSH in Azure Portal" -ForegroundColor White
Write-Host "   - Run: python manage.py migrate --settings=trading_project.settings_production" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Your app will be available at: https://$AppName.azurewebsites.net" -ForegroundColor Green
