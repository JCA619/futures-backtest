"""
run_remaining.py — Processes ES and YM only (NQ already done).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from backtest import detect_fvgs_and_backtest
from analyze import analyze_results

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

INSTRUMENTS = {
    'ES': {'file': 'es1-1m.csv', 'name': 'E-mini S&P 500'},
    'YM': {'file': 'ym1-1m.csv', 'name': 'E-mini Dow Jones'},
}

def load_raw_data(filepath):
    print(f"  Loading {filepath}...")
    df = pd.read_csv(filepath, header=None,
        names=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Contract'],
        parse_dates=['Datetime'])
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    if df['Datetime'].dt.tz is None:
        df['Datetime'] = df['Datetime'].dt.tz_localize('UTC')
    df['Datetime'] = df['Datetime'].dt.tz_convert('America/New_York')
    df = df.sort_values('Datetime').reset_index(drop=True)
    print(f"  Loaded {len(df):,} rows. Range: {df['Datetime'].iloc[0]} -> {df['Datetime'].iloc[-1]}")
    return df

def filter_last_n_years(df, years=3):
    cutoff = df['Datetime'].max() - pd.DateOffset(years=years)
    filtered = df[df['Datetime'] >= cutoff].copy().reset_index(drop=True)
    print(f"  Filtered to last {years} years: {len(filtered):,} rows")
    return filtered

def resample_ohlcv(df, timeframe):
    df_indexed = df.set_index('Datetime')
    resampled = df_indexed.resample(timeframe).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna(subset=['Open']).reset_index()
    print(f"  Resampled to {timeframe}: {len(resampled):,} bars")
    return resampled

def run_instrument(symbol, df_1m):
    print(f"\n{'='*60}")
    print(f"Processing {symbol} ({INSTRUMENTS[symbol]['name']})")
    print(f"{'='*60}")
    
    df_recent = filter_last_n_years(df_1m, years=3)
    
    timeframes = {
        '5min': {'tf_label': '5m', 'fvg_sizes': [0.0002, 0.0005, 0.0010], 'label': '5-Minute'},
        '15min': {'tf_label': '15m', 'fvg_sizes': [0.0003, 0.0007, 0.0015], 'label': '15-Minute'},
        '1h': {'tf_label': '1h', 'fvg_sizes': [0.0005, 0.0010, 0.0020], 'label': 'Hourly'},
    }
    reward_ratios = [1.5, 2.0, 3.0]
    
    for tf_key, tf_config in timeframes.items():
        print(f"\n--- {tf_config['label']} ---")
        df_tf = resample_ohlcv(df_recent, tf_key)
        if len(df_tf) < 100:
            print(f"  Skipping — not enough bars")
            continue
        for size in tf_config['fvg_sizes']:
            for rr in reward_ratios:
                out_name = f"results_{symbol}_{tf_config['tf_label']}_{size:.4f}_{rr:.1f}.json"
                out_path = os.path.join(DATA_DIR, out_name)
                print(f"  {out_name}...", end=' ', flush=True)
                trades = detect_fvgs_and_backtest(df_tf, min_fvg_size_pct=size, reward_ratio=rr)
                analyze_results(trades, out_path)
                print(f"done ({len(trades)} trades)")

def main():
    print("="*60)
    print("IFVG Backtester — Processing ES and YM")
    print("="*60)
    for symbol, info in INSTRUMENTS.items():
        filepath = os.path.join(DATA_DIR, info['file'])
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found. Skipping.")
            continue
        df_1m = load_raw_data(filepath)
        run_instrument(symbol, df_1m)
    print("\n" + "="*60)
    print("All backtests complete!")
    print("="*60)

if __name__ == "__main__":
    main()
