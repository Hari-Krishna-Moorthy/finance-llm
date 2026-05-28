import os
from unittest.mock import patch, MagicMock

from app.services.llm_analysis import generate_swing_trade_setup

@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch("app.services.llm_analysis.genai.GenerativeModel")
def test_generate_swing_trade_setup_success(mock_model_class):
    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "| Metric | Value |\n|---|---|\n| Trend | Bullish |"
    mock_instance.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_instance
    
    current_data = {
        'Close': 150.0,
        'EMA10': 148.0,
        'RSI': 65.0
    }
    
    result = generate_swing_trade_setup("AAPL", current_data)
    
    assert "Bullish" in result
    mock_instance.generate_content.assert_called_once()
    
    # Check if prompt included the data
    call_args = mock_instance.generate_content.call_args[0][0]
    assert "AAPL" in call_args
    assert "150.0" in call_args
    assert "148.0" in call_args

@patch.dict(os.environ, clear=True) # Ensure GEMINI_API_KEY is not set
def test_generate_swing_trade_setup_missing_key():
    # If key is missing, should return error message
    current_data = {'Close': 150.0}
    result = generate_swing_trade_setup("AAPL", current_data)
    
    assert "Error: GEMINI_API_KEY not set" in result

@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"})
@patch("app.services.llm_analysis.genai.GenerativeModel")
def test_generate_swing_trade_setup_exception(mock_model_class):
    mock_instance = MagicMock()
    mock_instance.generate_content.side_effect = Exception("API Timeout")
    mock_model_class.return_value = mock_instance
    
    current_data = {'Close': 150.0}
    result = generate_swing_trade_setup("AAPL", current_data)
    
    assert "Error generating analysis" in result
    assert "API Timeout" in result
