import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .. import models
from decimal import Decimal

class StockAnalyzer:
    def __init__(self, db: Session):
        self.db = db

    def fetch_data(self, ticker: str, period: str = "1y", interval: str = "1d"):
        """Fetch historical data using yfinance."""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            if df.empty:
                return None
            return df
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None

    def calculate_indicators(self, df: pd.DataFrame):
        """Calculate technical indicators manually using pandas."""
        # EMA
        df["EMA10"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        
        # SMA
        df["SMA50"] = df["Close"].rolling(window=50).mean()
        df["SMA200"] = df["Close"].rolling(window=200).mean()
        
        # RSI
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        
        # Relative Volume
        df["AvgVol"] = df["Volume"].rolling(window=20).mean()
        df["VolRatio"] = df["Volume"] / df["AvgVol"]
        
        return df

    def detect_support_resistance(self, df: pd.DataFrame, window: int = 20):
        """Identify support and resistance levels using local minima and maxima."""
        # Use non-centered rolling window to avoid NaN on the latest rows
        # We look at the recent price range
        df["RecentLow"] = df["Low"].rolling(window=window).min()
        df["RecentHigh"] = df["High"].rolling(window=window).max()
        
        # Latest support/resistance from the last completed window
        # To find 'true' support/resistance, we look at the min/max of the recent period
        support = df["RecentLow"].iloc[-1]
        resistance = df["RecentHigh"].iloc[-1]
        
        # Breakout detection: current close > previous window high
        # We use the high from one bar ago to see if the current bar broke out of the established range
        prev_window_high = df["RecentHigh"].iloc[-2] if len(df) > 1 else resistance
        is_breakout = df["Close"].iloc[-1] > prev_window_high
        
        return float(support), float(resistance), bool(is_breakout)

    def calculate_relative_strength(self, ticker_df: pd.DataFrame, spy_df: pd.DataFrame):
        """Calculate performance relative to SPY."""
        if ticker_df is None or spy_df is None or len(ticker_df) < 22 or len(spy_df) < 22:
            return 0.0
        
        ticker_return = (ticker_df["Close"].iloc[-1] / ticker_df["Close"].iloc[-21]) - 1 # 1 month return
        spy_return = (spy_df["Close"].iloc[-1] / spy_df["Close"].iloc[-21]) - 1
        
        return float(ticker_return - spy_return)

    def score_stock(self, ticker: str, df: pd.DataFrame, spy_df: pd.DataFrame):
        """Apply weighted scoring model to rank the stock."""
        if df is None or len(df) < 200:
            return None
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0
        details = {
            "support_score": 0,
            "ema_score": 0,
            "sma_score": 0,
            "rs_score": 0,
            "vol_score": 0,
            "macd_score": 0
        }

        # 1. Support & Resistance (max 25)
        support, resistance, is_breakout = self.detect_support_resistance(df)
        if is_breakout:
            details["support_score"] = 25
        elif last["Close"] < support * 1.02: # Near support
            details["support_score"] = 15
        score += details["support_score"]

        # 2. EMA Crossover (max 20)
        if last["EMA10"] > last["EMA20"] and prev["EMA10"] <= prev["EMA20"]:
            details["ema_score"] = 20
        elif last["EMA10"] > last["EMA20"] and last["Close"] > last["EMA10"]:
            details["ema_score"] = 10
        score += details["ema_score"]

        # 3. SMA Golden Cross (max 25)
        if last["SMA50"] > last["SMA200"] and prev["SMA50"] <= prev["SMA200"]:
            details["sma_score"] = 25
        elif last["SMA50"] > last["SMA200"] and last["Close"] > last["SMA200"]:
            details["sma_score"] = 15
        score += details["sma_score"]

        # 4. Relative Strength (max 15)
        rs = self.calculate_relative_strength(df, spy_df)
        if rs > 0.05: # Outperforming by 5% in a month
            details["rs_score"] = 15
        elif rs > 0:
            details["rs_score"] = 10
        score += details["rs_score"]

        # 5. Volume & Momentum (max 15: Vol + MACD)
        if last["VolRatio"] > 1.5:
            details["vol_score"] = 10
        elif last["VolRatio"] > 1.1:
            details["vol_score"] = 5
        score += details["vol_score"]

        if last["MACD"] > last["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"]:
            details["macd_score"] = 5
        score += details["macd_score"]

        # RSI Confirmation (Constraint: 55-75 is bullish)
        if not (55 <= last["RSI"] <= 75):
            score -= 10 

        classification = "Ignore"
        if score >= 85: classification = "Strong Buy"
        elif score >= 70: classification = "Buy"
        elif score >= 55: classification = "Watchlist"

        return {
            "score": max(0, score),
            "details": details,
            "classification": classification,
            "current_price": last["Close"],
            "indicators": last.to_dict(),
            "support": support,
            "resistance": resistance,
            "is_breakout": is_breakout
        }

    def analyze_and_save(self, ticker: str, spy_df: pd.DataFrame):
        """Fetch, analyze, and persist results."""
        df = self.fetch_data(ticker)
        if df is None: return None
        
        df = self.calculate_indicators(df)
        result = self.score_stock(ticker, df, spy_df)
        if not result: return None

        # Save Indicators
        ind = result["indicators"]
        indicator_model = models.TechnicalIndicator(
            ticker=ticker,
            rsi=float(ind.get("RSI", 0)),
            macd_val=float(ind.get("MACD", 0)),
            macd_signal=float(ind.get("MACD_Signal", 0)),
            ema10=float(ind.get("EMA10", 0)),
            ema20=float(ind.get("EMA20", 0)),
            sma50=float(ind.get("SMA50", 0)),
            sma200=float(ind.get("SMA200", 0)),
            relative_strength=float(result["score"]),
            volume_ratio=float(ind.get("VolRatio", 1.0))
        )
        self.db.add(indicator_model)

        # Save Support/Resistance
        sr_model = models.SupportResistanceLevel(
            ticker=ticker,
            support_price=Decimal(str(round(result["support"], 2))),
            resistance_price=Decimal(str(round(result["resistance"], 2))),
            is_breakout=result["is_breakout"]
        )
        self.db.add(sr_model)

        # Save Score
        d = result["details"]
        score_model = models.MomentumScore(
            ticker=ticker,
            overall_score=result["score"],
            support_score=d["support_score"],
            ema_score=d["ema_score"],
            sma_score=d["sma_score"],
            rs_score=d["rs_score"],
            vol_score=d["vol_score"],
            macd_score=d["macd_score"]
        )
        self.db.add(score_model)

        # Update or Create Signal
        signal = self.db.query(models.StockSignal).filter(models.StockSignal.ticker == ticker).first()
        if not signal:
            signal = models.StockSignal(ticker=ticker)
            self.db.add(signal)
        
        # Optimization: LongName from info can be slow, use ticker if it fails
        try:
            stock_info = yf.Ticker(ticker).info
            signal.company_name = stock_info.get("longName", ticker)
        except:
            signal.company_name = ticker

        current_price = float(result["current_price"])
        signal.current_price = Decimal(str(round(current_price, 2)))
        signal.signal_type = result["classification"]
        signal.score = result["score"]
        signal.status = "Active"
        
        # Suggested Strategy Logic:
        # If breakout: entry is current price or slightly above.
        # If near support: entry is a range between support and current.
        if result["is_breakout"]:
            entry_price = current_price
            signal.suggested_entry = f"{entry_price:.2f} (Breakout)"
            signal.suggested_stop_loss = Decimal(str(round(result["support"], 2)))
            # Target 1.5x risk
            risk = entry_price - result["support"]
            if risk <= 0: risk = entry_price * 0.05 # Fallback
            signal.suggested_target = Decimal(str(round(entry_price + (risk * 1.5), 2)))
        else:
            entry_price = result["support"] * 1.01
            signal.suggested_entry = f"{entry_price:.2f} - {entry_price * 1.02:.2f}"
            signal.suggested_stop_loss = Decimal(str(round(result["support"] * 0.98, 2)))
            signal.suggested_target = Decimal(str(round(result["resistance"], 2)))

        hist = models.HistoricalScanResult(
            ticker=ticker,
            score=result["score"],
            classification=result["classification"],
            price_at_scan=Decimal(str(round(current_price, 2)))
        )
        self.db.add(hist)

        self.db.commit()
        return result

    def get_historical_indicators(self, ticker: str, period: str = "1y"):
        """Calculate and return full history of technical indicators for charting."""
        df = self.fetch_data(ticker, period=period)
        if df is None:
            return None
        
        df = self.calculate_indicators(df)
        
        # Prepare for JSON
        # Convert index (datetime) to string
        df.index = df.index.strftime("%Y-%m-%d")
        
        # Replace NaN with None for JSON serialization, don't drop rows because
        # short periods (e.g. 3mo) won't have SMA200 and would be completely dropped.
        df = df.replace({np.nan: None})
        
        return df.reset_index().to_dict(orient="records")
