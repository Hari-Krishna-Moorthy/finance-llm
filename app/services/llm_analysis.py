import os
import google.generativeai as genai

def generate_swing_trade_setup(ticker: str, current_data: dict) -> str:
    """
    Generates an AI-driven swing trade setup using Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY not set in environment variables. Please add it to your .env file."
        
    genai.configure(api_key=api_key)
    
    # We use a standard stable model
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""You are a professional swing-trading analyst.

Analyze the stock {ticker} using ONLY the CURRENT market price and latest candle data provided below.

IMPORTANT RULES:
- Never use outdated entry prices.
- Ignore historical entry zones if current market price has already moved far away.
- All calculations MUST start from the latest live/current price.
- If the suggested entry is more than 8% away from current price, recalculate the setup completely.
- Use current trend, support/resistance, ATR, EMA, RSI, MACD, and volume.
- Generate a realistic trade setup for TODAY'S price.

Return the following:

1. Current Price
2. Market Trend (Bullish/Bearish/Neutral)
3. Nearest Support
4. Nearest Resistance
5. Suggested Entry Price
6. Stop Loss
7. Take Profit Target
8. Risk Per Share
9. Reward Per Share
10. Risk-to-Reward Ratio
11. Position Size Formula
12. Breakout Confirmation Level
13. Confidence Score (0-100)

CALCULATION RULES:

For LONG trades:
- Entry must be near current market price or breakout level.
- Stop loss must be below nearest support or ATR structure.
- Target should be based on resistance extension or measured move.

Use these formulas:
Risk = Entry - StopLoss
Reward = Target - Entry
RR = Reward / Risk
Position Size = AccountRisk / RiskPerShare

VALIDATION:
- Reject setups where stop loss is more than 15% away unless explicitly marked as high-risk.
- Reject targets producing RR below 1.5.
- If RSI > 70, warn that stock is overbought.
- If price is near resistance, require breakout confirmation.

OUTPUT FORMAT:

You MUST return the output EXACTLY as a Markdown table. Do NOT add any preamble or text before the table.
For the "Support", "Resistance", "Entry", "Stop Loss", and "Target" rows, you MUST include a brief comment explaining the rationale (e.g., "(EMA10)", "(Recent swing low)", "(Breakout level)").

| Metric | Value & Comments |
| :--- | :--- |
| **Current Price** | $ |
| **Trend** |  |
| **Support** | $ (comment) |
| **Resistance** | $ (comment) |
| **Entry** | $ (comment) |
| **Stop Loss** | $ (comment) |
| **Target** | $ (comment) |
| **Risk** | $ |
| **Reward** | $ |
| **RR** |  |
| **Suggested Position Size** |  |
| **Trade Type** |  |
| **Confidence** | /100 |

### Reasoning
(Provide your concise professional trading language reasoning here, below the table.)

LATEST TECHNICAL DATA FOR {ticker}:
Current Price: ${current_data.get('Close', 'N/A')}
EMA10: {current_data.get('EMA10', 'N/A')}
EMA20: {current_data.get('EMA20', 'N/A')}
SMA50: {current_data.get('SMA50', 'N/A')}
SMA200: {current_data.get('SMA200', 'N/A')}
RSI (14): {current_data.get('RSI', 'N/A')}
MACD: {current_data.get('MACD', 'N/A')}
MACD Signal: {current_data.get('MACD_Signal', 'N/A')}
Relative Volume: {current_data.get('VolRatio', 'N/A')}
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating analysis: {str(e)}"
