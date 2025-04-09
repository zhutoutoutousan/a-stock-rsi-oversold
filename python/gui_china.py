import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import pandas as pd

# --- Import logic from main_china.py ---
# Note: Ensure main_china.py is structured so functions can be imported.
# We might need to refactor main_china.py slightly if it assumes top-level execution.
# For now, assume functions are importable or copy necessary parts.
try:
    from main_china import (
        generate_specific_prefix_tickers, fetch_stock_data,
        RSI_PERIOD, OVERSOLD_THRESHOLD, OVERBOUGHT_THRESHOLD, TIME_PERIODS
    )
    print("Successfully imported logic from main_china.py")
except ImportError as e:
    print(f"Error importing from main_china.py: {e}")
    print("Please ensure main_china.py is in the same directory and is importable.")
    # As a fallback, copy the necessary functions/constants here if import fails
    # (For brevity, this fallback is not fully implemented here)
    exit() # Exit if import fails for now


# --- GUI Application Class ---
class StockScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("China Stock RSI Scanner - Oversold Status Table")
        self.geometry("800x600")

        self.scan_results_data = {} # Store final results {ticker: {"daily": bool, ...}}
        self.scan_queue = queue.Queue()
        self.is_scanning = False

        # --- Configure Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=3)

        # --- Control Frame ---
        control_frame = ttk.LabelFrame(self, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.scan_button = ttk.Button(control_frame, text="Start Scan", command=self.start_scan_thread)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        # --- Log Frame ---
        log_frame = ttk.LabelFrame(self, text="Log Output", padding="10")
        log_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_area.grid(row=0, column=0, sticky="nsew")
        self.log_area.config(state=tk.DISABLED)

        # --- Results Table Frame ---
        table_frame = ttk.LabelFrame(self, text="Oversold Signals", padding="10")
        table_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.results_table = ttk.Treeview(table_frame,
                                          columns=("ticker", "daily", "weekly", "monthly"),
                                          show="headings")
        self.results_table.grid(row=0, column=0, sticky="nsew")

        self.results_table.heading("ticker", text="Ticker")
        self.results_table.heading("daily", text="Daily Oversold")
        self.results_table.heading("weekly", text="Weekly Oversold")
        self.results_table.heading("monthly", text="Monthly Oversold")

        self.results_table.column("ticker", width=120, anchor=tk.W)
        self.results_table.column("daily", width=100, anchor=tk.CENTER)
        self.results_table.column("weekly", width=100, anchor=tk.CENTER)
        self.results_table.column("monthly", width=110, anchor=tk.CENTER)
        
        table_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_table.yview)
        table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_table['yscrollcommand'] = table_scrollbar.set

        # --- Redirect stdout ---
        self.stdout_redirector = StdoutRedirector(self.log_area)
        # sys.stdout = self.stdout_redirector # Commented out for now, use explicit logging

        # --- Start queue processor ---
        self.after(100, self.process_queue)

    def log(self, message):
        """Appends a message to the log area."""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # Scroll to the end
        self.log_area.config(state=tk.DISABLED)
        self.update_idletasks() # Ensure GUI updates

    def start_scan_thread(self):
        """Starts the stock scanning process in a separate thread."""
        if self.is_scanning:
            self.log("Scan already in progress.")
            return

        self.log("Starting scan...")
        self.is_scanning = True
        self.scan_button.config(text="Scanning...", state=tk.DISABLED)
        for i in self.results_table.get_children():
            self.results_table.delete(i)
        self.scan_results_data.clear()

        # Clear previous table results BEFORE starting thread
        try:
            self.log("Clearing previous table results before scan...")
            count = 0
            items_to_delete = tuple(self.results_table.get_children())
            for i in items_to_delete:
                self.results_table.delete(i)
                count += 1
            self.log(f"Cleared {count} table entries.")
            # No need to clear self.scan_results_data here anymore, as it's not used for bulk population
        except Exception as e_clear:
            self.log(f"Error clearing table before scan: {e_clear}")

        self.scan_thread = threading.Thread(target=self.run_scan, daemon=True)
        self.scan_thread.start()

    def run_scan(self):
        """The actual scanning logic run in the background thread."""
        try:
            sh_prefixes = [600, 601, 603, 688]
            SHANGHAI_TICKERS = generate_specific_prefix_tickers(sh_prefixes, ".SS", range_len=1000)
            sz_prefixes = [0, 1, 2, 3, 300]
            SHENZHEN_TICKERS = generate_specific_prefix_tickers(sz_prefixes, ".SZ", range_len=1000)
            TICKERS = SHANGHAI_TICKERS + SHENZHEN_TICKERS

            self.scan_queue.put(("log", f"Generated {len(SHANGHAI_TICKERS)} Shanghai tickers."))
            self.scan_queue.put(("log", f"Generated {len(SHENZHEN_TICKERS)} Shenzhen tickers."))
            self.scan_queue.put(("log", f"Scanning approximately {len(TICKERS)} potential Chinese tickers..."))
            self.scan_queue.put(("log", f"Looking for Daily RSI <= {OVERSOLD_THRESHOLD}..."))

            processed_count = 0
            found_count = 0
            fetch_errors = 0

            for ticker_symbol in TICKERS:
                if not self.is_scanning:
                     self.scan_queue.put(("log", "Scan cancelled."))
                     break

                processed_count += 1
                if processed_count % 50 == 0:
                    progress_msg = f" Processed {processed_count}/{len(TICKERS)}... Found {found_count} signals. Errors: {fetch_errors}"
                    self.scan_queue.put(("log", progress_msg))
                
                ticker_timeframe_results = {
                    "Daily": {"rsi": None, "oversold": False},
                    "Weekly": {"rsi": None, "oversold": False},
                    "Monthly": {"rsi": None, "oversold": False}
                }
                data_fetch_failed_daily = False

                for name in ["Daily", "Weekly", "Monthly"]:
                    params = TIME_PERIODS[name]
                    hist = fetch_stock_data(ticker_symbol, period=params["period"], interval=params["interval"])

                    if hist is None or hist.empty:
                        if name == "Daily": data_fetch_failed_daily = True
                        continue
                    
                    if len(hist) < RSI_PERIOD:
                        if name == "Daily": data_fetch_failed_daily = True
                        continue

                    hist.index = pd.to_datetime(hist.index)
                    hist['Close'] = pd.to_numeric(hist['Close'], errors='coerce')
                    hist.dropna(subset=['Close'], inplace=True)
                    if hist.empty:
                        if name == "Daily": data_fetch_failed_daily = True
                        continue
                    
                    hist.ta.rsi(length=RSI_PERIOD, append=True)
                    rsi_col = f'RSI_{RSI_PERIOD}'
                    if rsi_col not in hist.columns or hist[rsi_col].isnull().all():
                        if name == "Daily": data_fetch_failed_daily = True
                        continue
                        
                    hist.dropna(subset=[rsi_col], inplace=True)
                    if hist.empty:
                        if name == "Daily": data_fetch_failed_daily = True
                        continue

                    latest_rsi = hist[rsi_col].iloc[-1]
                    ticker_timeframe_results[name]["rsi"] = latest_rsi
                    ticker_timeframe_results[name]["oversold"] = latest_rsi <= OVERSOLD_THRESHOLD
                
                if data_fetch_failed_daily or ticker_timeframe_results["Daily"]["rsi"] is None:
                    continue

                if ticker_timeframe_results["Daily"]["oversold"]:
                    found_count += 1
                    self.scan_queue.put(("log", f"  -> Found signal: {ticker_symbol}"))
                    
                    # Prepare payload for immediate table update
                    row_data = {
                        "ticker": ticker_symbol,
                        "daily": ticker_timeframe_results["Daily"]["oversold"],
                        "weekly": ticker_timeframe_results["Weekly"]["oversold"],
                        "monthly": ticker_timeframe_results["Monthly"]["oversold"]
                    }
                    # Put 'add_row' message onto the queue
                    self.scan_queue.put(("add_row", row_data))

            # --- Scan Finished --- 
            # Send 'scan_complete' message without payload
            self.scan_queue.put(("scan_complete", None)) 

        except Exception as e_run_scan:
            self.scan_queue.put(("log", f"ERROR during scan: {e_run_scan}"))
            import traceback
            self.scan_queue.put(("log", traceback.format_exc()))
            self.scan_queue.put(("scan_complete", None)) 

    def process_queue(self):
        """Processes messages from the background thread."""
        try:
            while True:
                message = self.scan_queue.get_nowait()
                msg_type = message[0]
                payload = message[1]

                if msg_type == "log":
                    self.log(payload)
                    
                elif msg_type == "add_row":
                    # Handle inserting a single row into the table
                    try:
                        if payload and isinstance(payload, dict):
                             ticker = payload.get("ticker")
                             if ticker and not self.results_table.exists(ticker): # Check if ticker ID already exists
                                 daily_status = "Yes" if payload.get("daily", False) else "No"
                                 weekly_status = "Yes" if payload.get("weekly", False) else "No"
                                 monthly_status = "Yes" if payload.get("monthly", False) else "No"
                                 
                                 values_tuple = (ticker, daily_status, weekly_status, monthly_status)
                                 self.log(f"    Adding row: {values_tuple}")
                                 self.results_table.insert("", tk.END, iid=ticker, 
                                                            values=values_tuple)
                                 # Optional: Force update more frequently? Might impact performance.
                                 # self.update_idletasks() 
                             elif ticker and self.results_table.exists(ticker):
                                 self.log(f"    Skipping duplicate ticker: {ticker}")
                        else:
                            self.log(f"Warning: Received invalid payload for add_row: {payload}")
                            
                    except Exception as e_add_row:
                        self.log(f"*** ERROR adding row: {e_add_row} ***")
                        self.log(f"    Payload was: {payload}")
                        import traceback
                        self.log(traceback.format_exc())

                elif msg_type == "scan_complete":
                    # No payload processing needed here anymore
                    self.log("Received scan_complete message.") 
                    # self.scan_results_data = payload # No longer storing bulk data here
                    self.is_scanning = False
                    self.scan_button.config(text="Start Scan", state=tk.NORMAL)
                    self.log("\n--- Scan Complete --- Final table state shown.")
                    # REMOVED table population logic from here
                    
                    # Log final count from table maybe?
                    final_count = len(self.results_table.get_children())
                    self.log(f"Total signals in table: {final_count}")
                    
        except queue.Empty:
            pass # No messages in queue
        finally:
            self.after(100, self.process_queue) # Reschedule


# --- Stdout Redirector (Optional, use explicit logging instead) ---
class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.config(state=tk.NORMAL)
        self.text_space.insert(tk.END, string)
        self.text_space.see(tk.END)
        self.text_space.config(state=tk.DISABLED)
        self.text_space.update_idletasks() # Force update

    def flush(self):
        pass # Required for file-like object


# --- Main Execution ---
if __name__ == "__main__":
    # It might be necessary to adjust main_china.py to prevent
    # it from running its main loop when imported.
    # e.g., wrap its main logic in: if __name__ == "__main__":

    app = StockScannerApp()
    app.mainloop() 