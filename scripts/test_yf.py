import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

import yfinance as yf
from app.services.stock_analyzer import StockAnalyzer
from app.database import SessionLocal

def test_yfinance_direct():
    print("Testing yfinance directly...")
    try:
        stock = yf.Ticker("AAPL")
        df = stock.history(period="1mo", interval="1d")
        print(f"Direct yfinance fetch AAPL shape: {df.shape}")
        if df.empty:
            print("Direct fetch returned empty DataFrame.")
        else:
            print(df.head())
    except Exception as e:
        print(f"Direct yfinance fetch failed: {e}")

def test_analyzer_fetch():
    print("\nTesting StockAnalyzer fetch_data...")
    db = SessionLocal()
    try:
        analyzer = StockAnalyzer(db)
        df = analyzer.fetch_data("AAPL", period="1mo")
        if df is None:
            print("StockAnalyzer.fetch_data returned None.")
        else:
            print(f"StockAnalyzer fetch AAPL shape: {df.shape}")
            print(df.head())
    finally:
        db.close()

if __name__ == "__main__":
    test_yfinance_direct()
    test_analyzer_fetch()
