# 🚀 Trading Pro - Financial News Scraping System

A comprehensive Django-based web scraping system for financial news aggregation with anti-bot measures, API integration, and historical data storage.

## ✨ Features

### 🕷️ **Web Scraping & Data Ingestion**
- **Reuters Finance Scraper**: Scrapes financial news from reuters.com/finance
- **FinnHub API Integration**: Connects to FinnHub for additional financial data
- **Anti-Bot Measures**: User agent rotation, random delays, session management
- **JavaScript Support**: Selenium-based scraping for dynamic content
- **Continue Reading**: Handles "Continue Reading" buttons and pagination

### 📊 **Data Management**
- **Historical Records**: Maintains complete history of scraped articles
- **Database Storage**: SQLite database with optimized models and indexing
- **Data Deduplication**: Prevents duplicate articles based on URLs
- **Metadata Extraction**: Title, content, summary, author, category, tags

### 🎛️ **Control & Monitoring**
- **Web Interface**: Beautiful dashboard for managing scraping operations
- **Real-time Monitoring**: Track scraping sessions and success rates
- **API Management**: Configure and manage API keys securely
- **Command Line Tools**: Django management commands for automation

### 🔒 **Reliability & Security**
- **Error Handling**: Comprehensive error logging and recovery
- **Rate Limiting**: Configurable request limits to avoid blocking
- **Session Management**: Persistent sessions with retry logic
- **Data Validation**: Input sanitization and validation

## 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Scraping Core │    │   Database     │
│                 │    │                 │    │                 │
│ • News Dashboard│◄──►│ • Reuters       │◄──►│ • NewsArticle  │
│ • Scraping      │    │ • FinnHub       │    │ • Scraping     │
│   Control       │    │ • Base Scraper  │    │   Session      │
│ • API Config    │    │ • Manager       │    │ • APIConfig    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start**

### 1. **Installation**
```bash
# Clone the repository
git clone <repository-url>
cd trading_pro

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

### 2. **Access the System**
- **Home**: http://127.0.0.1:8000/
- **News Dashboard**: http://127.0.0.1:8000/news/
- **Scraping Control**: http://127.0.0.1:8000/scraping/
- **API Configuration**: http://127.0.0.1:8000/api-config/

### 3. **First Scraping Run**
```bash
# Scrape Reuters (default)
python manage.py scrape_news

# Scrape with custom settings
python manage.py scrape_news --source reuters --max-articles 50

# Scrape FinnHub (requires API key)
python manage.py scrape_news --source finnhub --symbol AAPL
```

## 📋 **Configuration**

### **Reuters Scraping**
- **URL**: https://www.reuters.com/finance
- **Features**: 
  - Automatic article detection
  - Content extraction with Selenium
  - Anti-detection measures
  - Configurable article limits

### **FinnHub API**
1. **Get API Key**: Visit [finnhub.io](https://finnhub.io/) and sign up
2. **Configure**: Use the API Configuration page
3. **Features**:
   - Company-specific news
   - Market news categories
   - Sentiment analysis
   - Related company tags

### **Environment Variables**
```bash
# Optional: Set Django secret key
export DJANGO_SECRET_KEY="your-secret-key"

# Optional: Set debug mode
export DJANGO_DEBUG=False
```

## 🎯 **Usage Examples**

### **Web Interface**
1. **Start Scraping**:
   - Go to `/scraping/`
   - Select source (Reuters/FinnHub)
   - Set parameters and click "Start Scraping"

2. **View Results**:
   - Go to `/news/` to see all scraped articles
   - Use filters to search by source, category, or keywords
   - Click on articles to view full content

3. **Manage APIs**:
   - Go to `/api-config/`
   - Add your FinnHub API key
   - Monitor API usage and status

### **Command Line**
```bash
# Basic Reuters scraping
python manage.py scrape_news

# Scrape multiple sources
python manage.py scrape_news --source all

# Company-specific news
python manage.py scrape_news --source finnhub --symbol TSLA

# Custom article limit
python manage.py scrape_news --source reuters --max-articles 100

# Test mode (don't save to DB)
python manage.py scrape_news --save-db false
```

### **Programmatic Usage**
```python
from main_app.scrapers import ScrapingManager

# Initialize manager
manager = ScrapingManager()

# Scrape Reuters
articles = manager.scrape_reuters(max_articles=20, save_to_db=True)

# Setup and scrape FinnHub
manager.setup_finnhub("your-api-key")
finnhub_articles = manager.scrape_finnhub(symbol="AAPL")
```

## 📊 **Data Models**

### **NewsArticle**
- `title`: Article headline
- `content`: Full article text
- `summary`: Article excerpt
- `url`: Source URL
- `source`: Data source (reuters/finnhub)
- `published_date`: Original publication date
- `scraped_date`: When article was scraped
- `author`: Article author
- `category`: News category
- `tags`: Related tags/companies
- `sentiment_score`: Sentiment analysis score

### **ScrapingSession**
- `source`: Scraping source
- `start_time`: Session start
- `end_time`: Session completion
- `status`: Running/Completed/Failed
- `articles_scraped`: Number of articles collected
- `errors`: Error log
- `config`: Session configuration

### **APIConfig**
- `name`: API service name
- `api_key`: Encrypted API key
- `base_url`: API endpoint
- `is_active`: Service status
- `rate_limit`: Request limits

## 🛡️ **Anti-Bot Measures**

### **Request Management**
- **User Agent Rotation**: Random user agents for each request
- **Random Delays**: Configurable delays between requests
- **Session Persistence**: Maintains cookies and headers
- **Retry Logic**: Automatic retry on failures

### **Selenium Features**
- **Stealth Mode**: Disables automation indicators
- **Dynamic Content**: Handles JavaScript-loaded content
- **Button Interaction**: Clicks "Continue Reading" buttons
- **Scroll Simulation**: Mimics human browsing behavior

## 📈 **Performance & Scaling**

### **Optimization Features**
- **Database Indexing**: Optimized queries for large datasets
- **Pagination**: Efficient article browsing
- **Caching**: Session and request caching
- **Async Processing**: Background task support (planned)

### **Monitoring**
- **Real-time Stats**: Live scraping statistics
- **Error Tracking**: Comprehensive error logging
- **Performance Metrics**: Response times and success rates
- **Resource Usage**: Memory and CPU monitoring

## 🔧 **Customization**

### **Adding New Sources**
1. **Create Scraper Class**:
   ```python
   class NewSourceScraper(BaseScraper):
       def scrape_articles(self):
           # Your scraping logic
           pass
   ```

2. **Update Models**:
   - Add source to `NewsArticle.SOURCE_CHOICES`
   - Update database migrations

3. **Add to Manager**:
   - Integrate with `ScrapingManager`
   - Add web interface controls

### **Custom Data Processing**
- **Content Filters**: Modify article processing
- **Metadata Extraction**: Add custom fields
- **Sentiment Analysis**: Integrate custom algorithms
- **Data Export**: Custom export formats

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Chrome Driver Not Found**:
   ```bash
   # Install Chrome WebDriver
   pip install webdriver-manager
   ```

2. **Scraping Blocked**:
   - Increase delay ranges
   - Rotate user agents more frequently
   - Use proxy rotation (advanced)

3. **Database Errors**:
   ```bash
   # Reset database
   python manage.py flush
   python manage.py migrate
   ```

4. **API Rate Limits**:
   - Check API configuration
   - Adjust rate limiting settings
   - Monitor API usage

### **Debug Mode**
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 **API Reference**

### **ScrapingManager Methods**
- `scrape_reuters(max_articles, save_to_db)`: Scrape Reuters
- `scrape_finnhub(symbol, category, save_to_db)`: Scrape FinnHub
- `setup_finnhub(api_key)`: Configure FinnHub API

### **BaseScraper Methods**
- `get_page(url, retries)`: Fetch web page
- `random_delay()`: Anti-detection delay
- `rotate_user_agent()`: Change user agent

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-scraper`
3. **Commit changes**: `git commit -am 'Add new scraper'`
4. **Push branch**: `git push origin feature/new-scraper`
5. **Submit pull request**

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions
- **Documentation**: Check this README and code comments

## 🔮 **Roadmap**

- [ ] **Real-time Scraping**: WebSocket-based live updates
- [ ] **Proxy Rotation**: Advanced anti-detection
- [ ] **Machine Learning**: Automated content classification
- [ ] **Data Export**: CSV, JSON, Excel export
- [ ] **Scheduled Scraping**: Cron-based automation
- [ ] **Multi-language Support**: International news sources
- [ ] **Mobile App**: React Native mobile interface

---

**Built with ❤️ using Django, Selenium, and BeautifulSoup**
