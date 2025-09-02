import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.common import TickerId, BarData
except ImportError:
    # Fallback for when IB API is not installed
    EClient = None
    EWrapper = None
    Contract = None
    Order = None
    TickerId = None
    BarData = None

from .models import (
    MarketTicker, MarketData, HistoricalData, 
    IBConnection, DataCollectionJob
)

logger = logging.getLogger(__name__)

class IBWrapper(EWrapper):
    """Interactive Brokers API Wrapper for handling callbacks"""
    
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.next_order_id = 1
        
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        """Handle API errors"""
        logger.error(f"IB API Error {errorCode}: {errorString} (ReqId: {reqId})")
        self.service.handle_error(reqId, errorCode, errorString)
    
    def nextValidId(self, orderId: int):
        """Receive next valid order ID"""
        self.next_order_id = orderId
        logger.info(f"Next valid order ID: {orderId}")
    
    def tickPrice(self, reqId: TickerId, tickType: int, price: float, attrib):
        """Handle real-time price updates"""
        self.service.handle_tick_price(reqId, tickType, price, attrib)
    
    def tickSize(self, reqId: TickerId, tickType: int, size: int):
        """Handle real-time size updates"""
        self.service.handle_tick_size(reqId, tickType, size)
    
    def historicalData(self, reqId: int, bar: BarData):
        """Handle historical data updates"""
        self.service.handle_historical_data(reqId, bar)
    
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Handle end of historical data"""
        self.service.handle_historical_data_end(reqId, start, end)
    
    def contractDetails(self, reqId: int, contractDetails):
        """Handle contract details"""
        self.service.handle_contract_details(reqId, contractDetails)
    
    def contractDetailsEnd(self, reqId: int):
        """Handle end of contract details"""
        self.service.handle_contract_details_end(reqId)

class IBAPIService:
    """Interactive Brokers API Service for market data collection"""
    
    def __init__(self, connection: IBConnection = None):
        if not EClient or not EWrapper:
            raise ImportError("Interactive Brokers API not installed. Please install ibapi package.")
        
        self.connection = connection
        self.client = None
        self.wrapper = None
        self.is_connected = False
        self.connection_thread = None
        self.request_id_counter = 1000
        self.active_requests = {}
        self.ticker_requests = {}
        
        # Callbacks
        self.on_connected = None
        self.on_disconnected = None
        self.on_error = None
        self.on_tick_update = None
        self.on_historical_data = None
        
    def set_connection(self, connection: IBConnection):
        """Set the IB connection configuration"""
        self.connection = connection
        
    def connect(self) -> bool:
        """Connect to Interactive Brokers"""
        if not self.connection:
            logger.error("No connection configuration set")
            return False
            
        try:
            self.wrapper = IBWrapper(self)
            self.client = EClient(self.wrapper)
            
            # Start connection in separate thread
            self.connection_thread = threading.Thread(
                target=self._run_connection,
                daemon=True
            )
            self.connection_thread.start()
            
            # Wait for connection
            timeout = self.connection.timeout
            start_time = time.time()
            
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                logger.info(f"Connected to IB at {self.connection.host}:{self.connection.port}")
                if self.on_connected:
                    self.on_connected()
                return True
            else:
                logger.error("Failed to connect to IB within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to IB: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Interactive Brokers"""
        if self.client and self.is_connected:
            self.client.disconnect()
            self.is_connected = False
            logger.info("Disconnected from IB")
            if self.on_disconnected:
                self.on_disconnected()
    
    def _run_connection(self):
        """Run the connection in a separate thread"""
        try:
            self.client.connect(
                self.connection.host,
                self.connection.port,
                self.connection.client_id
            )
            self.is_connected = True
            self.client.run()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.is_connected = False
    
    def handle_error(self, reqId: TickerId, errorCode: int, errorString: str):
        """Handle API errors"""
        if errorCode in [2104, 2106, 2158]:  # Connection errors
            self.is_connected = False
            if self.on_error:
                self.on_error(errorCode, errorString)
    
    def handle_tick_price(self, reqId: TickerId, tickType: int, price: float, attrib):
        """Handle real-time price updates"""
        if reqId in self.ticker_requests:
            ticker = self.ticker_requests[reqId]
            self._update_market_data(ticker, tickType, price, None)
            
            if self.on_tick_update:
                self.on_tick_update(ticker, tickType, price, None)
    
    def handle_tick_size(self, reqId: TickerId, tickType: int, size: int):
        """Handle real-time size updates"""
        if reqId in self.ticker_requests:
            ticker = self.ticker_requests[reqId]
            self._update_market_data(ticker, tickType, None, size)
    
    def handle_historical_data(self, reqId: int, bar: BarData):
        """Handle historical data updates"""
        if reqId in self.active_requests:
            request_info = self.active_requests[reqId]
            self._store_historical_data(request_info, bar)
    
    def handle_historical_data_end(self, reqId: int, start: str, end: str):
        """Handle end of historical data"""
        if reqId in self.active_requests:
            request_info = self.active_requests[reqId]
            request_info['completed'] = True
            logger.info(f"Historical data collection completed for request {reqId}")
    
    def handle_contract_details(self, reqId: int, contractDetails):
        """Handle contract details"""
        if reqId in self.active_requests:
            request_info = self.active_requests[reqId]
            self._update_ticker_info(request_info, contractDetails)
    
    def handle_contract_details_end(self, reqId: int):
        """Handle end of contract details"""
        if reqId in self.active_requests:
            request_info = self.active_requests[reqId]
            request_info['completed'] = True
    
    def create_contract(self, symbol: str, exchange: str = "SMART", 
                       sec_type: str = "STK", currency: str = "USD") -> Contract:
        """Create an IB contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract
    
    def request_market_data(self, ticker: MarketTicker) -> bool:
        """Request real-time market data for a ticker"""
        if not self.is_connected:
            logger.error("Not connected to IB")
            return False
        
        try:
            contract = self.create_contract(
                ticker.symbol,
                ticker.exchange,
                ticker.security_type,
                ticker.currency
            )
            
            req_id = self._get_next_request_id()
            self.ticker_requests[req_id] = ticker
            
            # Request market data
            self.client.reqMktData(req_id, contract, "", False, False, [])
            
            logger.info(f"Requested market data for {ticker.symbol} (ReqId: {req_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting market data for {ticker.symbol}: {e}")
            return False
    
    def request_historical_data(self, ticker: MarketTicker, timeframe: str = "1 D",
                               duration: str = "1 Y", bar_size: str = "1 day") -> bool:
        """Request historical data for a ticker"""
        if not self.is_connected:
            logger.error("Not connected to IB")
            return False
        
        try:
            contract = self.create_contract(
                ticker.symbol,
                ticker.exchange,
                ticker.security_type,
                ticker.currency
            )
            
            req_id = self._get_next_request_id()
            
            # Store request info
            self.active_requests[req_id] = {
                'ticker': ticker,
                'timeframe': timeframe,
                'duration': duration,
                'bar_size': bar_size,
                'completed': False,
                'data_count': 0
            }
            
            # Request historical data
            end_date = datetime.now().strftime("%Y%m%d %H:%M:%S")
            self.client.reqHistoricalData(
                req_id, contract, end_date, duration, bar_size, "TRADES", 1, 1, False, []
            )
            
            logger.info(f"Requested historical data for {ticker.symbol} (ReqId: {req_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting historical data for {ticker.symbol}: {e}")
            return False
    
    def request_contract_details(self, symbol: str, exchange: str = "SMART",
                                sec_type: str = "STK", currency: str = "USD") -> bool:
        """Request contract details for a symbol"""
        if not self.is_connected:
            logger.error("Not connected to IB")
            return False
        
        try:
            contract = self.create_contract(symbol, exchange, sec_type, currency)
            
            req_id = self._get_next_request_id()
            
            # Store request info
            self.active_requests[req_id] = {
                'symbol': symbol,
                'exchange': exchange,
                'sec_type': sec_type,
                'currency': currency,
                'completed': False
            }
            
            # Request contract details
            self.client.reqContractDetails(req_id, contract)
            
            logger.info(f"Requested contract details for {symbol} (ReqId: {req_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting contract details for {symbol}: {e}")
            return False
    
    def _get_next_request_id(self) -> int:
        """Get next available request ID"""
        self.request_id_counter += 1
        return self.request_id_counter
    
    def _update_market_data(self, ticker: MarketTicker, tickType: int, 
                           price: float = None, size: int = None):
        """Update market data in database"""
        try:
            with transaction.atomic():
                # Get or create latest market data record
                market_data, created = MarketData.objects.get_or_create(
                    ticker=ticker,
                    defaults={'timestamp': timezone.now()}
                )
                
                # Update fields based on tick type
                if price is not None:
                    if tickType == 1:  # Bid price
                        market_data.bid_price = Decimal(str(price))
                    elif tickType == 2:  # Ask price
                        market_data.ask_price = Decimal(str(price))
                    elif tickType == 4:  # Last price
                        market_data.last_price = Decimal(str(price))
                    elif tickType == 6:  # High price
                        market_data.high_price = Decimal(str(price))
                    elif tickType == 7:  # Low price
                        market_data.low_price = Decimal(str(price))
                    elif tickType == 9:  # Close price
                        market_data.close_price = Decimal(str(price))
                    elif tickType == 14:  # Open price
                        market_data.open_price = Decimal(str(price))
                
                if size is not None:
                    if tickType == 0:  # Bid size
                        market_data.bid_size = size
                    elif tickType == 3:  # Ask size
                        market_data.ask_size = size
                    elif tickType == 5:  # Last size
                        market_data.last_size = size
                    elif tickType == 8:  # Volume
                        market_data.volume = size
                
                # Calculate derived fields
                market_data.spread = market_data.calculate_spread()
                market_data.price_change = market_data.calculate_price_change()
                market_data.price_change_percent = market_data.calculate_price_change_percent()
                market_data.market_timestamp = timezone.now()
                
                market_data.save()
                
                # Update ticker's last price update
                ticker.last_price_update = timezone.now()
                ticker.save(update_fields=['last_price_update'])
                
        except Exception as e:
            logger.error(f"Error updating market data for {ticker.symbol}: {e}")
    
    def _store_historical_data(self, request_info: Dict, bar: BarData):
        """Store historical data in database"""
        try:
            ticker = request_info['ticker']
            timeframe = request_info['timeframe']
            
            # Convert bar time to datetime
            bar_time = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S")
            
            # Create or update historical data record
            historical_data, created = HistoricalData.objects.get_or_create(
                ticker=ticker,
                timeframe=timeframe,
                bar_time=bar_time,
                defaults={
                    'open_price': Decimal(str(bar.open)),
                    'high_price': Decimal(str(bar.high)),
                    'low_price': Decimal(str(bar.low)),
                    'close_price': Decimal(str(bar.close)),
                    'volume': bar.volume
                }
            )
            
            if not created:
                # Update existing record
                historical_data.open_price = Decimal(str(bar.open))
                historical_data.high_price = Decimal(str(bar.high))
                historical_data.low_price = Decimal(str(bar.low))
                historical_data.close_price = Decimal(str(bar.close))
                historical_data.volume = bar.volume
                historical_data.save()
            
            request_info['data_count'] += 1
            
        except Exception as e:
            logger.error(f"Error storing historical data: {e}")
    
    def _update_ticker_info(self, request_info: Dict, contractDetails):
        """Update ticker information from contract details"""
        try:
            symbol = request_info['symbol']
            exchange = request_info['exchange']
            sec_type = request_info['sec_type']
            currency = request_info['currency']
            
            contract = contractDetails.contract
            
            # Get or create ticker
            ticker, created = MarketTicker.objects.get_or_create(
                symbol=contract.symbol,
                exchange=contract.exchange,
                security_type=contract.secType,
                currency=contract.currency,
                defaults={
                    'company_name': contractDetails.longName or '',
                    'min_tick': Decimal(str(contractDetails.minTick)) if contractDetails.minTick else None,
                    'lot_size': contractDetails.lotSize or 1,
                }
            )
            
            if not created:
                # Update existing ticker
                if contractDetails.longName:
                    ticker.company_name = contractDetails.longName
                if contractDetails.minTick:
                    ticker.min_tick = Decimal(str(contractDetails.minTick))
                if contractDetails.lotSize:
                    ticker.lot_size = contractDetails.lotSize
                ticker.save()
            
            logger.info(f"Updated ticker info for {symbol}")
            
        except Exception as e:
            logger.error(f"Error updating ticker info: {e}")

class MarketDataManager:
    """Manager class for market data operations"""
    
    def __init__(self):
        self.ib_service = None
        self.connection = None
    
    def setup_connection(self, connection_name: str = None) -> bool:
        """Setup IB connection"""
        try:
            if connection_name:
                self.connection = IBConnection.objects.get(name=connection_name, is_active=True)
            else:
                self.connection = IBConnection.objects.filter(is_active=True).first()
            
            if not self.connection:
                logger.error("No active IB connection found")
                return False
            
            self.ib_service = IBAPIService(self.connection)
            return True
            
        except IBConnection.DoesNotExist:
            logger.error(f"IB connection '{connection_name}' not found")
            return False
        except Exception as e:
            logger.error(f"Error setting up connection: {e}")
            return False
    
    def connect(self) -> bool:
        """Connect to IB"""
        if not self.ib_service:
            logger.error("IB service not initialized")
            return False
        
        return self.ib_service.connect()
    
    def disconnect(self):
        """Disconnect from IB"""
        if self.ib_service:
            self.ib_service.disconnect()
    
    def start_real_time_data(self, tickers: List[str]) -> bool:
        """Start real-time data collection for multiple tickers"""
        if not self.ib_service or not self.ib_service.is_connected:
            logger.error("Not connected to IB")
            return False
        
        success_count = 0
        for symbol in tickers:
            try:
                ticker = MarketTicker.objects.get(symbol=symbol)
                if self.ib_service.request_market_data(ticker):
                    success_count += 1
            except MarketTicker.DoesNotExist:
                logger.warning(f"Ticker {symbol} not found in database")
            except Exception as e:
                logger.error(f"Error starting real-time data for {symbol}: {e}")
        
        logger.info(f"Started real-time data for {success_count}/{len(tickers)} tickers")
        return success_count > 0
    
    def collect_historical_data(self, tickers: List[str], timeframe: str = "1 D",
                               duration: str = "1 Y", bar_size: str = "1 day") -> bool:
        """Collect historical data for multiple tickers"""
        if not self.ib_service or not self.ib_service.is_connected:
            logger.error("Not connected to IB")
            return False
        
        success_count = 0
        for symbol in tickers:
            try:
                ticker = MarketTicker.objects.get(symbol=symbol)
                if self.ib_service.request_historical_data(ticker, timeframe, duration, bar_size):
                    success_count += 1
            except MarketTicker.DoesNotExist:
                logger.warning(f"Ticker {symbol} not found in database")
            except Exception as e:
                logger.error(f"Error collecting historical data for {symbol}: {e}")
        
        logger.info(f"Started historical data collection for {success_count}/{len(tickers)} tickers")
        return success_count > 0
    
    def get_popular_tickers(self) -> List[str]:
        """Get list of popular ticker symbols"""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'UBER', 'LYFT', 'SPOT',
            'TWTR', 'SNAP', 'PINS', 'SQ', 'ROKU', 'ZM', 'DOCU', 'OKTA',
            'CRWD', 'ZS', 'NET', 'DDOG', 'SNOW', 'PLTR', 'RBLX', 'COIN'
        ]
