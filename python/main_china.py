import yfinance as yf
import pandas_ta as ta
import pandas as pd
import matplotlib.pyplot as plt
import time
import akshare as ak # Import akshare
from datetime import datetime

# --- Configuration ---
# Generate potential Chinese stock tickers based on known prefixes
def generate_prefix_tickers(prefix, suffix, start_num, end_num):
    tickers = []
    # Ensure prefix is treated as string for formatting
    prefix_str = str(prefix)
    for i in range(start_num, end_num + 1):
        # Combine prefix and the rest of the number, padded to 6 digits total
        tickers.append(f"{i:06d}{suffix}")
    return tickers

def generate_specific_prefix_tickers(prefixes, suffix, range_len=1000):
    """Generates tickers like 600000-600999, 601000-601999, etc."""
    all_tickers = []
    for prefix in prefixes:
        start = prefix * (10**(6-len(str(prefix)))) # e.g., 600 * 1000 = 600000
        # Or for 000 prefix, start should be 1
        if prefix == 0:
            start = 1
            end = range_len -1 # e.g., 000001 to 000999
        else:
            end = start + range_len - 1 # e.g., 600000 + 1000 - 1 = 600999
        
        for i in range(start, end + 1):
             all_tickers.append(f"{i:06d}{suffix}")
    return all_tickers

# Shanghai Stock Exchange (.SS)
sh_prefixes = [600, 601, 603, 688]
SHANGHAI_TICKERS = generate_specific_prefix_tickers(sh_prefixes, ".SS", range_len=1000) # Generate 1000 tickers for each prefix

# Shenzhen Stock Exchange (.SZ)
sz_prefixes = [0, 1, 2, 3, 300] # 0 maps to 000xxx, 1 to 001xxx, etc. 300 maps to 300xxx
# Adjust range_len for 300 prefix if needed, assuming 1000 for now
SHENZHEN_TICKERS = generate_specific_prefix_tickers(sz_prefixes, ".SZ", range_len=1000)

TICKERS = SHANGHAI_TICKERS + SHENZHEN_TICKERS

print(f"Generated {len(SHANGHAI_TICKERS)} Shanghai tickers.")
print(f"Generated {len(SHENZHEN_TICKERS)} Shenzhen tickers.")

RSI_PERIOD = 14
OVERSOLD_THRESHOLD = 30
OVERBOUGHT_THRESHOLD = 70 # Define overbought threshold
TIME_PERIODS = {
    "Daily": {"interval": "1d", "period": "1y"},
    "Weekly": {"interval": "1wk", "period": "5y"},
    "Monthly": {"interval": "1mo", "period": "max"}
}

# Dictionary to store historical data for plotting oversold stocks
oversold_stocks_data = {}

# --- Helper Function for Data Fetching ---
def fetch_stock_data(ticker_symbol, period, interval):
    """Fetches stock data first using yfinance, then akshare as fallback."""
    print(f"    Attempting yfinance for {ticker_symbol} ({interval})...")
    try:
        # 1. Try yfinance
        ticker_data_yf = yf.Ticker(ticker_symbol)
        hist = ticker_data_yf.history(period=period, interval=interval)
        if not hist.empty:
            print(f"      yfinance SUCCESS for {ticker_symbol} ({interval})")
            return hist
        else:
            print(f"      yfinance FAILED (empty) for {ticker_symbol} ({interval}), trying akshare...")

    except Exception as e_yf:
        print(f"      yfinance FAILED (error: {e_yf}) for {ticker_symbol} ({interval}), trying akshare...")

    # 2. Try akshare if yfinance failed
    try:
        # Convert yfinance ticker symbol (e.g., 600000.SS) to akshare symbol (e.g., sh600000)
        parts = ticker_symbol.split('.')
        if len(parts) != 2:
             print(f"      akshare FAILED: Invalid ticker format for akshare: {ticker_symbol}")
             return pd.DataFrame() # Return empty DataFrame
        
        num = parts[0]
        exch = parts[1].lower()
        if exch not in ["ss", "sz"]:
             print(f"      akshare FAILED: Unknown exchange for akshare: {exch}")
             return pd.DataFrame()
        
        ak_symbol = f"{exch}{num}"
        
        # Convert yfinance period/interval to akshare parameters
        # akshare uses start_date and end_date, and period ('daily', 'weekly', 'monthly')
        end_date = datetime.now().strftime('%Y%m%d')
        # Rough mapping from yfinance periods to start dates (adjust as needed)
        if period == "1y":
            start_date = (datetime.now() - pd.Timedelta(days=365)).strftime('%Y%m%d')
        elif period == "5y":
            start_date = (datetime.now() - pd.Timedelta(days=365*5)).strftime('%Y%m%d')
        elif period == "max":
            start_date = "19900101" # Or an earlier date if needed
        else:
             start_date = (datetime.now() - pd.Timedelta(days=30)).strftime('%Y%m%d') # Default fallback

        ak_period_map = {"1d": "daily", "1wk": "weekly", "1mo": "monthly"}
        ak_period = ak_period_map.get(interval)
        
        if not ak_period:
             print(f"      akshare FAILED: Unsupported interval for akshare: {interval}")
             return pd.DataFrame()

        print(f"    Attempting akshare for {ak_symbol} ({ak_period})...")
        # Fetch data using stock_zh_a_hist
        hist_ak = ak.stock_zh_a_hist(symbol=ak_symbol, period=ak_period, start_date=start_date, end_date=end_date, adjust="qfq")
        
        if not hist_ak.empty:
            print(f"      akshare SUCCESS for {ak_symbol} ({ak_period})")
            # Standardize columns and index to match yfinance output
            hist_ak.rename(columns={
                '日期': 'Date', 
                '开盘': 'Open', 
                '收盘': 'Close', 
                '最高': 'High', 
                '最低': 'Low', 
                '成交量': 'Volume'
                # Add other columns if needed, e.g., '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'
            }, inplace=True)
            hist_ak['Date'] = pd.to_datetime(hist_ak['Date'])
            hist_ak.set_index('Date', inplace=True)
            # Select only the columns yfinance usually provides for consistency
            yf_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            return hist_ak[[col for col in yf_cols if col in hist_ak.columns]]
        else:
            print(f"      akshare FAILED (empty) for {ak_symbol} ({ak_period})")
            return pd.DataFrame() # Return empty if akshare also fails
            
    except Exception as e_ak:
        print(f"      akshare FAILED (error: {e_ak}) for {ak_symbol} ({ak_period})")
        return pd.DataFrame() # Return empty if akshare fails

# --- Main Execution Function ---
def run_china_scan_and_plot():
    # --- Configuration (Ticker Generation inside the function now) ---
    # Shanghai Stock Exchange (.SS)
    sh_prefixes = [600, 601, 603, 688]
    SHANGHAI_TICKERS = generate_specific_prefix_tickers(sh_prefixes, ".SS", range_len=1000) # Generate 1000 tickers for each prefix

    # Shenzhen Stock Exchange (.SZ)
    sz_prefixes = [0, 1, 2, 3, 300] # 0 maps to 000xxx, 1 to 001xxx, etc. 300 maps to 300xxx
    SHENZHEN_TICKERS = generate_specific_prefix_tickers(sz_prefixes, ".SZ", range_len=1000)

    TICKERS = SHANGHAI_TICKERS + SHENZHEN_TICKERS

    print(f"Generated {len(SHANGHAI_TICKERS)} Shanghai tickers.")
    print(f"Generated {len(SHENZHEN_TICKERS)} Shenzhen tickers.")

    # Dictionary to store historical data for plotting oversold stocks
    oversold_stocks_data = {}

    # --- Main Logic ---
    print(f"Scanning approximately {len(TICKERS)} potential Chinese tickers (using yfinance + akshare fallback)...")

    processed_count = 0
    found_count = 0
    fetch_errors = 0

    for ticker_symbol in TICKERS:
        processed_count += 1
        # Optional: time.sleep(0.1)
        if processed_count % 100 == 0:
            print(f" Processed {processed_count}/{len(TICKERS)} tickers... Found {found_count} oversold so far. Fetch errors: {fetch_errors}")

        # --- Data Fetching Loop ---
        is_oversold_all = True
        history_data = {} # Store history for this ticker temporarily
        data_fetched_successfully = True

        for name, params in TIME_PERIODS.items():
            # Use the helper function to get data
            hist = fetch_stock_data(ticker_symbol, period=params["period"], interval=params["interval"])
            
            if hist is None or hist.empty:
                # Don't print error here for direct run, handled by fetch_stock_data logging
                # print(f"  Could not fetch {name} data for {ticker_symbol} from either source. Skipping ticker.")
                is_oversold_all = False
                data_fetched_successfully = False # Mark failure for this ticker
                fetch_errors += 1
                break 
                
            # --- RSI Calculation ---
            if len(hist) < RSI_PERIOD:
                # print(f"  Insufficient {name} data ({len(hist)} points) for {ticker_symbol} after fetching. Skipping timeframe.")
                is_oversold_all = False
                break

            hist.index = pd.to_datetime(hist.index)
            hist['Close'] = pd.to_numeric(hist['Close'], errors='coerce')
            hist.dropna(subset=['Close'], inplace=True) 

            if hist.empty:
                # print(f"  No valid 'Close' data for {name} - {ticker_symbol}. Skipping timeframe.")
                is_oversold_all = False
                break

            hist.ta.rsi(length=RSI_PERIOD, append=True)

            rsi_col = f'RSI_{RSI_PERIOD}'
            if rsi_col not in hist.columns or hist[rsi_col].isnull().all():
                # print(f"  Could not calculate {name} RSI for {ticker_symbol}. Skipping timeframe.")
                is_oversold_all = False
                break

            hist.dropna(subset=[rsi_col], inplace=True)
            if hist.empty:
                # print(f"  Not enough data after RSI calculation for {name} - {ticker_symbol}. Skipping timeframe.")
                is_oversold_all = False
                break

            latest_rsi = hist[rsi_col].iloc[-1]
            history_data[name] = hist # Store history for potential plotting

            # --- Log RSI Status --- 
            status = "Neutral"
            if latest_rsi <= OVERSOLD_THRESHOLD:
                status = f"Oversold (<= {OVERSOLD_THRESHOLD})"
            elif latest_rsi >= OVERBOUGHT_THRESHOLD:
                status = f"Overbought (>= {OVERBOUGHT_THRESHOLD})"
            
            # Print status for the current timeframe when run directly
            print(f"    {ticker_symbol} - {name} RSI: {latest_rsi:.2f} ({status})")
            
            # --- Check if Oversold Condition Met for This Timeframe --- 
            if latest_rsi > OVERSOLD_THRESHOLD:
                # print(f"      -> Not oversold on {name}. Skipping remaining timeframes for {ticker_symbol}.")
                is_oversold_all = False # Mark as not meeting the 'oversold on all' criteria
                break # Stop checking other timeframes 

        # --- Check if Oversold on All Timeframes --- 
        if data_fetched_successfully and is_oversold_all:
            print(f"\n *** {ticker_symbol} is oversold on Daily, Weekly, and Monthly charts! Adding to results. ***\n")
            oversold_stocks_data[ticker_symbol] = history_data
            found_count += 1

    # --- Output Results & Plotting ---
    print(f"\n--- Scan Complete --- Processed {processed_count} tickers.")

    if oversold_stocks_data:
        print(f"Found {len(oversold_stocks_data)} stocks/instruments oversold on Daily, Weekly, and Monthly charts:")
        oversold_tickers = list(oversold_stocks_data.keys())
        for ticker_symbol in oversold_tickers:
            print(f"- {ticker_symbol}")

        print("\nGenerating RSI plots for oversold stocks...")
        # Use matplotlib (ensure imported)
        import matplotlib.pyplot as plt 
        for ticker_symbol, history_dict in oversold_stocks_data.items():
            fig, axes = plt.subplots(len(TIME_PERIODS), 1, figsize=(12, 8), sharex=False)
            fig.suptitle(f'RSI ({RSI_PERIOD}) for {ticker_symbol} (Oversold on D/W/M)', fontsize=16)
            rsi_col = f'RSI_{RSI_PERIOD}'

            for i, (name, hist) in enumerate(history_dict.items()):
                ax = axes[i]
                if rsi_col not in hist.columns: continue # Skip if RSI col missing

                ax.plot(hist.index, hist[rsi_col], label=f'{name} RSI')
                ax.axhline(OVERSOLD_THRESHOLD, color='red', linestyle='--', linewidth=1, label=f'Oversold ({OVERSOLD_THRESHOLD})')
                ax.axhline(OVERBOUGHT_THRESHOLD, color='green', linestyle=':', linewidth=1, label=f'Overbought ({OVERBOUGHT_THRESHOLD})') 
                ax.set_title(f'{name} Chart ({TIME_PERIODS[name]["interval"]})')
                ax.set_ylabel('RSI')
                ax.legend()
                ax.grid(True)
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

            plt.tight_layout(rect=[0, 0.03, 1, 0.95]) 
            plot_filename = f"{ticker_symbol}_rsi_plot.png"
            try:
                plt.savefig(plot_filename)
                print(f" Saved plot: {plot_filename}")
            except Exception as e:
                print(f" Could not save plot {plot_filename}: {e}")
            plt.close(fig) 

        print("\nPlotting complete. Check for .png files in the script directory.")

    else:
        print("No Chinese stocks found to be oversold on all three timeframes within the scanned range.")

# --- Guard for Direct Execution ---
if __name__ == "__main__":
    # This block only runs when main_china.py is executed directly
    run_china_scan_and_plot()

# (Remove original main logic from the bottom of the file if it exists outside the function) 