import os
import sys
import json

sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.services.stock_analyzer import StockAnalyzer

def test_get_historical_indicators():
    db = SessionLocal()
    try:
        analyzer = StockAnalyzer(db)
        print("Testing 1y period...")
        data_1y = analyzer.get_historical_indicators("AAPL", period="1y")
        print(f"1y data points: {len(data_1y) if data_1y else 0}")
        
        print("\nTesting 3mo period...")
        data_3mo = analyzer.get_historical_indicators("AAPL", period="3mo")
        print(f"3mo data points: {len(data_3mo) if data_3mo else 0}")
        
        if data_3mo:
            print("Sample 3mo row:")
            print(json.dumps(data_3mo[-1], indent=2))
            
    finally:
        db.close()

if __name__ == "__main__":
    test_get_historical_indicators()
