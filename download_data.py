import os
import yfinance as yf
import pandas as pd

def download_data():
    # Define directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    print("Starting data download for Nasdaq Futures (NQ=F)...")
    
    # 1. Download 2 years of hourly data (yfinance max for 1h)
    print("Downloading 2 years of hourly data...")
    try:
        # NQ=F is the E-mini Nasdaq-100 Futures
        hourly_df = yf.download("NQ=F", period="2y", interval="1h")
        if hourly_df.empty:
            print("Error: Hourly data is empty. Retrying with 730d period...")
            hourly_df = yf.download("NQ=F", period="730d", interval="1h")
            
        if not hourly_df.empty:
            # Flatten multi-index columns if they exist (yfinance sometimes returns multi-index columns)
            if isinstance(hourly_df.columns, pd.MultiIndex):
                hourly_df.columns = [col[0] for col in hourly_df.columns]
                
            # Localize index to New York time (CME/Nasdaq trading is typically aligned with NY time)
            if hourly_df.index.tz is None:
                hourly_df.index = hourly_df.index.tz_localize('UTC')
            hourly_df.index = hourly_df.index.tz_convert('America/New_York')
            
            # Reset index to make Datetime a column
            hourly_df = hourly_df.reset_index()
            hourly_df.rename(columns={hourly_df.columns[0]: 'Datetime'}, inplace=True)
            
            hourly_path = os.path.join(data_dir, 'NQ_hourly.csv')
            hourly_df.to_csv(hourly_path, index=False)
            print(f"Successfully saved hourly data to {hourly_path}. Shape: {hourly_df.shape}")
        else:
            print("Failed to download hourly data.")
    except Exception as e:
        print(f"Exception during hourly download: {e}")
        
    # 2. Download 5 years of daily data
    print("Downloading 5 years of daily data...")
    try:
        daily_df = yf.download("NQ=F", period="5y", interval="1d")
        if not daily_df.empty:
            if isinstance(daily_df.columns, pd.MultiIndex):
                daily_df.columns = [col[0] for col in daily_df.columns]
                
            # Localize daily date index
            if daily_df.index.tz is None:
                # Daily dates typically represent the start of the day in local exchange time
                # We can just format them as YYYY-MM-DD
                pass
            
            daily_df = daily_df.reset_index()
            daily_df.rename(columns={daily_df.columns[0]: 'Date'}, inplace=True)
            
            daily_path = os.path.join(data_dir, 'NQ_daily.csv')
            daily_df.to_csv(daily_path, index=False)
            print(f"Successfully saved daily data to {daily_path}. Shape: {daily_df.shape}")
        else:
            print("Failed to download daily data.")
    except Exception as e:
        print(f"Exception during daily download: {e}")

if __name__ == "__main__":
    download_data()
