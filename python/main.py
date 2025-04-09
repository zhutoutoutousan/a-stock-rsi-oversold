import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- Configuration ---
# Define a list of tickers to scan (add more as needed)
# Example: Major US indices, some tech stocks, etc.
TICKERS = [
    "^GSPC",  # S&P 500
    "^IXIC",  # Nasdaq Composite
    "^DJI",   # Dow Jones Industrial Average
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Alphabet (Google)
    "AMZN",   # Amazon
    "NVDA",   # Nvidia
    "TSLA",   # Tesla
    "BTC-USD",# Bitcoin (Example of non-stock instrument)
    "ETH-USD", # Ethereum
]

RSI_PERIOD = 14
OVERSOLD_THRESHOLD = 30
TIME_PERIODS = {
    "Daily": {"interval": "1d", "period": "1y"},
    "Weekly": {"interval": "1wk", "period": "5y"},
    "Monthly": {"interval": "1mo", "period": "max"} # Use max available for monthly
}

# List to store stocks that meet the criteria
oversold_stocks = []

# --- Main Logic ---
print(f"Scanning {len(TICKERS)} tickers...")

for ticker_symbol in TICKERS:
    print(f" Checking {ticker_symbol}...")
    try:
        ticker_data = yf.Ticker(ticker_symbol)
        is_oversold_all = True # Assume oversold on all timeframes initially

        for name, params in TIME_PERIODS.items():
            # Fetch historical data
            hist = ticker_data.history(period=params["period"], interval=params["interval"])

            if hist.empty:
                print(f"  Could not fetch {name} data for {ticker_symbol}. Skipping timeframe.")
                is_oversold_all = False # Cannot be oversold if data is missing
                break # No need to check other timeframes if one fails

            # Calculate RSI
            # Ensure the index is a DatetimeIndex, required by pandas_ta
            hist.index = pd.to_datetime(hist.index)
            hist.ta.rsi(length=RSI_PERIOD, append=True) # Appends RSI_14 column

            # Check if the latest RSI is available and below the threshold
            if f'RSI_{RSI_PERIOD}' not in hist.columns or hist[f'RSI_{RSI_PERIOD}'].isnull().all():
                 print(f"  Could not calculate {name} RSI for {ticker_symbol}. Skipping timeframe.")
                 is_oversold_all = False
                 break

            latest_rsi = hist[f'RSI_{RSI_PERIOD}'].iloc[-1]

            if latest_rsi > OVERSOLD_THRESHOLD:
                # If RSI is not oversold on this timeframe, stop checking this ticker
                is_oversold_all = False
                break
            else:
                 print(f"  {name} RSI: {latest_rsi:.2f} (Oversold)")


        # If the loop completed without breaking (i.e., oversold on all checked timeframes)
        if is_oversold_all:
            print(f" *** {ticker_symbol} is oversold on Daily, Weekly, and Monthly charts! ***")
            oversold_stocks.append(ticker_symbol)

    except Exception as e:
        print(f"  Error processing {ticker_symbol}: {e}")
        # Continue to the next ticker even if one fails

# --- Output Results ---
print("--- Scan Complete ---")
if oversold_stocks:
    print("Stocks/Instruments oversold on Daily, Weekly, and Monthly charts:")
    for stock in oversold_stocks:
        print(f"- {stock}")
else:
    print("No stocks/instruments found to be oversold on all three timeframes.")
