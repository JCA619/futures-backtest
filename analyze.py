import pandas as pd
import numpy as np
import json
import os

def parse_time_to_session(entry_time_str):
    """
    Classifies a trade entry time string into a trading session.
    Assumes entry_time_str is in America/New_York timezone.
    """
    try:
        dt = pd.to_datetime(entry_time_str, utc=True).tz_convert('America/New_York')
        hour = dt.hour
        minute = dt.minute
        
        # Convert to time of day in minutes for precise checks
        time_in_mins = hour * 60 + minute
        
        # Define session bounds in minutes from midnight
        london_start = 3 * 60        # 03:00
        london_end = 8 * 60          # 08:00
        pre_market_start = 8 * 60    # 08:00
        pre_market_end = 9 * 60 + 30 # 09:30
        ny_morning_start = 9 * 60 + 30 # 09:30
        ny_morning_end = 12 * 60     # 12:00
        ny_lunch_start = 12 * 60     # 12:00
        ny_lunch_end = 13 * 60 + 30  # 13:30
        ny_afternoon_start = 13 * 60 + 30 # 13:30
        ny_afternoon_end = 16 * 60   # 16:00
        post_market_start = 16 * 60  # 16:00
        post_market_end = 18 * 60    # 18:00
        
        if london_start <= time_in_mins < london_end:
            return "London Session"
        elif pre_market_start <= time_in_mins < pre_market_end:
            return "NY Pre-Market"
        elif ny_morning_start <= time_in_mins < ny_morning_end:
            return "NY Morning"
        elif ny_lunch_start <= time_in_mins < ny_lunch_end:
            return "NY Lunch"
        elif ny_afternoon_start <= time_in_mins < ny_afternoon_end:
            return "NY Afternoon"
        elif post_market_start <= time_in_mins < post_market_end:
            return "Post-Market"
        else:
            return "Globex Overnight"
    except Exception as e:
        return "Unknown"

def compute_drawdown(equity_curve):
    """
    Computes maximum drawdown of the equity curve in points.
    """
    equity = np.array(equity_curve)
    if len(equity) == 0:
        return 0.0
    cum_max = np.maximum.accumulate(equity)
    drawdowns = cum_max - equity
    return float(np.max(drawdowns))

def analyze_results(trade_log_df, output_json_path):
    """
    Analyzes backtest results and saves metrics to a JSON file.
    """
    if trade_log_df.empty:
        # Save empty structure
        empty_data = {
            "summary": {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_profit": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_drawdown": 0.0,
                "optimal_hour": "N/A",
                "optimal_session": "N/A"
            },
            "hourly_stats": [],
            "session_stats": [],
            "equity_curve": [],
            "trades": []
        }
        with open(output_json_path, 'w') as f:
            json.dump(empty_data, f, indent=4)
        return
    
    # 1. Parse Datetime to timezone-aware timestamps and local hours
    trade_log_df['entry_time_dt'] = pd.to_datetime(trade_log_df['entry_time'], utc=True).dt.tz_convert('America/New_York')
    trade_log_df['hour'] = trade_log_df['entry_time_dt'].dt.hour
    trade_log_df['session'] = trade_log_df['entry_time'].apply(parse_time_to_session)
    
    # 2. Cumulative Equity Curve
    trade_log_df = trade_log_df.sort_values('entry_time_dt').reset_index(drop=True)
    trade_log_df['cum_pnl'] = trade_log_df['pnl'].cumsum()
    equity_curve = [0.0] + list(trade_log_df['cum_pnl'].values)
    
    # Formulate equity curve for chart: list of dicts
    equity_chart_data = [{"time": "Start", "pnl": 0.0}]
    for index, row in trade_log_df.iterrows():
        equity_chart_data.append({
            "time": str(row['entry_time']),
            "pnl": float(row['cum_pnl'])
        })
        
    # 3. Summary Stats
    total_trades = len(trade_log_df)
    wins = trade_log_df[trade_log_df['win'] == 1]
    losses = trade_log_df[trade_log_df['win'] == 0]
    
    win_rate = float(len(wins) / total_trades) if total_trades > 0 else 0.0
    net_profit = float(trade_log_df['pnl'].sum())
    
    gross_profit = float(wins['pnl'].sum())
    gross_loss = float(abs(losses['pnl'].sum()))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
    if np.isinf(profit_factor):
        profit_factor = 999.0  # Cap infinity representation
        
    avg_win = float(wins['pnl'].mean()) if len(wins) > 0 else 0.0
    avg_loss = float(losses['pnl'].mean()) if len(losses) > 0 else 0.0
    max_dd = compute_drawdown(equity_curve)
    
    # 4. Hourly Aggregation
    hourly_groups = trade_log_df.groupby('hour')
    hourly_stats = []
    
    # Pre-populate all 24 hours so the chart has placeholders
    for h in range(24):
        if h in hourly_groups.groups:
            group = hourly_groups.get_group(h)
            h_wins = group[group['win'] == 1]
            h_losses = group[group['win'] == 0]
            
            h_gp = float(h_wins['pnl'].sum())
            h_gl = float(abs(h_losses['pnl'].sum()))
            h_pf = float(h_gp / h_gl) if h_gl > 0 else 999.0 if h_gp > 0 else 0.0
            
            hourly_stats.append({
                "hour": int(h),
                "total_trades": int(len(group)),
                "win_rate": float(len(h_wins) / len(group)),
                "net_profit": float(group['pnl'].sum()),
                "profit_factor": h_pf if not np.isinf(h_pf) else 999.0,
                "avg_pnl": float(group['pnl'].mean())
            })
        else:
            hourly_stats.append({
                "hour": int(h),
                "total_trades": 0,
                "win_rate": 0.0,
                "net_profit": 0.0,
                "profit_factor": 0.0,
                "avg_pnl": 0.0
            })
            
    # Find optimal hour
    valid_hours = [h for h in hourly_stats if h['total_trades'] >= 5]
    if valid_hours:
        optimal_hour_obj = max(valid_hours, key=lambda x: x['net_profit'])
        optimal_hour = f"{optimal_hour_obj['hour']}:00 (PnL: {optimal_hour_obj['net_profit']:.1f} pts)"
    else:
        optimal_hour = "N/A (Insufficient Trades)"
        
    # 5. Session Aggregation
    session_groups = trade_log_df.groupby('session')
    session_stats = []
    
    sessions_to_track = [
        "London Session", "NY Pre-Market", "NY Morning", 
        "NY Lunch", "NY Afternoon", "Post-Market", "Globex Overnight"
    ]
    
    for sess in sessions_to_track:
        if sess in session_groups.groups:
            group = session_groups.get_group(sess)
            s_wins = group[group['win'] == 1]
            s_losses = group[group['win'] == 0]
            
            s_gp = float(s_wins['pnl'].sum())
            s_gl = float(abs(s_losses['pnl'].sum()))
            s_pf = float(s_gp / s_gl) if s_gl > 0 else 999.0 if s_gp > 0 else 0.0
            
            session_stats.append({
                "session": sess,
                "total_trades": int(len(group)),
                "win_rate": float(len(s_wins) / len(group)),
                "net_profit": float(group['pnl'].sum()),
                "profit_factor": s_pf if not np.isinf(s_pf) else 999.0,
                "avg_pnl": float(group['pnl'].mean())
            })
        else:
            session_stats.append({
                "session": sess,
                "total_trades": 0,
                "win_rate": 0.0,
                "net_profit": 0.0,
                "profit_factor": 0.0,
                "avg_pnl": 0.0
            })
            
    # Find optimal session
    valid_sessions = [s for s in session_stats if s['total_trades'] >= 5]
    if valid_sessions:
        optimal_sess_obj = max(valid_sessions, key=lambda x: x['net_profit'])
        optimal_session = f"{optimal_sess_obj['session']} (PnL: {optimal_sess_obj['net_profit']:.1f} pts)"
    else:
        optimal_session = "N/A"
        
    # Build complete package
    final_data = {
        "summary": {
            "total_trades": int(total_trades),
            "win_rate": float(win_rate),
            "net_profit": float(net_profit),
            "profit_factor": float(profit_factor),
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss),
            "max_drawdown": float(max_dd),
            "optimal_hour": optimal_hour,
            "optimal_session": optimal_session
        },
        "hourly_stats": hourly_stats,
        "session_stats": session_stats,
        "equity_curve": equity_chart_data,
        "trades": trade_log_df.drop(columns=['entry_time_dt']).to_dict(orient='records')
    }
    
    # Save to JSON
    with open(output_json_path, 'w') as f:
        json.dump(final_data, f, indent=4)
        
    print(f"Successfully processed {total_trades} trades. Metrics saved to {output_json_path}")
    print(f"Overall Win Rate: {win_rate*100:.1f}%, Net Profit: {net_profit:.1f} points, Profit Factor: {profit_factor:.2f}")
    print(f"Optimal Trading Hour: {optimal_hour}")
    print(f"Optimal Session: {optimal_session}")
