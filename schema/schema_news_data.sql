
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
    