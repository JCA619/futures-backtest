"""
run_new_data.py — Processes the raw 1-minute futures CSVs (NQ, ES, YM),
resamples to multiple timeframes, runs the IFVG backtest across a parameter
matrix, and outputs JSON results for the dashboard.
"""
import os
import pandas as pd
import numpy as np
from backtest import detect_fvgs_and_backtest
from analyze import analyze_results

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Instrument definitions
INSTRUMENTS = {
    'NQ': {
        'file': 'nq1-1m.csv',
        'name': 'E-mini NASDAQ 100',
        'point_value': 20.0
    },
    'ES': {
        'file': 'es1-1m.csv',
        'name': 'E-mini S&P 500',
        'point_value': 50.0
    },
    'YM': {
        'file': 'ym1-1m.csv',
        'name': 'E-mini Dow Jones',
        'point_value': 5.0
    }
}

def load_raw_data(filepath):
    """Load headerless 1-minute CSV: datetime, open, high, low, close, volume, contract"""
    print(f"  Loading {filepath}...")
    df = pd.read_csv(
        filepath,
        header=None,
        names=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Contract'],
        parse_dates=['Datetime']
    )
    # Drop any blank rows
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    
    # Ensure timezone aware (data is UTC+00:00) then convert to NY
    if df['Datetime'].dt.tz is None:
        df['Datetime'] = df['Datetime'].dt.tz_localize('UTC')
    df['Datetime'] = df['Datetime'].dt.tz_convert('America/New_York')
    
    df = df.sort_values('Datetime').reset_index(drop=True)
    print(f"  Loaded {len(df):,} rows. Range: {df['Datetime'].iloc[0]} → {df['Datetime'].iloc[-1]}")
    return df

def filter_last_n_years(df, years=3):
    """Keep only the last N years of data."""
    cutoff = df['Datetime'].max() - pd.DateOffset(years=years)
    filtered = df[df['Datetime'] >= cutoff].copy().reset_index(drop=True)
    print(f"  Filtered to last {years} years: {len(filtered):,} rows. Range: {filtered['Datetime'].iloc[0]} → {filtered['Datetime'].iloc[-1]}")
    return filtered

def resample_ohlcv(df, timeframe):
    """
    Resample 1-minute OHLCV data to a higher timeframe.
    timeframe: '5min', '15min', '1h', '4h', '1D'
    """
    df_indexed = df.set_index('Datetime')
    resampled = df_indexed.resample(timeframe).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna(subset=['Open'])
    
    resampled = resampled.reset_index()
    print(f"  Resampled to {timeframe}: {len(resampled):,} bars")
    return resampled

def run_instrument_backtests(symbol, df_1m, years=3):
    """Run a full parameter matrix of IFVG backtests for one instrument."""
    print(f"\n{'='*60}")
    print(f"Processing {symbol} ({INSTRUMENTS[symbol]['name']})")
    print(f"{'='*60}")
    
    # Filter to last N years
    df_recent = filter_last_n_years(df_1m, years=years)
    
    # Resample to multiple timeframes
    timeframes = {
        '5min': {'tf_label': '5m', 'fvg_sizes': [0.0002, 0.0005, 0.0010], 'label': '5-Minute'},
        '15min': {'tf_label': '15m', 'fvg_sizes': [0.0003, 0.0007, 0.0015], 'label': '15-Minute'},
        '1h': {'tf_label': '1h', 'fvg_sizes': [0.0005, 0.0010, 0.0020], 'label': 'Hourly'},
    }
    
    reward_ratios = [1.5, 2.0, 3.0]
    
    for tf_key, tf_config in timeframes.items():
        print(f"\n--- Resampling to {tf_config['label']} ---")
        df_tf = resample_ohlcv(df_recent, tf_key)
        
        if len(df_tf) < 100:
            print(f"  Skipping {tf_key} — not enough bars ({len(df_tf)})")
            continue
        
        for size in tf_config['fvg_sizes']:
            for rr in reward_ratios:
                print(f"  Backtest: {symbol} {tf_config['label']} | FVG Size: {size:.4f} | RR: {rr:.1f}...")
                trades = detect_fvgs_and_backtest(df_tf, min_fvg_size_pct=size, reward_ratio=rr)
                
                output_name = f"results_{symbol}_{tf_config['tf_label']}_{size:.4f}_{rr:.1f}.json"
                output_path = os.path.join(DATA_DIR, output_name)
                analyze_results(trades, output_path)

def main():
    print("=" * 60)
    print("IFVG Backtester — Multi-Instrument Pipeline (New Data)")
    print("=" * 60)
    
    for symbol, info in INSTRUMENTS.items():
        filepath = os.path.join(DATA_DIR, info['file'])
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found. Skipping {symbol}.")
            continue
        
        df_1m = load_raw_data(filepath)
        run_instrument_backtests(symbol, df_1m, years=3)
    
    print("\n" + "=" * 60)
    print("All backtests complete! JSON files saved to data/")
    print("=" * 60)

if __name__ == "__main__":
    main()
