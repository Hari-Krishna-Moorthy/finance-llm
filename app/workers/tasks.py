from .celery_app import celery_app
from ..database import SessionLocal
from ..services.ingestion import process_file, process_markdown_text
from ..services.upload_tracking import mark_statement_upload_processed
from ..services.stock_analyzer import StockAnalyzer
import time

@celery_app.task(name="process_statement_task")
def process_statement_task(file_path: str, account_id: int, upload_id: int, password: str = None):
    db = SessionLocal()
    try:
        process_file(file_path, account_id, password=password)
        mark_statement_upload_processed(db, upload_id, True, None)
        return {"status": "success", "file": file_path}
    except Exception as e:
        mark_statement_upload_processed(db, upload_id, False, str(e))
        return {"status": "error", "message": str(e), "file": file_path}
    finally:
        db.close()

@celery_app.task(name="process_markdown_task")
def process_markdown_task(text: str, account_id: int):
    try:
        process_markdown_text(text, account_id)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@celery_app.task(name="scan_us_markets_task")
def scan_us_markets_task():
    db = SessionLocal()
    try:
        analyzer = StockAnalyzer(db)
        
        # Curated list of high-impact stocks for the initial scanner
        # Top US Market Stocks Universe (Approx 200 Stocks)
        # Mix of:
        # - Mega caps
        # - High growth tech
        # - Financials
        # - Healthcare
        # - Industrials
        # - Consumer
        # - Energy
        # - Semiconductor
        # - AI & Cloud
        # - ETFs for benchmarking

        tickers = [

            # =========================
            # BIG TECH / MEGA CAPS
            # =========================
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "AVGO", "ORCL", "CRM", "ADBE", "NFLX", "AMD", "INTC",
            "QCOM", "CSCO", "IBM", "NOW", "UBER", "SHOP",
            "SQ", "PYPL", "SNOW", "PLTR", "PANW", "CRWD",
            "ZS", "DDOG", "NET", "MDB", "TEAM", "DOCU",
            "OKTA", "AI", "SMCI", "MU", "ANET", "DELL",
            "HPQ", "WDAY", "INTU", "SAP", "VMW", "TWLO",

            # =========================
            # SEMICONDUCTORS / AI
            # =========================
            "TSM", "ASML", "AMAT", "LRCX", "KLAC", "MRVL",
            "ON", "NXPI", "MCHP", "ADI", "TXN", "ARM",
            "TER", "MPWR", "ENTG", "LSCC", "COHR",

            # =========================
            # BANKS & FINANCIALS
            # =========================
            "JPM", "BAC", "WFC", "C", "GS", "MS",
            "BLK", "SCHW", "AXP", "V", "MA", "PYPL",
            "SPGI", "ICE", "CME", "KKR", "BX", "APO",
            "COIN", "SOFI", "HOOD", "ALLY", "USB", "PNC",

            # =========================
            # HEALTHCARE / PHARMA
            # =========================
            "LLY", "JNJ", "PFE", "MRK", "ABBV", "UNH",
            "ISRG", "TMO", "DHR", "VRTX", "REGN", "AMGN",
            "BMY", "GILD", "MDT", "CI", "HUM", "ZTS",
            "SYK", "BSX", "CVS", "ELV", "BIIB", "MRNA",

            # =========================
            # CONSUMER / RETAIL
            # =========================
            "WMT", "COST", "HD", "LOW", "TGT", "NKE",
            "SBUX", "MCD", "KO", "PEP", "PG", "EL",
            "LULU", "TJX", "ROST", "CMG", "YUM", "ULTA",
            "ETSY", "EBAY", "BKNG", "ABNB", "MAR", "HLT",

            # =========================
            # INDUSTRIALS / DEFENSE
            # =========================
            "BA", "CAT", "DE", "HON", "GE", "RTX",
            "LMT", "NOC", "GD", "ETN", "PH", "MMM",
            "UNP", "CSX", "NSC", "UPS", "FDX", "EMR",
            "TT", "PCAR", "ODFL", "JCI", "CARR",

            # =========================
            # ENERGY / UTILITIES
            # =========================
            "XOM", "CVX", "COP", "SLB", "EOG", "OXY",
            "MPC", "PSX", "VLO", "KMI", "NEE", "DUK",
            "SO", "EXC", "AEP", "SRE", "PEG", "XEL",

            # =========================
            # TELECOM / MEDIA
            # =========================
            "DIS", "CMCSA", "TMUS", "VZ", "T", "CHTR",
            "WBD", "PARA", "FOX", "SPOT", "ROKU",

            # =========================
            # REAL ESTATE / REITS
            # =========================
            "PLD", "AMT", "CCI", "EQIX", "O", "SPG",
            "DLR", "WELL", "PSA", "VICI", "AVB",

            # =========================
            # AUTO / EV / TRANSPORT
            # =========================
            "RIVN", "LCID", "F", "GM", "NIO", "XPEV",
            "LI", "TM", "HMC", "STLA", "DASH", "LYFT",

            # =========================
            # MATERIALS / MINING
            # =========================
            "LIN", "FCX", "NEM", "APD", "ECL", "NUE",
            "STLD", "AA", "MOS", "CF", "DOW",

            # =========================
            # ETFs / INDEX TRACKERS
            # =========================
            "SPY", "QQQ", "DIA", "IWM", "VTI",
            "SMH", "XLF", "XLK", "XLE", "ARKK",

            # =========================
            # HIGH MOMENTUM / GROWTH
            # =========================
            "CELH", "DUOL", "APP", "HUBS", "TTD",
            "PATH", "UPST", "AFRM", "CAVA", "CVNA",
            "MELI", "SE", "PINS", "SNAP", "BILL",

            # =========================
            # CYBERSECURITY / CLOUD
            # =========================
            "FTNT", "CYBR", "S", "ESTC", "AKAM",
            "FSLY", "GTLB", "HCP", "RBLX", "U",

            # =========================
            # BIOTECH / INNOVATION
            # =========================
            "CRSP", "EDIT", "NTLA", "BEAM", "DNA",
            "RXRX", "ILMN", "PACB", "EXAS", "TXG"
        ]
        
        # Fetch SPY for relative strength
        spy_df = analyzer.fetch_data("SPY")
        
        results = []
        for ticker in tickers:
            try:
                print(f"Scanning {ticker}...")
                res = analyzer.analyze_and_save(ticker, spy_df)
                if res:
                    results.append({"ticker": ticker, "score": res["score"], "classification": res["classification"]})
            except Exception as e:
                print(f"Error scanning {ticker}: {e}")
            
            # Rate limit handling: avoid hitting Yahoo Finance limits
            time.sleep(1) 
            
        # Sort by score and take top
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return {"status": "success", "scanned": len(results), "top_candidates": results[:5]}
    except Exception as e:
        print(f"Scan Error: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
