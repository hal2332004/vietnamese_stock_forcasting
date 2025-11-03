"""
Script để thiết kế schema và upload dữ liệu lên Supabase
"""

import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Lấy thông tin từ .env
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY')

# Khởi tạo Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_stock_data_table():
    """
    Tạo bảng stock_data với schema phù hợp
    SQL schema cho bảng stock_data
    """
    print("=" * 60)
    print("SCHEMA CHO BẢNG: stock_data")
    print("=" * 60)
    
    schema_sql = """
    CREATE TABLE IF NOT EXISTS stock_data (
        id BIGSERIAL PRIMARY KEY,
        time DATE NOT NULL,
        open DECIMAL(10, 2),
        high DECIMAL(10, 2),
        low DECIMAL(10, 2),
        close DECIMAL(10, 2),
        volume BIGINT,
        ticker VARCHAR(10) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Indexes để tăng performance
        CONSTRAINT unique_stock_date_ticker UNIQUE(time, ticker)
    );
    
    -- Tạo index cho các truy vấn thường dùng
    CREATE INDEX IF NOT EXISTS idx_stock_ticker ON stock_data(ticker);
    CREATE INDEX IF NOT EXISTS idx_stock_time ON stock_data(time);
    CREATE INDEX IF NOT EXISTS idx_stock_ticker_time ON stock_data(ticker, time);
    
    -- Enable Row Level Security (RLS)
    ALTER TABLE stock_data ENABLE ROW LEVEL SECURITY;
    
    -- Tạo policy để cho phép đọc dữ liệu công khai
    CREATE POLICY "Enable read access for all users" ON stock_data
        FOR SELECT USING (true);
    
    -- Tạo policy để chèn dữ liệu (có thể giới hạn sau)
    CREATE POLICY "Enable insert for authenticated users only" ON stock_data
        FOR INSERT WITH CHECK (true);
    """
    
    print(schema_sql)
    print("\n✓ Vui lòng chạy SQL này trong Supabase SQL Editor\n")
    return schema_sql

def create_news_data_table():
    """
    Tạo bảng news_data với schema phù hợp
    SQL schema cho bảng news_data
    """
    print("=" * 60)
    print("SCHEMA CHO BẢNG: news_data")
    print("=" * 60)
    
    schema_sql = """
    CREATE TABLE IF NOT EXISTS news_data (
        id BIGSERIAL PRIMARY KEY,
        date VARCHAR(100),
        year INTEGER,
        ticker VARCHAR(10) NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        source TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Indexes để tăng performance
        CONSTRAINT unique_news_title_ticker UNIQUE(title, ticker, date)
    );
    
    -- Tạo index cho các truy vấn thường dùng
    CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_data(ticker);
    CREATE INDEX IF NOT EXISTS idx_news_date ON news_data(date);
    CREATE INDEX IF NOT EXISTS idx_news_year ON news_data(year);
    CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_data(ticker, date);
    CREATE INDEX IF NOT EXISTS idx_news_ticker_year ON news_data(ticker, year);
    
    -- Tạo Full Text Search index cho title và content
    CREATE INDEX IF NOT EXISTS idx_news_title_search ON news_data USING GIN(to_tsvector('english', title));
    CREATE INDEX IF NOT EXISTS idx_news_content_search ON news_data USING GIN(to_tsvector('english', content));
    
    -- Enable Row Level Security (RLS)
    ALTER TABLE news_data ENABLE ROW LEVEL SECURITY;
    
    -- Tạo policy để cho phép đọc dữ liệu công khai
    CREATE POLICY "Enable read access for all users" ON news_data
        FOR SELECT USING (true);
    
    -- Tạo policy để chèn dữ liệu
    CREATE POLICY "Enable insert for authenticated users only" ON news_data
        FOR INSERT WITH CHECK (true);
    """
    
    print(schema_sql)
    print("\n✓ Vui lòng chạy SQL này trong Supabase SQL Editor\n")
    return schema_sql

def upload_stock_data(csv_path: str, batch_size: int = 1000):
    """
    Upload dữ liệu stock từ CSV lên Supabase
    """
    print(f"\n{'=' * 60}")
    print(f"UPLOADING STOCK DATA")
    print(f"{'=' * 60}\n")
    
    # Đọc CSV
    print(f"📖 Đang đọc file: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"✓ Đã đọc {len(df)} dòng dữ liệu")
    print(f"\nCột trong dataset: {list(df.columns)}")
    print(f"\nMẫu dữ liệu:\n{df.head()}\n")
    
    # Chuẩn bị dữ liệu
    records = []
    for _, row in df.iterrows():
        record = {
            'time': row['time'],
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
            'ticker': row['symbol']  # Map 'symbol' từ CSV sang 'ticker' trong database
        }
        records.append(record)
    
    # Upload theo batch
    total_uploaded = 0
    total_batches = (len(records) + batch_size - 1) // batch_size
    
    print(f"\n🚀 Bắt đầu upload {len(records)} records (chia thành {total_batches} batches)...\n")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        try:
            response = supabase.table('stock_data').insert(batch).execute()
            total_uploaded += len(batch)
            print(f"✓ Batch {batch_num}/{total_batches}: Đã upload {len(batch)} records (Tổng: {total_uploaded}/{len(records)})")
        except Exception as e:
            print(f"✗ Lỗi tại batch {batch_num}: {str(e)}")
            # Tiếp tục với batch tiếp theo
            continue
    
    print(f"\n{'=' * 60}")
    print(f"✅ Hoàn thành! Đã upload {total_uploaded}/{len(records)} records")
    print(f"{'=' * 60}\n")

def upload_news_data(csv_path: str, batch_size: int = 500):
    """
    Upload dữ liệu news từ CSV lên Supabase
    """
    print(f"\n{'=' * 60}")
    print(f"UPLOADING NEWS DATA")
    print(f"{'=' * 60}\n")
    
    # Đọc CSV
    print(f"📖 Đang đọc file: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"✓ Đã đọc {len(df)} dòng dữ liệu")
    print(f"\nCột trong dataset: {list(df.columns)}")
    print(f"\nMẫu dữ liệu:\n{df.head()}\n")
    
    # Chuẩn bị dữ liệu
    records = []
    for _, row in df.iterrows():
        record = {
            'date': str(row['date']) if pd.notna(row['date']) else None,
            'year': int(row['year']) if pd.notna(row['year']) else None,
            'ticker': str(row['ticker']),
            'title': str(row['title']),
            'content': str(row['content']) if pd.notna(row['content']) else None,
            'source': str(row['source']) if pd.notna(row['source']) else None
        }
        records.append(record)
    
    # Upload theo batch
    total_uploaded = 0
    total_batches = (len(records) + batch_size - 1) // batch_size
    
    print(f"\n🚀 Bắt đầu upload {len(records)} records (chia thành {total_batches} batches)...\n")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        try:
            response = supabase.table('news_data').insert(batch).execute()
            total_uploaded += len(batch)
            print(f"✓ Batch {batch_num}/{total_batches}: Đã upload {len(batch)} records (Tổng: {total_uploaded}/{len(records)})")
        except Exception as e:
            print(f"✗ Lỗi tại batch {batch_num}: {str(e)}")
            # Tiếp tục với batch tiếp theo
            continue
    
    print(f"\n{'=' * 60}")
    print(f"✅ Hoàn thành! Đã upload {total_uploaded}/{len(records)} records")
    print(f"{'=' * 60}\n")

def main():
    """
    Main function để chạy toàn bộ quy trình
    """
    print("\n" + "=" * 60)
    print("SUPABASE DATABASE SETUP & UPLOAD")
    print("=" * 60 + "\n")
    
    # Kiểm tra environment variables
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Lỗi: Vui lòng thiết lập SUPABASE_URL và SUPABASE_PUBLISHABLE_KEY trong file .env")
        return
    
    print("✓ Đã kết nối với Supabase")
    print(f"  URL: {SUPABASE_URL}\n")
    
    # Bước 1: Hiển thị SQL schemas
    print("BƯỚC 1: TẠO TABLES")
    print("-" * 60 + "\n")
    
    stock_schema = create_stock_data_table()
    news_schema = create_news_data_table()
    
    # Lưu schemas vào file
    with open('schema_stock_data.sql', 'w', encoding='utf-8') as f:
        f.write(stock_schema)
    with open('schema_news_data.sql', 'w', encoding='utf-8') as f:
        f.write(news_schema)
    
    print(f"✓ Đã lưu schemas vào:")
    print(f"  - schema_stock_data.sql")
    print(f"  - schema_news_data.sql\n")
    
    # Hỏi người dùng có muốn tiếp tục upload không
    response = input("❓ Bạn đã chạy SQL schemas trong Supabase chưa? (y/n): ")
    
    if response.lower() != 'y':
        print("\n⚠️  Vui lòng:")
        print("  1. Mở Supabase Dashboard")
        print("  2. Vào SQL Editor")
        print("  3. Copy và chạy nội dung từ schema_stock_data.sql và schema_news_data.sql")
        print("  4. Sau đó chạy lại script này\n")
        return
    
    # Bước 2: Upload dữ liệu
    print("\nBƯỚC 2: UPLOAD DỮ LIỆU")
    print("-" * 60)
    
    # Đường dẫn tới các file CSV
    stock_csv = './data/stock_data_2025_raw.csv'
    news_csv = './data/stock_market_news_cleaned_merged.csv'
    
    # Upload stock data
    if os.path.exists(stock_csv):
        upload_stock_data(stock_csv)
    else:
        print(f"⚠️  Không tìm thấy file: {stock_csv}")
    
    # Upload news data
    if os.path.exists(news_csv):
        upload_news_data(news_csv)
    else:
        print(f"⚠️  Không tìm thấy file: {news_csv}")
    
    print("\n" + "=" * 60)
    print("🎉 HOÀN THÀNH!")
    print("=" * 60 + "\n")
    print("Bạn có thể xem dữ liệu tại Supabase Dashboard:")
    print(f"{SUPABASE_URL}\n")

if __name__ == "__main__":
    main()
