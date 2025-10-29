"""
Stock Data Crawler using vnstock library
Lấy dữ liệu giá cổ phiếu từ vnstock cho các mã ACB, BID, VCB, MBB, FPT
Thời gian OUTPUT: từ đầu năm 2025 đến đầu tháng 10/2025 (được CẮT NGHIÊM NGẶT)
Tính toán các chỉ số kỹ thuật: MA, EMA, RSI, MACD, Bollinger Bands, Stochastic, ATR, OBV, etc.

Lưu ý triển khai để khắc phục 2 vấn đề:
1) Đầu ra chỉ trong khoảng [2025-01-01, 2025-10-01], không lẫn dữ liệu 2024/11.
2) Hai file CSV (raw và with_indicators) có cùng số dòng và cùng các ngày/rows (không drop dòng theo ngưỡng NaN).

# PSAR_down    505
# PSAR_up      415
"""

import pandas as pd
from vnstock3 import Vnstock
from datetime import datetime
import time
import ta  # Thư viện Technical Analysis
import numpy as np
import sys
import os

# Danh sách các mã cổ phiếu cần lấy
STOCK_SYMBOLS = ['ACB', 'BID', 'VCB', 'MBB', 'FPT']

# Thời gian OUTPUT cần giữ lại (cắt nghiêm ngặt trước khi lưu)
START_DATE = '2015-10-01'
END_DATE = '2025-10-01'  # inclusive

# Số ngày lùi để tính các chỉ báo dài (vd: SMA_200) nhưng vẫn cắt output đúng range
LOOKBACK_DAYS = 400

# Cấu hình hạn mức và backoff khi bị giới hạn tốc độ (rate limit)
# Nhà cung cấp gợi ý: "thử lại sau 2 giây" => đặt base delay >= 2s
RATE_LIMIT_BASE_DELAY = 2.5  # giây
RATE_LIMIT_MAX_RETRIES = 6   # số lần thử lại tối đa mỗi request
RATE_LIMIT_JITTER = 0.7      # thêm trễ ngẫu nhiên [0, JITTER] để tránh trùng nhịp
CHUNK_DAYS = 365             # tải theo từng khung ngày để giảm xác suất bị chặn

# === Ghi log output ra file bằng cơ chế tee (in ra console đồng thời ghi vào file) ===
class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
            except Exception:
                pass
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass

def setup_logging(log_dir: str = "logs", filename: str | None = None) -> str:
    """Thiết lập ghi log toàn bộ stdout/stderr vào file đồng thời vẫn in ra console.
    Trả về đường dẫn file log.

    - log_dir: thư mục chứa log (mặc định 'logs' cạnh script)
    - filename: tên file log tùy chọn; nếu None sẽ tạo theo timestamp
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stock_data_{ts}.log"
        log_path = os.path.join(log_dir, filename)

        # Mở file ở chế độ line-buffered (buffering=1) để ghi ngay
        log_file = open(log_path, mode="a", encoding="utf-8", buffering=1)

        # Thiết lập tee cho stdout và stderr
        sys.stdout = _Tee(sys.__stdout__, log_file)
        sys.stderr = _Tee(sys.__stderr__, log_file)

        # Ghi header thông tin phiên chạy
        print("=" * 70)
        print(f"LOG file: {log_path}")
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        return log_path
    except Exception as e:
        # Nếu không thể tạo log, vẫn tiếp tục chạy bình thường
        print(f"[WARN] Không thể thiết lập ghi log ra file: {e}")
        return ""

def get_stock_data(symbol, start_date, end_date):
    """
    Lấy dữ liệu lịch sử giá cổ phiếu từ vnstock
    
    Parameters:
    -----------
    symbol : str
        Mã cổ phiếu
    start_date : str
        Ngày bắt đầu (format: YYYY-MM-DD)
    end_date : str
        Ngày kết thúc (format: YYYY-MM-DD)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame chứa dữ liệu giá cổ phiếu
    """
    # Thử nhiều nguồn dữ liệu khác nhau
    sources = ['TCBS', 'VCI', 'MSN']
    
    for source in sources:
        try:
            print(f"Đang lấy dữ liệu cho mã {symbol} từ {source}...")
            
            # Khởi tạo Vnstock
            stock = Vnstock().stock(symbol=symbol, source=source)
            
            # Lấy dữ liệu lịch sử giá theo từng đoạn thời gian nhỏ + retry khi bị rate-limit
            df = fetch_history_with_backoff(stock, start_date, end_date, interval='1D',
                                            chunk_days=CHUNK_DAYS,
                                            max_retries=RATE_LIMIT_MAX_RETRIES,
                                            base_delay=RATE_LIMIT_BASE_DELAY,
                                            jitter=RATE_LIMIT_JITTER)
            
            if df is not None and not df.empty:
                # Thêm cột mã cổ phiếu
                df['symbol'] = symbol
                
                # Đảm bảo cột time là datetime và reset index
                if 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'])
                elif df.index.name == 'time':
                    df = df.reset_index()
                    df['time'] = pd.to_datetime(df['time'])

                # Chuẩn hóa time: bỏ timezone, đưa về 00:00:00 để so sánh ngày
                if pd.api.types.is_datetime64_any_dtype(df['time']):
                    try:
                        # nếu có timezone thì bỏ
                        if getattr(df['time'].dt, 'tz', None) is not None:
                            df['time'] = df['time'].dt.tz_localize(None)
                    except Exception:
                        pass
                    # normalize về ngày
                    df['time'] = df['time'].dt.normalize()
                
                print(f"✓ Lấy thành công {len(df)} dòng dữ liệu cho {symbol} từ {source}")
                return df
            else:
                print(f"  Không có dữ liệu từ {source}, thử nguồn khác...")
                
        except Exception as e:
            print(f"  Lỗi từ {source}: {str(e)}")
            if source == sources[-1]:  # Nếu là nguồn cuối cùng
                print(f"✗ Không thể lấy dữ liệu cho {symbol} từ bất kỳ nguồn nào")
            continue
    
    return None

def collect_all_stock_data(symbols, start_date, end_date):
    """
    Lấy dữ liệu cho tất cả các mã cổ phiếu
    
    Parameters:
    -----------
    symbols : list
        Danh sách các mã cổ phiếu
    start_date : str
        Ngày bắt đầu
    end_date : str
        Ngày kết thúc
    
    Returns:
    --------
    pd.DataFrame
        DataFrame tổng hợp dữ liệu tất cả các mã
    """
    all_data = []
    
    for symbol in symbols:
        df = get_stock_data(symbol, start_date, end_date)
        if df is not None:
            all_data.append(df)
        
        # Delay để tránh quá tải API (theo gợi ý provider, ≥ 2 giây)
        time.sleep(RATE_LIMIT_BASE_DELAY + np.random.random() * RATE_LIMIT_JITTER)
    
    if all_data:
        # Gộp tất cả dữ liệu
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Sắp xếp theo thời gian và mã cổ phiếu
        combined_df = combined_df.sort_values(['time', 'symbol']).reset_index(drop=True)

        # Loại trùng lặp nếu có
        combined_df = combined_df.drop_duplicates(subset=['time', 'symbol'])
        
        return combined_df
    else:
        return None


def clip_date_range(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Cắt DataFrame theo khoảng ngày [start, end] (inclusive) dựa trên cột 'time'."""
    if df is None or df.empty:
        return df
    out = df.copy()
    # Đảm bảo chuẩn hóa time
    out['time'] = pd.to_datetime(out['time']).dt.normalize()
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    mask = (out['time'] >= start_ts) & (out['time'] <= end_ts)
    out = out.loc[mask].copy()
    out = out.sort_values(['time', 'symbol']).drop_duplicates(['time', 'symbol']).reset_index(drop=True)
    return out


def _is_rate_limit_error(err: Exception | str) -> bool:
    """Nhận diện thông báo lỗi rate limit từ nhà cung cấp (TA, VNStock/TCBS,...)."""
    msg = str(err).lower()
    tokens = [
        "rate limit",  # tiếng Anh chung
        "quá nhiều request",  # VN
        "too many requests",
        "thử lại sau",  # VN
        "429",  # HTTP code
        "tcbs"  # nhà cung cấp
    ]
    return any(t in msg for t in tokens)


def _daterange_chunks(start_date: str, end_date: str, chunk_days: int):
    """Sinh các cặp (start, end) theo từng khung chunk_days ngày, bao trùm [start_date, end_date]."""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    cur_start = start
    delta = pd.Timedelta(days=chunk_days)
    while cur_start <= end:
        cur_end = min(cur_start + delta, end)
        yield cur_start.strftime('%Y-%m-%d'), cur_end.strftime('%Y-%m-%d')
        # Tăng 1 ngày để không trùng biên
        cur_start = cur_end + pd.Timedelta(days=1)


def fetch_history_with_backoff(stock, start: str, end: str, interval: str = '1D',
                               chunk_days: int = CHUNK_DAYS,
                               max_retries: int = RATE_LIMIT_MAX_RETRIES,
                               base_delay: float = RATE_LIMIT_BASE_DELAY,
                               jitter: float = RATE_LIMIT_JITTER) -> pd.DataFrame | None:
    """
    Tải dữ liệu lịch sử theo từng khung ngày nhỏ và áp dụng exponential backoff + jitter
    khi gặp rate limit. Gộp kết quả tất cả chunk thành một DataFrame duy nhất.

    Trả về None nếu tất cả chunk đều thất bại.
    """
    frames = []
    total_chunks = 0
    for s, e in _daterange_chunks(start, end, chunk_days):
        total_chunks += 1
        attempt = 0
        while True:
            try:
                print(f"  - Lấy chunk {s} -> {e} ...")
                part = stock.quote.history(start=s, end=e, interval=interval)
                # Tôn trọng khuyến nghị provider: tạm nghỉ sau mỗi request
                time.sleep(base_delay + np.random.random() * jitter)
                if part is not None and not part.empty:
                    frames.append(part)
                else:
                    print("    (trống)")
                break  # chunk thành công hoặc trống thì chuyển chunk tiếp theo
            except Exception as ex:
                attempt += 1
                if _is_rate_limit_error(ex) and attempt <= max_retries:
                    # exponential backoff with jitter
                    delay = (base_delay * (2 ** (attempt - 1))) + (np.random.random() * jitter)
                    delay = min(delay, 60)  # không đợi quá 60s cho mỗi lần backoff
                    print(f"    Gặp rate-limit, thử lại lần {attempt}/{max_retries} sau {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"    Lỗi chunk {s}->{e}: {ex}")
                    break  # bỏ chunk này, chuyển chunk khác

    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    # Chuẩn hóa & sắp xếp
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
    elif df.index.name == 'time':
        df = df.reset_index()
        df['time'] = pd.to_datetime(df['time'])
    # normalize time
    try:
        if getattr(df['time'].dt, 'tz', None) is not None:
            df['time'] = df['time'].dt.tz_localize(None)
    except Exception:
        pass
    df['time'] = df['time'].dt.normalize()
    # Loại trùng lặp và sắp xếp
    if 'symbol' in df.columns:
        df = df.drop_duplicates(subset=['time', 'symbol']).sort_values(['time', 'symbol']).reset_index(drop=True)
    else:
        df = df.drop_duplicates(subset=['time']).sort_values(['time']).reset_index(drop=True)
    print(f"  ✓ Hoàn tất {total_chunks} chunk, tổng {len(df)} dòng")
    return df

def save_to_csv(df, filename='stock_data_2025.csv'):
    """
    Lưu DataFrame vào file CSV
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame cần lưu
    filename : str
        Tên file output
    """
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✓ Đã lưu dữ liệu vào file: {filename}")
        print(f"  - Tổng số dòng: {len(df)}")
        print(f"  - Các cột: {', '.join(df.columns.tolist())}")
        print(f"  - Thời gian: {df['time'].min()} đến {df['time'].max()}")
    except Exception as e:
        print(f"✗ Lỗi khi lưu file: {str(e)}")

def calculate_technical_indicators(df):
    """
    Tính toán các chỉ số kỹ thuật cho dữ liệu cổ phiếu
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame chứa dữ liệu OHLCV (Open, High, Low, Close, Volume)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame với các chỉ số kỹ thuật đã được thêm vào
    """
    # Tạo bản sao để không ảnh hưởng đến DataFrame gốc
    df = df.copy()
    
    # Đảm bảo dữ liệu được sắp xếp theo thời gian
    df = df.sort_values('time').reset_index(drop=True)
    
    print("Đang tính toán chỉ số kỹ thuật...")
    
    # 1. MOVING AVERAGES (Đường trung bình động)
    df['SMA_5'] = ta.trend.sma_indicator(df['close'], window=5)
    df['SMA_10'] = ta.trend.sma_indicator(df['close'], window=10)
    df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50)
    df['SMA_200'] = ta.trend.sma_indicator(df['close'], window=200)
    
    df['EMA_5'] = ta.trend.ema_indicator(df['close'], window=5)
    df['EMA_10'] = ta.trend.ema_indicator(df['close'], window=10)
    df['EMA_20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50)
    
    # 2. RSI (Relative Strength Index) - Chỉ số sức mạnh tương đối
    df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)
    df['RSI_7'] = ta.momentum.rsi(df['close'], window=7)
    
    # 3. MACD (Moving Average Convergence Divergence)
    macd = ta.trend.MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_diff'] = macd.macd_diff()
    
    # 4. BOLLINGER BANDS (Dải Bollinger)
    bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_middle'] = bollinger.bollinger_mavg()
    df['BB_lower'] = bollinger.bollinger_lband()
    df['BB_width'] = bollinger.bollinger_wband()
    df['BB_pband'] = bollinger.bollinger_pband()
    
    # 5. STOCHASTIC OSCILLATOR (Chỉ số Stochastic)
    stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
    df['Stoch_K'] = stoch.stoch()
    df['Stoch_D'] = stoch.stoch_signal()
    
    # 6. ATR (Average True Range) - Độ biến động trung bình
    df['ATR_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    
    # 7. ADX (Average Directional Index) - Chỉ số xu hướng
    adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'])
    df['ADX'] = adx.adx()
    df['ADX_pos'] = adx.adx_pos()
    df['ADX_neg'] = adx.adx_neg()
    
    # 8. OBV (On-Balance Volume) - Khối lượng cân bằng
    df['OBV'] = ta.volume.on_balance_volume(df['close'], df['volume'])
    
    # 9. CCI (Commodity Channel Index)
    df['CCI_20'] = ta.trend.cci(df['high'], df['low'], df['close'], window=20)
    
    # 10. Williams %R
    df['Williams_R'] = ta.momentum.williams_r(df['high'], df['low'], df['close'], lbp=14)
    
    # 11. MFI (Money Flow Index)
    df['MFI_14'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window=14)
    
    # 12. ROC (Rate of Change) - Tốc độ thay đổi
    df['ROC_10'] = ta.momentum.roc(df['close'], window=10)
    
    # 13. Parabolic SAR
    psar = ta.trend.PSARIndicator(df['high'], df['low'], df['close'])
    df['PSAR'] = psar.psar()
    df['PSAR_up'] = psar.psar_up()
    df['PSAR_down'] = psar.psar_down()
    # Gộp PSAR_up/PSAR_down: trong thư viện ta, thường chỉ một trong hai cột có giá trị tại mỗi hàng,
    # cột còn lại sẽ NaN. Để tiện sử dụng và tránh thiếu dữ liệu, tạo cột hợp nhất không làm mất hàng.
    # - PSAR_merged: lấy giá trị không NaN giữa PSAR_up và PSAR_down
    # - PSAR_side:  1 khi là xu hướng tăng (có PSAR_up), -1 khi là xu hướng giảm (có PSAR_down), 0 nếu cả hai đều NaN
    df['PSAR_merged'] = df['PSAR_up'].combine_first(df['PSAR_down'])
    df['PSAR_side'] = np.select(
        [df['PSAR_up'].notna(), df['PSAR_down'].notna()],
        [1, -1],
        default=0
    )
    # Nếu cột PSAR gốc bị thiếu tại một số hàng, có thể điền bằng giá trị hợp nhất (không drop hàng)
    df['PSAR_filled'] = df['PSAR'].combine_first(df['PSAR_merged'])
    
    # 14. VWAP (Volume Weighted Average Price) - Giá trung bình theo khối lượng
    df['VWAP'] = ta.volume.volume_weighted_average_price(df['high'], df['low'], df['close'], df['volume'])
    
    # 15. Ichimoku Cloud
    ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'])
    df['Ichimoku_a'] = ichimoku.ichimoku_a()
    df['Ichimoku_b'] = ichimoku.ichimoku_b()
    df['Ichimoku_base'] = ichimoku.ichimoku_base_line()
    df['Ichimoku_conv'] = ichimoku.ichimoku_conversion_line()
    
    # 16. Trix
    df['TRIX'] = ta.trend.trix(df['close'], window=15)
    
    # 17. KST (Know Sure Thing)
    kst = ta.trend.KSTIndicator(df['close'])
    df['KST'] = kst.kst()
    df['KST_signal'] = kst.kst_sig()
    
    # 18. Chaikin Money Flow
    df['CMF'] = ta.volume.chaikin_money_flow(df['high'], df['low'], df['close'], df['volume'], window=20)
    
    # 19. Force Index
    df['Force_Index'] = ta.volume.force_index(df['close'], df['volume'], window=13)
    
    # 20. Ease of Movement
    df['EOM'] = ta.volume.ease_of_movement(df['high'], df['low'], df['volume'], window=14)
    
    # 21. Keltner Channel
    keltner = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'])
    df['Keltner_upper'] = keltner.keltner_channel_hband()
    df['Keltner_middle'] = keltner.keltner_channel_mband()
    df['Keltner_lower'] = keltner.keltner_channel_lband()
    
    # 22. Donchian Channel
    donchian = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'])
    df['Donchian_upper'] = donchian.donchian_channel_hband()
    df['Donchian_middle'] = donchian.donchian_channel_mband()
    df['Donchian_lower'] = donchian.donchian_channel_lband()
    
    # 23. Ulcer Index
    df['Ulcer_Index'] = ta.volatility.ulcer_index(df['close'])
    
    # 24. Thêm các chỉ số tự tính
    # Daily Return (Lợi nhuận hàng ngày)
    df['Daily_Return'] = df['close'].pct_change() * 100
    
    # Price Change
    df['Price_Change'] = df['close'] - df['open']
    df['Price_Change_Pct'] = (df['Price_Change'] / df['open']) * 100
    
    # High-Low Range
    df['HL_Range'] = df['high'] - df['low']
    df['HL_Range_Pct'] = (df['HL_Range'] / df['low']) * 100
    
    # Volume Change
    df['Volume_Change_Pct'] = df['volume'].pct_change() * 100
    
    print("✓ Đã tính toán xong các chỉ số kỹ thuật!")
    print(f"  - Số lượng chỉ số đã thêm: {len(df.columns) - 7}")  # Trừ đi các cột gốc
    
    return df

def main():
    """
    Hàm chính để chạy chương trình
    """
    # Thiết lập log trước khi có bất kỳ print nào để bắt trọn output
    setup_logging(log_dir="logs")

    print("=" * 70)
    print("CHƯƠNG TRÌNH LẤY DỮ LIỆU CỔ PHIẾU TỪ VNSTOCK")
    print("=" * 70)
    print(f"Các mã cổ phiếu: {', '.join(STOCK_SYMBOLS)}")
    print(f"Thời gian: {START_DATE} đến {END_DATE}")
    print("=" * 70)
    print()
    
    # 1) Lấy dữ liệu thô đúng khoảng OUTPUT (để đảm bảo file raw chuẩn)
    df_raw = collect_all_stock_data(STOCK_SYMBOLS, START_DATE, END_DATE)
    if df_raw is None or df_raw.empty:
        print("\n✗ Không lấy được dữ liệu nào!")
        print("\n" + "=" * 70)
        print("HOÀN THÀNH!")
        print("=" * 70)
        return

    # Cắt nghiêm ngặt theo khoảng OUTPUT và chuẩn hóa time
    df_raw = clip_date_range(df_raw, START_DATE, END_DATE)
    
    if df_raw is not None and not df_raw.empty:
        # Hiển thị thông tin tổng quan
        print("\n" + "=" * 70)
        print("THỐNG KÊ DỮ LIỆU")
        print("=" * 70)
        print(f"Tổng số dòng (RAW): {len(df_raw)}")
        print(f"\nSố dòng theo từng mã cổ phiếu:")
        print(df_raw['symbol'].value_counts().sort_index())
        
        print(f"\nMẫu dữ liệu (5 dòng đầu):")
        print(df_raw.head())
        
        # 2) Để tính indicators dài (SMA_200...), ta LẤY THÊM LOOKBACK nhưng sẽ CẮT OUTPUT về đúng range
        print("\n" + "=" * 70)
        print("TÍNH TOÁN CHỈ SỐ KỸ THUẬT")
        print("=" * 70)
        lookback_start = (pd.to_datetime(START_DATE) - pd.Timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')
        print(f"Lấy thêm lookback từ: {lookback_start} đến {END_DATE} để tính chỉ báo dài, nhưng output sẽ bị cắt về [{START_DATE}..{END_DATE}].")

        # Lấy dữ liệu extended (lookback) một lần cho tất cả mã
        df_ext = collect_all_stock_data(STOCK_SYMBOLS, lookback_start, END_DATE)
        if df_ext is None or df_ext.empty:
            print("\n✗ Không lấy được dữ liệu lookback, sẽ tính chỉ báo từ dữ liệu RAW hiện có (có thể có NaN đầu kỳ).")
            df_ext = df_raw.copy()
        
        df_with_indicators = []
        for symbol in df_raw['symbol'].unique():
            print(f"\nXử lý mã {symbol}...")
            # Dùng extended để tính chỉ báo, sau đó cắt về đúng range và đảm bảo khớp với RAW rows
            df_symbol_ext = df_ext[df_ext['symbol'] == symbol].copy()
            df_symbol_ext = calculate_technical_indicators(df_symbol_ext)
            # Cắt output theo range yêu cầu
            df_symbol_cut = clip_date_range(df_symbol_ext, START_DATE, END_DATE)
            
            # Đảm bảo bộ rows/time y hệt RAW (inner join theo ['time','symbol'])
            df_raw_sym = df_raw[df_raw['symbol'] == symbol][['time', 'symbol']]
            df_symbol_final = df_symbol_cut.merge(df_raw_sym, on=['time', 'symbol'], how='inner')
            # Sắp xếp cột để time, open,... ở đầu (nếu có)
            base_cols = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
            ordered_cols = [c for c in base_cols if c in df_symbol_final.columns] + [c for c in df_symbol_final.columns if c not in base_cols]
            df_symbol_final = df_symbol_final[ordered_cols]
            df_with_indicators.append(df_symbol_final)
        
        # Gộp lại tất cả các mã
        df_final = pd.concat(df_with_indicators, ignore_index=True)
        df_final = df_final.sort_values(['time', 'symbol']).reset_index(drop=True)
        
        # 3) KHÔNG LỌC THEO NGƯỠNG NaN để giữ NGUYÊN SỐ DÒNG so với RAW
        #    (nếu cần, có thể điền NaN bằng phương pháp khác nhưng KHÔNG DROP DÒNG)
        #    Đồng thời đảm bảo số dòng khớp với RAW
        print("\nĐối chiếu số dòng giữa RAW và WITH_INDICATORS...")
        rows_raw = df_raw.groupby('symbol')['time'].count().sum()
        rows_ind = df_final.groupby('symbol')['time'].count().sum()
        print(f"  - RAW rows: {rows_raw}")
        print(f"  - IND rows: {rows_ind}")
        if rows_raw != rows_ind:
            print("  ! Cảnh báo: số dòng chưa khớp. Sẽ ép khớp lại theo (time,symbol) ở RAW.")
            df_final = df_final.merge(df_raw[['time', 'symbol']], on=['time', 'symbol'], how='right')
            df_final = df_final.sort_values(['time', 'symbol']).reset_index(drop=True)
            print(f"  - IND rows sau khi ép khớp: {len(df_final)}")

        # Theo yêu cầu: không lấy hai cột PSAR_up và PSAR_down (nhiều missing),
        # vẫn giữ PSAR_filled và PSAR_side để dùng phân tích/huấn luyện.
        cols_to_drop = [c for c in ['PSAR_up', 'PSAR_down'] if c in df_final.columns]
        if cols_to_drop:
            df_final = df_final.drop(columns=cols_to_drop)
            print(f"\nLoại bỏ cột ít dữ liệu: {cols_to_drop} (giữ PSAR_filled, PSAR_side)")

        # Lưu vào file CSV (WITH_INDICATORS và RAW) – cùng số dòng, cùng ngày
        save_to_csv(df_final, 'stock_data_2025_with_indicators.csv')
        save_to_csv(df_raw, 'stock_data_2025_raw.csv')
        
        # Hiển thị mẫu dữ liệu sau cùng
        print("\n" + "=" * 70)
        print("MẪU DỮ LIỆU WITH_INDICATORS (5 DÒNG ĐẦU)")
        print("=" * 70)
        print(df_final.head())
        
    print("\n" + "=" * 70)
    print("HOÀN THÀNH!")
    print("=" * 70)

if __name__ == "__main__":
    main()
