import os
import pandas as pd
from download_data import download_data
from backtest import detect_fvgs_and_backtest
from analyze import analyze_results

def run_pipeline():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    dashboard_data_dir = os.path.join(base_dir, 'data')
    os.makedirs(dashboard_data_dir, exist_ok=True)
    
    # 1. Download data
    # Check if files already exist to save API calls, but download if not
    hourly_csv = os.path.join(data_dir, 'NQ_hourly.csv')
    daily_csv = os.path.join(data_dir, 'NQ_daily.csv')
    
    if not os.path.exists(hourly_csv) or not os.path.exists(daily_csv):
        download_data()
    else:
        print("Data files already exist. Skipping download. If you want fresh data, delete the files in the 'data/' directory.")
        
    # 2. Verify files exist
    if not os.path.exists(hourly_csv):
        print(f"Error: {hourly_csv} is missing. Cannot proceed.")
        return
    if not os.path.exists(daily_csv):
        print(f"Error: {daily_csv} is missing. Cannot proceed.")
        return
        
    # 3. Load Datasets
    print("Loading data for analysis...")
    hourly_df = pd.read_csv(hourly_csv)
    daily_df = pd.read_csv(daily_csv)
    
    print(f"Hourly data rows: {len(hourly_df)}")
    print(f"Daily data rows: {len(daily_df)}")
    
    # 4. Run Intraday Multi-Parameter Matrix
    # We pre-compute backtests for different parameter configurations for the hourly data
    fvg_sizes = [0.0002, 0.0005, 0.0010]  # 0.02%, 0.05%, 0.10%
    reward_ratios = [1.5, 2.0, 3.0]
    
    print("Generating Hourly Parameter Matrix...")
    for size in fvg_sizes:
        for rr in reward_ratios:
            print(f"Running Hourly backtest for Size: {size:.4f}, RR: {rr:.1f}...")
            trades = detect_fvgs_and_backtest(
                hourly_df, 
                min_fvg_size_pct=size, 
                reward_ratio=rr
            )
            output_name = f"results_hourly_{size:.4f}_{rr:.1f}.json"
            output_path = os.path.join(dashboard_data_dir, output_name)
            analyze_results(trades, output_path)
            
    # 5. Run Daily Timeframe Backtest (Full 5 years!)
    # Since daily data has larger moves, we use larger FVG size percentages
    print("Running Daily backtest...")
    daily_df['Datetime'] = pd.to_datetime(daily_df['Date']) # Align datetime name
    daily_sizes = [0.001, 0.003, 0.005]  # 0.1%, 0.3%, 0.5%
    daily_rrs = [1.5, 2.0, 3.0]
    
    for size in daily_sizes:
        for rr in daily_rrs:
            print(f"Running Daily backtest for Size: {size:.3f}, RR: {rr:.1f}...")
            trades = detect_fvgs_and_backtest(
                daily_df, 
                min_fvg_size_pct=size, 
                reward_ratio=rr
            )
            output_name = f"results_daily_{size:.3f}_{rr:.1f}.json"
            output_path = os.path.join(dashboard_data_dir, output_name)
            analyze_results(trades, output_path)
            
    print("All backtests complete. JSON data packages saved in dashboard/data/.")

if __name__ == "__main__":
    run_pipeline()
