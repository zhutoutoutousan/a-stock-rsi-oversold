import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import queue
import time
import pandas as pd
import yfinance as yf
import json
import os

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

# Define sectors for filtering
SECTORS = {
    # Basic Materials
    "basic-materials": "基础材料",
    "agricultural-inputs": "农业投入",
    "aluminum": "铝",
    "building-materials": "建筑材料",
    "chemicals": "化学品",
    "coking-coal": "焦煤",
    "copper": "铜",
    "gold": "黄金",
    "lumber-wood-production": "木材生产",
    "other-industrial-metals-mining": "其他工业金属矿业",
    "other-precious-metals-mining": "其他贵金属矿业",
    "paper-paper-products": "纸和纸制品",
    "silver": "白银",
    "specialty-chemicals": "特种化学品",
    "steel": "钢铁",
    
    # Communication Services
    "communication-services": "通信服务",
    "advertising-agencies": "广告代理",
    "broadcasting": "广播",
    "electronic-gaming-multimedia": "电子游戏多媒体",
    "entertainment": "娱乐",
    "internet-content-information": "互联网内容信息",
    "publishing": "出版",
    "telecom-services": "电信服务",
    
    # Consumer Cyclical
    "consumer-cyclical": "大消费",
    "apparel-manufacturing": "服装制造",
    "apparel-retail": "服装零售",
    "auto-manufacturers": "汽车制造商",
    "auto-parts": "汽车零部件",
    "auto-truck-dealerships": "汽车卡车经销商",
    "department-stores": "百货商店",
    "footwear-accessories": "鞋类和配饰",
    "furnishings-fixtures-appliances": "家具固定装置和电器",
    "gambling": "赌博",
    "home-improvement-retail": "家居装修零售",
    "internet-retail": "互联网零售",
    "leisure": "休闲",
    "lodging": "住宿",
    "luxury-goods": "奢侈品",
    "packaging-containers": "包装容器",
    "personal-services": "个人服务",
    "recreational-vehicles": "休闲车",
    "residential-construction": "住宅建筑",
    "resorts-casinos": "度假村赌场",
    "restaurants": "餐厅",
    "specialty-retail": "专业零售",
    "textile-manufacturing": "纺织制造",
    "travel-services": "旅游服务",
    
    # Consumer Defensive
    "consumer-defensive": "防御性消费",
    "beverages-brewers": "饮料酿造商",
    "beverages-non-alcoholic": "非酒精饮料",
    "beverages-wineries-distilleries": "酿酒厂和蒸馏厂",
    "confectioners": "糖果商",
    "discount-stores": "折扣店",
    "education-training-services": "教育和培训服务",
    "farm-products": "农产品",
    "food-distribution": "食品分销",
    "grocery-stores": "杂货店",
    "household-personal-products": "家居和个人产品",
    "packaged-foods": "包装食品",
    "tobacco": "烟草",
    
    # Energy
    "energy": "能源",
    "oil-gas-drilling": "石油天然气钻探",
    "oil-gas-e-p": "石油天然气勘探与生产",
    "oil-gas-equipment-services": "石油天然气设备服务",
    "oil-gas-integrated": "综合石油天然气",
    "oil-gas-midstream": "石油天然气中游",
    "oil-gas-refining-marketing": "石油天然气炼化和营销",
    "thermal-coal": "动力煤",
    "uranium": "铀",
    
    # Financial Services
    "financial-services": "金融",
    "asset-management": "资产管理",
    "banks-diversified": "多元化银行",
    "banks-regional": "区域性银行",
    "capital-markets": "资本市场",
    "credit-services": "信贷服务",
    "financial-conglomerates": "金融集团",
    "financial-data-stock-exchanges": "金融数据和证券交易所",
    "insurance-brokers": "保险经纪人",
    "insurance-diversified": "多元化保险",
    "insurance-life": "人寿保险",
    "insurance-property-casualty": "财产和意外保险",
    "insurance-reinsurance": "再保险",
    "insurance-specialty": "专业保险",
    "mortgage-finance": "抵押贷款金融",
    "shell-companies": "空壳公司",
    
    # Healthcare
    "healthcare": "创新药",
    "biotechnology": "生物技术",
    "diagnostics-research": "诊断研究",
    "drug-manufacturers-general": "通用药品制造商",
    "drug-manufacturers-specialty-generic": "专业和仿制药制造商",
    "health-information-services": "健康信息服务",
    "healthcare-plans": "医疗保健计划",
    "medical-care-facilities": "医疗保健设施",
    "medical-devices": "医疗设备",
    "medical-distribution": "医疗分销",
    "medical-instruments-supplies": "医疗仪器和用品",
    "pharmaceutical-retailers": "药品零售商",
    
    # Industrials
    "industrials": "工业",
    "aerospace-defense": "航空航天和国防",
    "airlines": "航空公司",
    "airports-air-services": "机场和航空服务",
    "building-products-equipment": "建筑产品和设备",
    "business-equipment-supplies": "商业设备和用品",
    "conglomerates": "企业集团",
    "consulting-services": "咨询服务",
    "electrical-equipment-parts": "电气设备和零件",
    "engineering-construction": "工程和建筑",
    "farm-heavy-construction-machinery": "农业和重型建筑机械",
    "industrial-distribution": "工业分销",
    "infrastructure-operations": "基础设施运营",
    "integrated-freight-logistics": "综合货运和物流",
    "marine-shipping": "海运",
    "metal-fabrication": "金属制造",
    "pollution-treatment-controls": "污染处理和控制",
    "railroads": "铁路",
    "rental-leasing-services": "租赁服务",
    "security-protection-services": "安全和保护服务",
    "specialty-business-services": "专业商业服务",
    "specialty-industrial-machinery": "专业工业机械",
    "staffing-employment-services": "人员配备和就业服务",
    "tools-accessories": "工具和配件",
    "trucking": "卡车运输",
    "waste-management": "废物管理",
    
    # Real Estate
    "real-estate": "房地产",
    "real-estate-development": "房地产开发",
    "real-estate-diversified": "多元化房地产",
    "real-estate-services": "房地产服务",
    "reit-diversified": "多元化房地产投资信托",
    "reit-healthcare-facilities": "医疗保健设施房地产投资信托",
    "reit-hotel-motel": "酒店和汽车旅馆房地产投资信托",
    "reit-industrial": "工业房地产投资信托",
    "reit-mortgage": "抵押贷款房地产投资信托",
    "reit-office": "办公房地产投资信托",
    "reit-residential": "住宅房地产投资信托",
    "reit-retail": "零售房地产投资信托",
    "reit-specialty": "专业房地产投资信托",
    
    # Technology
    "technology": "科技",
    "communication-equipment": "通信设备",
    "computer-hardware": "计算机硬件",
    "consumer-electronics": "消费电子",
    "electronic-components": "电子元件",
    "electronics-computer-distribution": "电子和计算机分销",
    "information-technology-services": "信息技术服务",
    "scientific-technical-instruments": "科学和技术仪器",
    "semiconductor-equipment-materials": "半导体设备和材料",
    "semiconductors": "半导体",
    "software-application": "应用软件",
    "software-infrastructure": "基础设施软件",
    "solar": "太阳能",
    
    # Utilities
    "utilities": "电力",
    "utilities-diversified": "多元化公用事业",
    "utilities-independent-power-producers": "独立电力生产商",
    "utilities-regulated-electric": "受监管的电力公用事业",
    "utilities-regulated-gas": "受监管的天然气公用事业",
    "utilities-regulated-water": "受监管的水务公用事业",
    "utilities-renewable": "可再生能源公用事业"
}

# Recommended sectors for trade war conditions
RECOMMENDED_SECTORS = ["consumer-cyclical", "utilities", "healthcare"]

# --- GUI Application Class ---
class StockScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("China Stock RSI Scanner - Oversold Status Table")
        self.geometry("1000x800")  # Increased window size

        self.scan_results_data = {} # Store final results {ticker: {"daily": bool, ...}}
        self.scan_queue = queue.Queue()
        self.is_scanning = False
        self.is_paused = False
        self.processed_tickers = set()  # Track processed tickers for resume functionality
        self.selected_sectors = set()  # Track selected sectors for filtering

        # --- Configure Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=3)
        self.grid_rowconfigure(3, weight=1)  # Add weight for the bottom row

        # --- Control Frame ---
        control_frame = ttk.LabelFrame(self, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.scan_button = ttk.Button(control_frame, text="Start Scan", command=self.start_scan_thread)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(control_frame, text="Pause Scan", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(control_frame, text="Save Progress", command=self.save_progress)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.load_button = ttk.Button(control_frame, text="Load Progress", command=self.load_progress)
        self.load_button.pack(side=tk.LEFT, padx=5)

        # --- Log Frame ---
        log_frame = ttk.LabelFrame(self, text="Log Output", padding="10")
        log_frame.grid(row=1, column=0, rowspan=2, padx=10, pady=5, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)  # Increased height
        self.log_area.grid(row=0, column=0, sticky="nsew")
        self.log_area.config(state=tk.DISABLED)

        # --- Settings Notebook ---
        settings_notebook = ttk.Notebook(self)
        settings_notebook.grid(row=3, column=0, padx=10, pady=5, sticky="nsew", rowspan=3)
        
        # --- Sector Filter Tab ---
        sector_tab = ttk.Frame(settings_notebook)
        settings_notebook.add(sector_tab, text="Sector Filters")
        
        # Create a canvas with scrollbar for sectors
        sector_canvas = tk.Canvas(sector_tab)
        sector_scrollbar = ttk.Scrollbar(sector_tab, orient="vertical", command=sector_canvas.yview)
        self.sector_scrollable_frame = ttk.Frame(sector_canvas)

        self.sector_scrollable_frame.bind(
            "<Configure>",
            lambda e: sector_canvas.configure(scrollregion=sector_canvas.bbox("all"))
        )

        sector_canvas.create_window((0, 0), window=self.sector_scrollable_frame, anchor="nw")
        sector_canvas.configure(yscrollcommand=sector_scrollbar.set)

        # Add sector checkboxes
        self.sector_vars = {}
        
        # Add "Show All Sectors" option at the top
        self.show_all_sectors_var = tk.BooleanVar(value=True)
        show_all_cb = ttk.Checkbutton(self.sector_scrollable_frame, text="显示所有板块 (不筛选)", variable=self.show_all_sectors_var, 
                                     command=self.toggle_sector_filters)
        show_all_cb.pack(anchor="w", padx=5, pady=5)
        
        # Add a separator
        ttk.Separator(self.sector_scrollable_frame, orient="horizontal").pack(fill="x", padx=5, pady=5)
        
        for sector_key, sector_name in SECTORS.items():
            var = tk.BooleanVar()
            self.sector_vars[sector_key] = var
            cb = ttk.Checkbutton(self.sector_scrollable_frame, text=sector_name, variable=var, state=tk.NORMAL)
            cb.pack(anchor="w", padx=5, pady=2)

        # Pack the canvas and scrollbar
        sector_canvas.pack(side="left", fill="both", expand=True)
        sector_scrollbar.pack(side="right", fill="y")

        # Add recommended approach button
        recommended_button = ttk.Button(sector_tab, text="贸易战推荐板块", command=self.apply_recommended_sectors)
        recommended_button.pack(side=tk.BOTTOM, pady=10, fill=tk.X)
        
        # --- Other Settings Tab (placeholder for future settings) ---
        other_settings_tab = ttk.Frame(settings_notebook)
        settings_notebook.add(other_settings_tab, text="Other Settings")
        
        # Add a label to the other settings tab
        ttk.Label(other_settings_tab, text="Additional settings will be added here in future updates.").pack(padx=20, pady=20)

        # --- Results Table Frame ---
        table_frame = ttk.LabelFrame(self, text="Oversold Signals", padding="10")
        table_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.results_table = ttk.Treeview(table_frame,
                                          columns=("ticker", "daily", "weekly", "monthly", "market_cap", "earnings_growth", "sector"),
                                          show="headings")
        self.results_table.grid(row=0, column=0, sticky="nsew")

        self.results_table.heading("ticker", text="Ticker")
        self.results_table.heading("daily", text="Daily Oversold")
        self.results_table.heading("weekly", text="Weekly Oversold")
        self.results_table.heading("monthly", text="Monthly Oversold")
        self.results_table.heading("market_cap", text="Market Cap (亿)")
        self.results_table.heading("earnings_growth", text="Earnings Growth")
        self.results_table.heading("sector", text="Sector")

        self.results_table.column("ticker", width=120, anchor=tk.W)
        self.results_table.column("daily", width=100, anchor=tk.CENTER)
        self.results_table.column("weekly", width=100, anchor=tk.CENTER)
        self.results_table.column("monthly", width=110, anchor=tk.CENTER)
        self.results_table.column("market_cap", width=100, anchor=tk.CENTER)
        self.results_table.column("earnings_growth", width=100, anchor=tk.CENTER)
        self.results_table.column("sector", width=100, anchor=tk.CENTER)
        
        table_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_table.yview)
        table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.results_table['yscrollcommand'] = table_scrollbar.set

        # --- Filtered Results Table Frame ---
        filtered_table_frame = ttk.LabelFrame(self, text="Filtered Oversold Signals", padding="10")
        filtered_table_frame.grid(row=3, column=1, padx=10, pady=10, sticky="nsew")
        filtered_table_frame.grid_rowconfigure(0, weight=1)
        filtered_table_frame.grid_columnconfigure(0, weight=1)

        self.filtered_table = ttk.Treeview(filtered_table_frame,
                                          columns=("ticker", "daily", "weekly", "monthly", "market_cap", "earnings_growth", "sector"),
                                          show="headings")
        self.filtered_table.grid(row=0, column=0, sticky="nsew")

        self.filtered_table.heading("ticker", text="Ticker")
        self.filtered_table.heading("daily", text="Daily Oversold")
        self.filtered_table.heading("weekly", text="Weekly Oversold")
        self.filtered_table.heading("monthly", text="Monthly Oversold")
        self.filtered_table.heading("market_cap", text="Market Cap (亿)")
        self.filtered_table.heading("earnings_growth", text="Earnings Growth")
        self.filtered_table.heading("sector", text="Sector")

        self.filtered_table.column("ticker", width=120, anchor=tk.W)
        self.filtered_table.column("daily", width=100, anchor=tk.CENTER)
        self.filtered_table.column("weekly", width=100, anchor=tk.CENTER)
        self.filtered_table.column("monthly", width=110, anchor=tk.CENTER)
        self.filtered_table.column("market_cap", width=100, anchor=tk.CENTER)
        self.filtered_table.column("earnings_growth", width=100, anchor=tk.CENTER)
        self.filtered_table.column("sector", width=100, anchor=tk.CENTER)
        
        filtered_table_scrollbar = ttk.Scrollbar(filtered_table_frame, orient=tk.VERTICAL, command=self.filtered_table.yview)
        filtered_table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.filtered_table['yscrollcommand'] = filtered_table_scrollbar.set

        # --- Overbought Signals Table Frame ---
        overbought_table_frame = ttk.LabelFrame(self, text="Overbought Signals", padding="10")
        overbought_table_frame.grid(row=4, column=1, padx=10, pady=10, sticky="nsew")
        overbought_table_frame.grid_rowconfigure(0, weight=1)
        overbought_table_frame.grid_columnconfigure(0, weight=1)

        self.overbought_table = ttk.Treeview(overbought_table_frame,
                                          columns=("ticker", "daily", "weekly", "monthly", "market_cap", "earnings_growth", "sector"),
                                          show="headings")
        self.overbought_table.grid(row=0, column=0, sticky="nsew")

        self.overbought_table.heading("ticker", text="Ticker")
        self.overbought_table.heading("daily", text="Daily Overbought")
        self.overbought_table.heading("weekly", text="Weekly Overbought")
        self.overbought_table.heading("monthly", text="Monthly Overbought")
        self.overbought_table.heading("market_cap", text="Market Cap (亿)")
        self.overbought_table.heading("earnings_growth", text="Earnings Growth")
        self.overbought_table.heading("sector", text="Sector")

        self.overbought_table.column("ticker", width=120, anchor=tk.W)
        self.overbought_table.column("daily", width=100, anchor=tk.CENTER)
        self.overbought_table.column("weekly", width=100, anchor=tk.CENTER)
        self.overbought_table.column("monthly", width=110, anchor=tk.CENTER)
        self.overbought_table.column("market_cap", width=100, anchor=tk.CENTER)
        self.overbought_table.column("earnings_growth", width=100, anchor=tk.CENTER)
        self.overbought_table.column("sector", width=100, anchor=tk.CENTER)
        
        overbought_table_scrollbar = ttk.Scrollbar(overbought_table_frame, orient=tk.VERTICAL, command=self.overbought_table.yview)
        overbought_table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.overbought_table['yscrollcommand'] = overbought_table_scrollbar.set

        # --- Filtered Overbought Signals Table Frame ---
        filtered_overbought_table_frame = ttk.LabelFrame(self, text="Filtered Overbought Signals", padding="10")
        filtered_overbought_table_frame.grid(row=5, column=1, padx=10, pady=10, sticky="nsew")
        filtered_overbought_table_frame.grid_rowconfigure(0, weight=1)
        filtered_overbought_table_frame.grid_columnconfigure(0, weight=1)

        self.filtered_overbought_table = ttk.Treeview(filtered_overbought_table_frame,
                                          columns=("ticker", "daily", "weekly", "monthly", "market_cap", "earnings_growth", "sector"),
                                          show="headings")
        self.filtered_overbought_table.grid(row=0, column=0, sticky="nsew")

        self.filtered_overbought_table.heading("ticker", text="Ticker")
        self.filtered_overbought_table.heading("daily", text="Daily Overbought")
        self.filtered_overbought_table.heading("weekly", text="Weekly Overbought")
        self.filtered_overbought_table.heading("monthly", text="Monthly Overbought")
        self.filtered_overbought_table.heading("market_cap", text="Market Cap (亿)")
        self.filtered_overbought_table.heading("earnings_growth", text="Earnings Growth")
        self.filtered_overbought_table.heading("sector", text="Sector")

        self.filtered_overbought_table.column("ticker", width=120, anchor=tk.W)
        self.filtered_overbought_table.column("daily", width=100, anchor=tk.CENTER)
        self.filtered_overbought_table.column("weekly", width=100, anchor=tk.CENTER)
        self.filtered_overbought_table.column("monthly", width=110, anchor=tk.CENTER)
        self.filtered_overbought_table.column("market_cap", width=100, anchor=tk.CENTER)
        self.filtered_overbought_table.column("earnings_growth", width=100, anchor=tk.CENTER)
        self.filtered_overbought_table.column("sector", width=100, anchor=tk.CENTER)
        
        filtered_overbought_table_scrollbar = ttk.Scrollbar(filtered_overbought_table_frame, orient=tk.VERTICAL, command=self.filtered_overbought_table.yview)
        filtered_overbought_table_scrollbar.grid(row=0, column=1, sticky="ns")
        self.filtered_overbought_table['yscrollcommand'] = filtered_overbought_table_scrollbar.set

        # --- Redirect stdout ---
        self.stdout_redirector = StdoutRedirector(self.log_area)
        # sys.stdout = self.stdout_redirector # Commented out for now, use explicit logging

        # --- Start queue processor ---
        self.after(100, self.process_queue)

    def toggle_sector_filters(self):
        """Show or hide sector checkboxes based on the 'Show All Sectors' option."""
        show_all = self.show_all_sectors_var.get()
        
        # Get all checkbuttons in the sector scrollable frame
        for widget in self.sector_scrollable_frame.winfo_children():
            if isinstance(widget, ttk.Checkbutton):
                # Skip the "Show All Sectors" checkbox itself
                if widget.cget("text") == "显示所有板块 (不筛选)":
                    continue
                    
                # Show or hide the checkbox
                if show_all:
                    # When "Show All" is selected, hide all sector checkboxes
                    widget.pack_forget()
                else:
                    # When "Show All" is deselected, show all sector checkboxes
                    widget.pack(anchor="w", padx=5, pady=2)
        
        if show_all:
            self.log("已启用显示所有板块 - 不进行板块筛选")
        else:
            self.log("已禁用显示所有板块 - 请选择要筛选的板块")
            
    def apply_recommended_sectors(self):
        """Apply the recommended sectors for trade war conditions."""
        # Clear all selections
        for sector_key, var in self.sector_vars.items():
            var.set(False)
        
        # Select recommended sectors
        for sector in RECOMMENDED_SECTORS:
            if sector in self.sector_vars:
                self.sector_vars[sector].set(True)
        
        # Disable "Show All Sectors" option
        self.show_all_sectors_var.set(False)
        self.toggle_sector_filters()
        
        self.log("已应用贸易战推荐板块: 大消费、电力、创新药")
        self.log("贸易战下，重点关注:")
        self.log("1. 大消费 - 内需驱动，受贸易战影响较小")
        self.log("2. 电力 - 基础设施，稳定增长")
        self.log("3. 创新药 - 高壁垒，进口替代")

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

        # Get selected sectors
        self.selected_sectors = {sector for sector, var in self.sector_vars.items() if var.get()}
        if self.selected_sectors:
            self.log(f"Filtering by sectors: {', '.join([SECTORS.get(s, s) for s in self.selected_sectors])}")
        else:
            self.log("No sectors selected, scanning all sectors")

        self.log("Starting scan...")
        self.is_scanning = True
        self.is_paused = False
        self.scan_button.config(text="Scanning...", state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL, text="Pause Scan")
        
        # Clear tables only if starting a new scan (not resuming)
        if not self.processed_tickers:
            for i in self.results_table.get_children():
                self.results_table.delete(i)
            for i in self.filtered_table.get_children():
                self.filtered_table.delete(i)
            for i in self.overbought_table.get_children():
                self.overbought_table.delete(i)
            for i in self.filtered_overbought_table.get_children():
                self.filtered_overbought_table.delete(i)
            self.scan_results_data.clear()

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

            # Filter out already processed tickers
            TICKERS = [t for t in TICKERS if t not in self.processed_tickers]

            self.scan_queue.put(("log", f"Generated {len(SHANGHAI_TICKERS)} Shanghai tickers."))
            self.scan_queue.put(("log", f"Generated {len(SHENZHEN_TICKERS)} Shenzhen tickers."))
            self.scan_queue.put(("log", f"Scanning {len(TICKERS)} remaining tickers..."))
            self.scan_queue.put(("log", f"Looking for Daily RSI <= {OVERSOLD_THRESHOLD}..."))

            processed_count = 0
            found_count = 0
            fetch_errors = 0

            for ticker_symbol in TICKERS:
                if not self.is_scanning:
                     self.scan_queue.put(("log", "Scan cancelled."))
                     break

                # Handle pausing
                while self.is_paused and self.is_scanning:
                    time.sleep(0.1)  # Sleep briefly to prevent CPU hogging
                    continue

                processed_count += 1
                self.processed_tickers.add(ticker_symbol)  # Track processed ticker

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
                    ticker_data = yf.Ticker(ticker_symbol)
                    info = ticker_data.info
                    market_cap = info.get('marketCap', 0)
                    market_cap_billion = market_cap / 100000000
                    earnings_growth = info.get('earningsGrowth', 0)
                    sector = info.get('sector', '')
                    
                    row_data = {
                        "ticker": ticker_symbol,
                        "daily": ticker_timeframe_results["Daily"]["oversold"],
                        "weekly": ticker_timeframe_results["Weekly"]["oversold"],
                        "monthly": ticker_timeframe_results["Monthly"]["oversold"],
                        "market_cap": market_cap_billion,
                        "earnings_growth": earnings_growth,
                        "sector": sector
                    }
                    # Put 'add_row' message onto the queue
                    self.scan_queue.put(("add_row", row_data))

                    # Check if the stock meets the filter criteria
                    show_all_sectors = self.show_all_sectors_var.get()
                    if filter_stock_by_market_cap_and_earnings(ticker_data, self.selected_sectors, show_all_sectors):
                        self.scan_queue.put(("add_filtered_row", row_data))

                # Check for overbought conditions
                if ticker_timeframe_results["Daily"]["rsi"] > OVERBOUGHT_THRESHOLD:
                    self.scan_queue.put(("log", f"  -> Found overbought signal: {ticker_symbol}"))
                    row_data = {
                        "ticker": ticker_symbol,
                        "daily": ticker_timeframe_results["Daily"]["rsi"] > OVERBOUGHT_THRESHOLD,
                        "weekly": ticker_timeframe_results["Weekly"]["rsi"] > OVERBOUGHT_THRESHOLD,
                        "monthly": ticker_timeframe_results["Monthly"]["rsi"] > OVERBOUGHT_THRESHOLD,
                        "market_cap": market_cap_billion,
                        "earnings_growth": earnings_growth,
                        "sector": sector
                    }
                    self.scan_queue.put(("add_overbought_row", row_data))
                    show_all_sectors = self.show_all_sectors_var.get()
                    if filter_stock_by_market_cap_and_earnings(ticker_data, self.selected_sectors, show_all_sectors):
                        self.scan_queue.put(("add_filtered_overbought_row", row_data))

            # --- Scan Finished --- 
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
                                 market_cap = payload.get("market_cap", 0)
                                 earnings_growth = payload.get("earnings_growth", 0)
                                 sector = payload.get("sector", "")
                                 values_tuple = (ticker, daily_status, weekly_status, monthly_status, market_cap, earnings_growth, sector)
                                 self.log(f"    Adding row: {values_tuple}")
                                 self.results_table.insert("", tk.END, iid=ticker, values=values_tuple)
                             elif ticker and self.results_table.exists(ticker):
                                 self.log(f"    Skipping duplicate ticker: {ticker}")
                        else:
                            self.log(f"Warning: Received invalid payload for add_row: {payload}")
                    except Exception as e_add_row:
                        self.log(f"*** ERROR adding row: {e_add_row} ***")
                        self.log(f"    Payload was: {payload}")
                        import traceback
                        self.log(traceback.format_exc())

                elif msg_type == "add_filtered_row":
                    # Handle inserting a single row into the filtered table
                    try:
                        if payload and isinstance(payload, dict):
                             ticker = payload.get("ticker")
                             if ticker and not self.filtered_table.exists(ticker): # Check if ticker ID already exists
                                 daily_status = "Yes" if payload.get("daily", False) else "No"
                                 weekly_status = "Yes" if payload.get("weekly", False) else "No"
                                 monthly_status = "Yes" if payload.get("monthly", False) else "No"
                                 market_cap = payload.get("market_cap", 0)
                                 earnings_growth = payload.get("earnings_growth", 0)
                                 sector = payload.get("sector", "")
                                 values_tuple = (ticker, daily_status, weekly_status, monthly_status, market_cap, earnings_growth, sector)
                                 self.log(f"    Adding filtered row: {values_tuple}")
                                 self.filtered_table.insert("", tk.END, iid=ticker, values=values_tuple)
                             elif ticker and self.filtered_table.exists(ticker):
                                 self.log(f"    Skipping duplicate filtered ticker: {ticker}")
                        else:
                            self.log(f"Warning: Received invalid payload for add_filtered_row: {payload}")
                    except Exception as e_add_filtered_row:
                        self.log(f"*** ERROR adding filtered row: {e_add_filtered_row} ***")
                        self.log(f"    Payload was: {payload}")
                        import traceback
                        self.log(traceback.format_exc())

                elif msg_type == "add_overbought_row":
                    # Handle inserting a single row into the overbought table
                    try:
                        if payload and isinstance(payload, dict):
                             ticker = payload.get("ticker")
                             if ticker and not self.overbought_table.exists(ticker): # Check if ticker ID already exists
                                 daily_status = "Yes" if payload.get("daily", False) else "No"
                                 weekly_status = "Yes" if payload.get("weekly", False) else "No"
                                 monthly_status = "Yes" if payload.get("monthly", False) else "No"
                                 market_cap = payload.get("market_cap", 0)
                                 earnings_growth = payload.get("earnings_growth", 0)
                                 sector = payload.get("sector", "")
                                 values_tuple = (ticker, daily_status, weekly_status, monthly_status, market_cap, earnings_growth, sector)
                                 self.log(f"    Adding overbought row: {values_tuple}")
                                 self.overbought_table.insert("", tk.END, iid=ticker, values=values_tuple)
                             elif ticker and self.overbought_table.exists(ticker):
                                 self.log(f"    Skipping duplicate overbought ticker: {ticker}")
                        else:
                            self.log(f"Warning: Received invalid payload for add_overbought_row: {payload}")
                    except Exception as e_add_overbought_row:
                        self.log(f"*** ERROR adding overbought row: {e_add_overbought_row} ***")
                        self.log(f"    Payload was: {payload}")
                        import traceback
                        self.log(traceback.format_exc())

                elif msg_type == "add_filtered_overbought_row":
                    # Handle inserting a single row into the filtered overbought table
                    try:
                        if payload and isinstance(payload, dict):
                             ticker = payload.get("ticker")
                             if ticker and not self.filtered_overbought_table.exists(ticker): # Check if ticker ID already exists
                                 daily_status = "Yes" if payload.get("daily", False) else "No"
                                 weekly_status = "Yes" if payload.get("weekly", False) else "No"
                                 monthly_status = "Yes" if payload.get("monthly", False) else "No"
                                 market_cap = payload.get("market_cap", 0)
                                 earnings_growth = payload.get("earnings_growth", 0)
                                 sector = payload.get("sector", "")
                                 values_tuple = (ticker, daily_status, weekly_status, monthly_status, market_cap, earnings_growth, sector)
                                 self.log(f"    Adding filtered overbought row: {values_tuple}")
                                 self.filtered_overbought_table.insert("", tk.END, iid=ticker, values=values_tuple)
                             elif ticker and self.filtered_overbought_table.exists(ticker):
                                 self.log(f"    Skipping duplicate filtered overbought ticker: {ticker}")
                        else:
                            self.log(f"Warning: Received invalid payload for add_filtered_overbought_row: {payload}")
                    except Exception as e_add_filtered_overbought_row:
                        self.log(f"*** ERROR adding filtered overbought row: {e_add_filtered_overbought_row} ***")
                        self.log(f"    Payload was: {payload}")
                        import traceback
                        self.log(traceback.format_exc())

                elif msg_type == "scan_complete":
                    self.log("Received scan_complete message.") 
                    self.is_scanning = False
                    self.is_paused = False
                    self.scan_button.config(text="Start Scan", state=tk.NORMAL)
                    self.pause_button.config(state=tk.DISABLED, text="Pause Scan")
                    self.log("\n--- Scan Complete --- Final table state shown.")
                    
                    final_count = len(self.results_table.get_children())
                    self.log(f"Total signals in table: {final_count}")
                    
        except queue.Empty:
            pass # No messages in queue
        finally:
            self.after(100, self.process_queue) # Reschedule

    def save_progress(self):
        """Save the current mining progress to a file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Save Mining Progress"
            )
            if not file_path:
                return

            # Collect data from all tables
            data = {
                "processed_tickers": list(self.processed_tickers),
                "oversold_signals": self._get_table_data(self.results_table),
                "filtered_oversold_signals": self._get_table_data(self.filtered_table),
                "overbought_signals": self._get_table_data(self.overbought_table),
                "filtered_overbought_signals": self._get_table_data(self.filtered_overbought_table),
                "selected_sectors": list(self.selected_sectors)
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.log(f"Progress saved to {file_path}")

        except Exception as e:
            self.log(f"Error saving progress: {e}")
            import traceback
            self.log(traceback.format_exc())

    def load_progress(self):
        """Load mining progress from a saved file."""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json")],
                title="Load Mining Progress"
            )
            if not file_path:
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Clear existing tables
            for table in [self.results_table, self.filtered_table, 
                         self.overbought_table, self.filtered_overbought_table]:
                for item in table.get_children():
                    table.delete(item)

            # Restore processed tickers
            self.processed_tickers = set(data.get("processed_tickers", []))

            # Restore selected sectors
            self.selected_sectors = set(data.get("selected_sectors", []))
            for sector_key, var in self.sector_vars.items():
                var.set(sector_key in self.selected_sectors)

            # Restore table data
            self._restore_table_data(self.results_table, data.get("oversold_signals", []))
            self._restore_table_data(self.filtered_table, data.get("filtered_oversold_signals", []))
            self._restore_table_data(self.overbought_table, data.get("overbought_signals", []))
            self._restore_table_data(self.filtered_overbought_table, data.get("filtered_overbought_signals", []))

            self.log(f"Progress loaded from {file_path}")
            self.log(f"Loaded {len(self.processed_tickers)} processed tickers")

        except Exception as e:
            self.log(f"Error loading progress: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _get_table_data(self, table):
        """Extract data from a table widget."""
        data = []
        for item in table.get_children():
            values = table.item(item)['values']
            data.append({
                'ticker': values[0],
                'daily': values[1] == "Yes",
                'weekly': values[2] == "Yes",
                'monthly': values[3] == "Yes",
                'market_cap': float(values[4]) if values[4] else 0,
                'earnings_growth': float(values[5]) if values[5] else 0,
                'sector': values[6] if len(values) > 6 else ""
            })
        return data

    def _restore_table_data(self, table, data):
        """Restore data to a table widget."""
        for item in data:
            values = (
                item['ticker'],
                "Yes" if item['daily'] else "No",
                "Yes" if item['weekly'] else "No",
                "Yes" if item['monthly'] else "No",
                item['market_cap'],
                item['earnings_growth'],
                item.get('sector', '')
            )
            table.insert("", tk.END, iid=item['ticker'], values=values)

    def toggle_pause(self):
        """Toggle between pause and resume states."""
        if self.is_scanning:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_button.config(text="Resume Scan")
                self.log("Scan paused. Click 'Resume Scan' to continue.")
            else:
                self.pause_button.config(text="Pause Scan")
                self.log("Scan resumed.")


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


def filter_stock_by_market_cap_and_earnings(ticker_data, selected_sectors=None, show_all_sectors=False):
    """
    Filter stocks based on market cap (100-300亿), earnings growth, and sector.
    Returns True if the stock meets the criteria, False otherwise.
    
    Args:
        ticker_data: yfinance Ticker object
        selected_sectors: Set of selected sector keys
        show_all_sectors: Boolean indicating whether to show all sectors without filtering
    """
    try:
        info = ticker_data.info
        market_cap = info.get('marketCap', 0)
        # Convert market cap to 亿 (100 million)
        market_cap_billion = market_cap / 100000000
        if not (100 <= market_cap_billion <= 300):
            return False
        # Check for earnings growth (assuming 'earningsGrowth' is available)
        earnings_growth = info.get('earningsGrowth', 0)
        if earnings_growth <= 0:
            return False
            
        # Skip sector filtering if show_all_sectors is True
        if show_all_sectors:
            return True
            
        # Check sector if sectors are selected
        if selected_sectors:
            sector = info.get('sector', '').lower()
            # Map sector to yfinance sector key
            sector_mapping = {
                'consumer cyclical': 'consumer-cyclical',
                'consumer defensive': 'consumer-defensive',
                'financial services': 'financial-services',
                'communication services': 'communication-services',
                'basic materials': 'basic-materials',
                'real estate': 'real-estate'
            }
            sector_key = sector_mapping.get(sector, sector.replace(' ', '-'))
            if sector_key not in selected_sectors:
                return False
                
        return True
    except Exception as e:
        print(f"Error filtering stock: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    # It might be necessary to adjust main_china.py to prevent
    # it from running its main loop when imported.
    # e.g., wrap its main logic in: if __name__ == "__main__":

    app = StockScannerApp()
    app.mainloop() 