import os
from typing import Optional, List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(THIS_DIR, 'stock_data_2025_raw.csv')
IND_CSV = os.path.join(THIS_DIR, 'stock_data_2025_with_indicators.csv')
OUT_DIR = os.path.join(THIS_DIR, 'charts')


def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f'Không tìm thấy file: {path}')
    df = pd.read_csv(path, encoding='utf-8-sig')
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None).dt.normalize()
    return df.sort_values(['symbol', 'time']).reset_index(drop=True)


def ensure_outdir():
    os.makedirs(OUT_DIR, exist_ok=True)


def available_symbols(df: pd.DataFrame) -> List[str]:
    return sorted(df['symbol'].dropna().unique().tolist())


def plot_raw(df_sym: pd.DataFrame, symbol: str, out_path: str):
    # Expect columns: time, open, high, low, close, volume
    df_sym = df_sym.sort_values('time').copy()
    # Drop rows without close
    df_sym = df_sym.dropna(subset=['close'])

    fig = plt.figure(figsize=(12, 6))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.1)

    ax_price = fig.add_subplot(gs[0, 0])
    ax_vol = fig.add_subplot(gs[1, 0], sharex=ax_price)

    # Price line + high/low band
    ax_price.plot(df_sym['time'], df_sym['close'], label='Close', color='#1f77b4', linewidth=1.3)
    if {'high', 'low'}.issubset(df_sym.columns):
        ax_price.fill_between(df_sym['time'], df_sym['low'], df_sym['high'], color='#1f77b4', alpha=0.08, label='High–Low')

    # On-the-fly short SMA to smooth (visual only)
    if 'close' in df_sym.columns:
        sma20 = df_sym['close'].rolling(20).mean()
        ax_price.plot(df_sym['time'], sma20, label='SMA 20 (viz)', color='#ff7f0e', linewidth=1.0, alpha=0.9)

    ax_price.set_title(f'{symbol} — Giá và Khối lượng (RAW)')
    ax_price.set_ylabel('Giá')
    ax_price.grid(True, linestyle='--', alpha=0.25)
    ax_price.legend(loc='upper left', ncol=3, fontsize=9)

    # Volume bars
    vol = df_sym['volume'] if 'volume' in df_sym.columns else pd.Series(index=df_sym.index, data=np.nan)
    ax_vol.bar(df_sym['time'], vol, color='#2ca02c', alpha=0.6, width=1.0)
    ax_vol.set_ylabel('KL')
    ax_vol.grid(True, linestyle='--', alpha=0.25)

    # Formatting
    for label in ax_vol.get_xticklabels():
        label.set_rotation(0)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_with_indicators(df_sym: pd.DataFrame, symbol: str, out_path: str):
    # Require at least these columns; silently handle missing by skipping
    df_sym = df_sym.sort_values('time').copy()
    df_sym = df_sym.dropna(subset=['close'])

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1.4, 1.4, 1.2], hspace=0.12)

    ax_p = fig.add_subplot(gs[0, 0])
    ax_v = fig.add_subplot(gs[1, 0], sharex=ax_p)
    ax_macd = fig.add_subplot(gs[2, 0], sharex=ax_p)
    ax_rsi = fig.add_subplot(gs[3, 0], sharex=ax_p)

    t = df_sym['time']

    # Panel 1: Price + MAs + Bollinger
    ax_p.plot(t, df_sym['close'], color='#1f77b4', label='Close', linewidth=1.3)
    for col, color, label in [
        ('SMA_20', '#ff7f0e', 'SMA 20'),
        ('SMA_50', '#2ca02c', 'SMA 50'),
        ('EMA_20', '#9467bd', 'EMA 20'),
    ]:
        if col in df_sym.columns:
            ax_p.plot(t, df_sym[col], color=color, label=label, linewidth=1.0)

    if {'BB_upper', 'BB_lower'}.issubset(df_sym.columns):
        ax_p.fill_between(t, df_sym['BB_lower'], df_sym['BB_upper'], color='#1f77b4', alpha=0.08, label='Bollinger')

    ax_p.set_title(f'{symbol} — Giá + MA/EMA + Bollinger')
    ax_p.set_ylabel('Giá')
    ax_p.grid(True, linestyle='--', alpha=0.25)
    ax_p.legend(loc='upper left', ncol=4, fontsize=9)

    # Panel 2: Volume + OBV
    if 'volume' in df_sym.columns:
        ax_v.bar(t, df_sym['volume'], color='#2ca02c', alpha=0.6, width=1.0, label='Volume')
    if 'OBV' in df_sym.columns:
        ax_v2 = ax_v.twinx()
        ax_v2.plot(t, df_sym['OBV'], color='#8c564b', linewidth=1.0, label='OBV')
        ax_v2.set_ylabel('OBV')
        ax_v2.grid(False)
        # Build combined legend
        lines1, labels1 = ax_v.get_legend_handles_labels()
        lines2, labels2 = ax_v2.get_legend_handles_labels()
        ax_v.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)
    ax_v.set_ylabel('KL')
    ax_v.grid(True, linestyle='--', alpha=0.25)

    # Panel 3: MACD
    if {'MACD', 'MACD_signal', 'MACD_diff'}.issubset(df_sym.columns):
        ax_macd.plot(t, df_sym['MACD'], color='#1f77b4', label='MACD', linewidth=1.0)
        ax_macd.plot(t, df_sym['MACD_signal'], color='#ff7f0e', label='Signal', linewidth=1.0)
        ax_macd.bar(t, df_sym['MACD_diff'], color=np.where(df_sym['MACD_diff']>=0, '#2ca02c', '#d62728'), alpha=0.6, width=1.0, label='Hist')
        ax_macd.axhline(0, color='gray', linewidth=0.8, alpha=0.6)
        ax_macd.set_ylabel('MACD')
        ax_macd.legend(loc='upper left', ncol=3, fontsize=9)
    ax_macd.grid(True, linestyle='--', alpha=0.25)

    # Panel 4: RSI + Stochastic
    if 'RSI_14' in df_sym.columns:
        ax_rsi.plot(t, df_sym['RSI_14'], color='#1f77b4', label='RSI 14', linewidth=1.0)
    if 'RSI_7' in df_sym.columns:
        ax_rsi.plot(t, df_sym['RSI_7'], color='#2ca02c', alpha=0.7, label='RSI 7', linewidth=0.9)
    if 'Stoch_K' in df_sym.columns:
        ax_rsi.plot(t, df_sym['Stoch_K'], color='#ff7f0e', alpha=0.7, label='%K', linewidth=0.9)
    if 'Stoch_D' in df_sym.columns:
        ax_rsi.plot(t, df_sym['Stoch_D'], color='#9467bd', alpha=0.7, label='%D', linewidth=0.9)
    ax_rsi.axhline(70, color='red', linestyle='--', linewidth=0.8, alpha=0.6)
    ax_rsi.axhline(30, color='green', linestyle='--', linewidth=0.8, alpha=0.6)
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel('RSI/Stoch')
    ax_rsi.set_xlabel('Thời gian')
    ax_rsi.legend(loc='upper left', ncol=4, fontsize=9)
    ax_rsi.grid(True, linestyle='--', alpha=0.25)

    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def visualize(raw_csv: str = RAW_CSV, ind_csv: str = IND_CSV, symbol: Optional[str] = None):
    ensure_outdir()
    raw = load_csv(raw_csv)
    ind = load_csv(ind_csv)

    # Determine symbols to render
    syms = [symbol] if symbol else sorted(set(available_symbols(raw)) | set(available_symbols(ind)))

    for sym in syms:
        df_raw_sym = raw[raw['symbol'] == sym].copy()
        df_ind_sym = ind[ind['symbol'] == sym].copy()

        if df_raw_sym.empty and df_ind_sym.empty:
            print(f'Bỏ qua {sym}: không có dữ liệu trong file CSV.')
            continue

        # Clip to common date range if both are present (for visual coherence)
        if not df_raw_sym.empty and not df_ind_sym.empty:
            tmin = max(df_raw_sym['time'].min(), df_ind_sym['time'].min())
            tmax = min(df_raw_sym['time'].max(), df_ind_sym['time'].max())
            df_raw_sym = df_raw_sym[(df_raw_sym['time'] >= tmin) & (df_raw_sym['time'] <= tmax)].copy()
            df_ind_sym = df_ind_sym[(df_ind_sym['time'] >= tmin) & (df_ind_sym['time'] <= tmax)].copy()

        # Plot RAW
        if not df_raw_sym.empty:
            out_raw = os.path.join(OUT_DIR, f'{sym}_raw.png')
            plot_raw(df_raw_sym, sym, out_raw)
            print(f'Đã lưu: {out_raw}')

        # Plot WITH INDICATORS
        if not df_ind_sym.empty:
            out_ind = os.path.join(OUT_DIR, f'{sym}_indicators.png')
            plot_with_indicators(df_ind_sym, sym, out_ind)
            print(f'Đã lưu: {out_ind}')


if __name__ == '__main__':
    # Đọc biến môi trường để chọn symbol nếu muốn, ví dụ: SYMBOL=ACB python visualize_stock.py
    sym = os.environ.get('SYMBOL')
    visualize(symbol=sym)
