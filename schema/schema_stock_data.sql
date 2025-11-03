
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
    