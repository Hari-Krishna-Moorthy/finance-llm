from decimal import Decimal
from datetime import date, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.database import Base
from app.models import StockSignal, TechnicalIndicator, SupportResistanceLevel, MomentumScore, HistoricalScanResult
from app.services.stock_analyzer import StockAnalyzer

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

def generate_dummy_stock_data(periods=250, start_date='2026-01-01'):
    dates = pd.date_range(start=start_date, periods=periods, freq='B') # Business days
    df = pd.DataFrame({
        'Open': np.linspace(100, 150, periods),
        'High': np.linspace(105, 155, periods),
        'Low': np.linspace(95, 145, periods),
        'Close': np.linspace(102, 152, periods),
        'Volume': np.random.randint(1000000, 5000000, periods)
    }, index=dates)
    return df

@patch("app.services.stock_analyzer.yf.Ticker")
def test_fetch_data(mock_ticker_class):
    db = _make_session()
    analyzer = StockAnalyzer(db)
    
    mock_instance = MagicMock()
    mock_instance.history.return_value = generate_dummy_stock_data(10)
    mock_ticker_class.return_value = mock_instance
    
    df = analyzer.fetch_data("AAPL", period="10d")
    assert df is not None
    assert len(df) == 10
    mock_instance.history.assert_called_once_with(period="10d", interval="1d")

def test_calculate_indicators():
    db = _make_session()
    analyzer = StockAnalyzer(db)
    df = generate_dummy_stock_data(250)
    
    df_indicators = analyzer.calculate_indicators(df)
    
    assert "EMA10" in df_indicators.columns
    assert "EMA20" in df_indicators.columns
    assert "SMA50" in df_indicators.columns
    assert "SMA200" in df_indicators.columns
    assert "RSI" in df_indicators.columns
    assert "MACD" in df_indicators.columns
    assert "MACD_Signal" in df_indicators.columns
    assert "VolRatio" in df_indicators.columns
    
    # Check that rolling windows produce NaN initially, but valid numbers later
    assert pd.isna(df_indicators["SMA200"].iloc[0])
    assert not pd.isna(df_indicators["SMA200"].iloc[200])

def test_detect_support_resistance_trending():
    db = _make_session()
    analyzer = StockAnalyzer(db)
    
    # Generate 100 days of data
    # Days 0-50: Price is around $100
    # Days 50-99: Price is around $300
    # Day 100: Huge jump to $350 (Breakout)
    dates = pd.date_range(start='2026-01-01', periods=101, freq='B')
    prices = np.concatenate([
        np.linspace(95, 105, 50),
        np.linspace(295, 305, 50),
        [350.0]
    ])
    df = pd.DataFrame({
        'Open': prices,
        'High': prices + 1,
        'Low': prices - 1,
        'Close': prices,
        'Volume': 1000000
    }, index=dates)
    
    # window=20. It should look at the last 20 days (where price is ~$300)
    # and NOT return the $100 support from earlier.
    support, resistance, is_breakout = analyzer.detect_support_resistance(df, window=20)
    
    # Recent low should be around 294 (295 - 1)
    assert support > 250
    assert support < 310
    
    # Because prices jumped to 350, it should be a clear breakout
    assert is_breakout is True

def test_calculate_relative_strength():
    db = _make_session()
    analyzer = StockAnalyzer(db)
    
    ticker_df = generate_dummy_stock_data(50)
    spy_df = generate_dummy_stock_data(50)
    
    # Make ticker outperform SPY
    ticker_df.loc[ticker_df.index[-1], "Close"] = 200.0 # Huge jump
    
    rs = analyzer.calculate_relative_strength(ticker_df, spy_df)
    assert isinstance(rs, float)
    assert rs > 0.0 # Outperformed

@patch.object(StockAnalyzer, 'fetch_data')
def test_analyze_and_save(mock_fetch_data):
    db = _make_session()
    analyzer = StockAnalyzer(db)
    
    # Setup dummy data
    ticker_df = generate_dummy_stock_data(250)
    spy_df = generate_dummy_stock_data(250)
    
    # Force a very bullish setup to ensure a score > 0
    ticker_df.loc[ticker_df.index[-1], "Close"] = 160.0
    mock_fetch_data.return_value = ticker_df
    
    # Run analysis
    with patch("app.services.stock_analyzer.yf.Ticker") as mock_ticker:
        mock_info = MagicMock()
        mock_info.info = {"longName": "Test Company Inc."}
        mock_ticker.return_value = mock_info
        
        result = analyzer.analyze_and_save("TEST", spy_df)
    
    assert result is not None
    assert "score" in result
    assert "classification" in result
    
    # Verify DB persistence
    signal = db.query(StockSignal).filter(StockSignal.ticker == "TEST").first()
    assert signal is not None
    assert signal.company_name == "Test Company Inc."
    assert signal.status == "Active"
    
    ind = db.query(TechnicalIndicator).filter(TechnicalIndicator.ticker == "TEST").first()
    assert ind is not None
    
    sr = db.query(SupportResistanceLevel).filter(SupportResistanceLevel.ticker == "TEST").first()
    assert sr is not None
    
    score = db.query(MomentumScore).filter(MomentumScore.ticker == "TEST").first()
    assert score is not None
    
    hist = db.query(HistoricalScanResult).filter(HistoricalScanResult.ticker == "TEST").first()
    assert hist is not None

@patch.object(StockAnalyzer, 'fetch_data')
def test_get_historical_indicators_nan_handling(mock_fetch_data):
    db = _make_session()
    analyzer = StockAnalyzer(db)
    
    # 60 days of data (less than 200, so SMA200 will be NaN)
    df = generate_dummy_stock_data(60)
    mock_fetch_data.return_value = df
    
    result_list = analyzer.get_historical_indicators("TEST", period="3mo")
    
    assert result_list is not None
    assert len(result_list) == 60
    
    # Verify that NaN was replaced with None (which is valid for JSON)
    first_row = result_list[0]
    assert first_row["SMA200"] is None
