from datetime import date
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import AIAnalysisResult
from app.workers.tasks import scan_us_markets_task, generate_ai_analysis_task

def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.StockAnalyzer")
@patch("app.workers.tasks.time.sleep", return_value=None) # Skip sleeps during test
def test_scan_us_markets_task(mock_sleep, mock_analyzer_class, mock_session_local):
    db = _make_session()
    mock_session_local.return_value = db
    
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.fetch_data.return_value = "dummy_spy_df"
    
    # Return a dummy result for the first ticker, None for others
    def mock_analyze_and_save(ticker, spy_df):
        if ticker == "AAPL":
            return {"score": 90, "classification": "Strong Buy"}
        return None
        
    mock_analyzer_instance.analyze_and_save.side_effect = mock_analyze_and_save
    mock_analyzer_class.return_value = mock_analyzer_instance
    
    result = scan_us_markets_task()
    
    assert result["status"] == "success"
    assert result["scanned"] == 1
    assert result["top_candidates"][0]["ticker"] == "AAPL"
    
@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.StockAnalyzer")
@patch("app.workers.tasks.generate_swing_trade_setup")
def test_generate_ai_analysis_task(mock_generate_setup, mock_analyzer_class, mock_session_local):
    db = _make_session()
    mock_session_local.return_value = db
    
    mock_analyzer_instance = MagicMock()
    # Return a dummy list of historical data dicts
    mock_analyzer_instance.get_historical_indicators.return_value = [{"Close": 150.0}]
    mock_analyzer_class.return_value = mock_analyzer_instance
    
    mock_generate_setup.return_value = "AI Analysis Result Text"
    
    # 1. Test normal generation
    result = generate_ai_analysis_task("AAPL")
    
    assert result["status"] == "success"
    
    # Verify DB persistence
    saved_result = db.query(AIAnalysisResult).filter(AIAnalysisResult.ticker == "AAPL").first()
    assert saved_result is not None
    assert saved_result.analysis_text == "AI Analysis Result Text"
    assert saved_result.generated_date == date.today()
    
    # 2. Test already generated (should not call LLM again)
    mock_generate_setup.reset_mock()
    
    result2 = generate_ai_analysis_task("AAPL")
    assert result2["status"] == "success"
    assert result2["message"] == "Already generated"
    mock_generate_setup.assert_not_called()

@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.StockAnalyzer")
def test_generate_ai_analysis_task_ticker_not_found(mock_analyzer_class, mock_session_local):
    db = _make_session()
    mock_session_local.return_value = db
    
    mock_analyzer_instance = MagicMock()
    # Return None for data to simulate not found
    mock_analyzer_instance.get_historical_indicators.return_value = None
    mock_analyzer_class.return_value = mock_analyzer_instance
    
    result = generate_ai_analysis_task("INVALID")
    
    assert result["status"] == "error"
    assert result["message"] == "Ticker not found"
