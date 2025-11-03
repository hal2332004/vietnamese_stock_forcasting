"""
Script để lấy dữ liệu từ Supabase theo ticker
Hỗ trợ 5 loại ticker: ACB, VCB, MBB, FPT, BID
"""

import os
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# Load environment variables
load_dotenv()

# Lấy thông tin từ .env
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY')

# Khởi tạo Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Danh sách 5 ticker được hỗ trợ
SUPPORTED_TICKERS = ['ACB', 'VCB', 'MBB', 'FPT', 'BID']


class SupabaseDataFetcher:
    """Class để lấy dữ liệu từ Supabase"""
    
    def __init__(self):
        self.supabase = supabase
        
    def get_stock_data_by_ticker(
        self, 
        ticker: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu giá cổ phiếu theo ticker
        
        Args:
            ticker: Mã cổ phiếu (ACB, VCB, MBB, FPT, BID)
            start_date: Ngày bắt đầu (format: 'YYYY-MM-DD'), None = không giới hạn
            end_date: Ngày kết thúc (format: 'YYYY-MM-DD'), None = không giới hạn
            limit: Số lượng records tối đa, None = lấy tất cả
            
        Returns:
            DataFrame chứa dữ liệu giá cổ phiếu
        """
        ticker = ticker.upper()
        if ticker not in SUPPORTED_TICKERS:
            print(f"⚠️  Ticker '{ticker}' không được hỗ trợ. Chỉ hỗ trợ: {', '.join(SUPPORTED_TICKERS)}")
            return pd.DataFrame()
        
        print(f"\n📊 Đang lấy dữ liệu stock cho ticker: {ticker}")
        
        # Xây dựng query
        query = self.supabase.table('stock_data').select('*').eq('ticker', ticker)
        
        # Thêm filter theo ngày
        if start_date:
            query = query.gte('time', start_date)
            print(f"  - Từ ngày: {start_date}")
        if end_date:
            query = query.lte('time', end_date)
            print(f"  - Đến ngày: {end_date}")
        
        # Thêm limit
        if limit:
            query = query.limit(limit)
            print(f"  - Giới hạn: {limit} records")
        
        # Sắp xếp theo thời gian
        query = query.order('time', desc=False)
        
        # Thực hiện query
        try:
            response = query.execute()
            data = response.data
            
            if not data:
                print(f"  ⚠️  Không tìm thấy dữ liệu cho ticker {ticker}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            print(f"  ✓ Đã lấy {len(df)} records")
            return df
            
        except Exception as e:
            print(f"  ✗ Lỗi khi lấy dữ liệu: {str(e)}")
            return pd.DataFrame()
    
    def get_news_data_by_ticker(
        self, 
        ticker: str,
        year: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu tin tức theo ticker
        
        Args:
            ticker: Mã cổ phiếu (ACB, VCB, MBB, FPT, BID)
            year: Năm (2015-2025), None = không giới hạn
            start_date: Ngày bắt đầu (format string), None = không giới hạn
            end_date: Ngày kết thúc (format string), None = không giới hạn
            limit: Số lượng records tối đa, None = lấy tất cả
            
        Returns:
            DataFrame chứa dữ liệu tin tức
        """
        ticker = ticker.upper()
        if ticker not in SUPPORTED_TICKERS:
            print(f"⚠️  Ticker '{ticker}' không được hỗ trợ. Chỉ hỗ trợ: {', '.join(SUPPORTED_TICKERS)}")
            return pd.DataFrame()
        
        print(f"\n📰 Đang lấy dữ liệu news cho ticker: {ticker}")
        
        # Xây dựng query
        query = self.supabase.table('news_data').select('*').eq('ticker', ticker)
        
        # Thêm filter theo năm
        if year:
            query = query.eq('year', year)
            print(f"  - Năm: {year}")
        
        # Thêm filter theo ngày (nếu cần search trong cột date)
        if start_date:
            print(f"  - Từ ngày: {start_date}")
        if end_date:
            print(f"  - Đến ngày: {end_date}")
        
        # Thêm limit
        if limit:
            query = query.limit(limit)
            print(f"  - Giới hạn: {limit} records")
        
        # Sắp xếp theo year và date
        query = query.order('year', desc=False)
        
        # Thực hiện query
        try:
            response = query.execute()
            data = response.data
            
            if not data:
                print(f"  ⚠️  Không tìm thấy dữ liệu cho ticker {ticker}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Filter theo date string nếu cần (vì date là VARCHAR)
            if start_date or end_date:
                # Đơn giản hóa: filter sau khi lấy data
                if start_date:
                    df = df[df['date'].str.contains(start_date, na=False)]
                if end_date:
                    df = df[df['date'].str.contains(end_date, na=False)]
            
            print(f"  ✓ Đã lấy {len(df)} records")
            return df
            
        except Exception as e:
            print(f"  ✗ Lỗi khi lấy dữ liệu: {str(e)}")
            return pd.DataFrame()
    
    def get_all_tickers_stock_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit_per_ticker: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Lấy dữ liệu stock cho tất cả 5 ticker
        
        Returns:
            Dictionary với key là ticker, value là DataFrame
        """
        print(f"\n{'=' * 60}")
        print("LẤY DỮ LIỆU STOCK CHO TẤT CẢ TICKER")
        print(f"{'=' * 60}")
        
        results = {}
        for ticker in SUPPORTED_TICKERS:
            df = self.get_stock_data_by_ticker(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                limit=limit_per_ticker
            )
            results[ticker] = df
        
        print(f"\n{'=' * 60}")
        print(f"✅ Hoàn thành! Tổng số ticker: {len(results)}")
        for ticker, df in results.items():
            print(f"  - {ticker}: {len(df)} records")
        print(f"{'=' * 60}\n")
        
        return results
    
    def get_all_tickers_news_data(
        self,
        year: Optional[int] = None,
        limit_per_ticker: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Lấy dữ liệu news cho tất cả 5 ticker
        
        Returns:
            Dictionary với key là ticker, value là DataFrame
        """
        print(f"\n{'=' * 60}")
        print("LẤY DỮ LIỆU NEWS CHO TẤT CẢ TICKER")
        print(f"{'=' * 60}")
        
        results = {}
        for ticker in SUPPORTED_TICKERS:
            df = self.get_news_data_by_ticker(
                ticker=ticker,
                year=year,
                limit=limit_per_ticker
            )
            results[ticker] = df
        
        print(f"\n{'=' * 60}")
        print(f"✅ Hoàn thành! Tổng số ticker: {len(results)}")
        for ticker, df in results.items():
            print(f"  - {ticker}: {len(df)} records")
        print(f"{'=' * 60}\n")
        
        return results
    
    def get_combined_data_by_ticker(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Lấy cả dữ liệu stock và news cho 1 ticker
        
        Returns:
            Dictionary với 2 keys: 'stock' và 'news'
        """
        print(f"\n{'=' * 60}")
        print(f"LẤY DỮ LIỆU KẾT HỢP CHO TICKER: {ticker}")
        print(f"{'=' * 60}")
        
        stock_df = self.get_stock_data_by_ticker(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )
        
        year = int(start_date.split('-')[0]) if start_date else None
        news_df = self.get_news_data_by_ticker(
            ticker=ticker,
            year=year,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"\n{'=' * 60}")
        print(f"✅ Hoàn thành!")
        print(f"  - Stock records: {len(stock_df)}")
        print(f"  - News records: {len(news_df)}")
        print(f"{'=' * 60}\n")
        
        return {
            'stock': stock_df,
            'news': news_df
        }
    
    def export_to_csv(self, df: pd.DataFrame, filename: str):
        """
        Export DataFrame ra file CSV
        """
        output_path = f"./data/exports/{filename}"
        os.makedirs('./data/exports', exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✓ Đã export dữ liệu ra: {output_path}")
    
    def check_sentiment_coverage(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Kiểm tra coverage của sentiment scores trong bảng news_data
        
        Args:
            ticker: Mã cổ phiếu cụ thể, None = kiểm tra tất cả
            
        Returns:
            Dictionary chứa thống kê về sentiment coverage
        """
        print(f"\n{'=' * 60}")
        print(f"KIỂM TRA SENTIMENT COVERAGE")
        if ticker:
            print(f"Ticker: {ticker}")
        else:
            print("Tất cả ticker")
        print(f"{'=' * 60}\n")
        
        try:
            # Query để lấy tất cả records
            query = self.supabase.table('news_data').select('id, ticker, negative_score, positive_score, neutral_score')
            
            if ticker:
                query = query.eq('ticker', ticker.upper())
            
            response = query.execute()
            data = response.data
            
            if not data:
                print("⚠️  Không tìm thấy dữ liệu")
                return {}
            
            df = pd.DataFrame(data)
            total_records = len(df)
            
            # Kiểm tra records có sentiment (không null và khác giá trị mặc định)
            has_sentiment = df[
                (df['negative_score'].notna()) & 
                (df['positive_score'].notna()) & 
                (df['neutral_score'].notna()) &
                ~((df['negative_score'] == 0) & (df['positive_score'] == 0) & (df['neutral_score'] == 1))
            ]
            
            # Kiểm tra records thiếu sentiment (null hoặc giá trị mặc định)
            missing_sentiment = df[
                (df['negative_score'].isna()) | 
                (df['positive_score'].isna()) | 
                (df['neutral_score'].isna()) |
                ((df['negative_score'] == 0) & (df['positive_score'] == 0) & (df['neutral_score'] == 1))
            ]
            
            has_count = len(has_sentiment)
            missing_count = len(missing_sentiment)
            coverage_percent = (has_count / total_records * 100) if total_records > 0 else 0
            
            print(f"📊 THỐNG KÊ:")
            print(f"  ✅ Tổng số records: {total_records}")
            print(f"  ✅ Đã có sentiment: {has_count} ({coverage_percent:.2f}%)")
            print(f"  ❌ Thiếu sentiment: {missing_count} ({100-coverage_percent:.2f}%)")
            
            # Thống kê theo ticker nếu không filter
            if not ticker:
                print(f"\n📊 THỐNG KÊ THEO TICKER:")
                ticker_stats = df.groupby('ticker').apply(
                    lambda x: pd.Series({
                        'total': len(x),
                        'has_sentiment': len(x[
                            (x['negative_score'].notna()) & 
                            (x['positive_score'].notna()) & 
                            (x['neutral_score'].notna()) &
                            ~((x['negative_score'] == 0) & (x['positive_score'] == 0) & (x['neutral_score'] == 1))
                        ]),
                        'missing_sentiment': len(x[
                            (x['negative_score'].isna()) | 
                            (x['positive_score'].isna()) | 
                            (x['neutral_score'].isna()) |
                            ((x['negative_score'] == 0) & (x['positive_score'] == 0) & (x['neutral_score'] == 1))
                        ])
                    })
                )
                ticker_stats['coverage_%'] = (ticker_stats['has_sentiment'] / ticker_stats['total'] * 100).round(2)
                print(ticker_stats.to_string())
            
            # Hiển thị một số sample records thiếu sentiment
            if missing_count > 0:
                print(f"\n⚠️  MẪU CÁC RECORDS THIẾU SENTIMENT (5 records đầu):")
                missing_ids = missing_sentiment['id'].head(5).tolist()
                print(f"  IDs: {missing_ids}")
            
            print(f"\n{'=' * 60}\n")
            
            return {
                'total_records': total_records,
                'has_sentiment': has_count,
                'missing_sentiment': missing_count,
                'coverage_percent': coverage_percent,
                'missing_ids': missing_sentiment['id'].tolist() if missing_count > 0 else []
            }
            
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")
            return {}


def main():
    """
    Demo sử dụng các hàm
    """
    fetcher = SupabaseDataFetcher()
    
    print("\n" + "=" * 60)
    print("SUPABASE DATA FETCHER - DEMO")
    print("=" * 60 + "\n")
    
    print("Các ticker được hỗ trợ:", ', '.join(SUPPORTED_TICKERS))
    
    # Menu lựa chọn
    print("\nChọn chức năng:")
    print("1. Lấy dữ liệu stock cho 1 ticker")
    print("2. Lấy dữ liệu news cho 1 ticker")
    print("3. Lấy dữ liệu kết hợp (stock + news) cho 1 ticker")
    print("4. Lấy dữ liệu stock cho tất cả ticker")
    print("5. Lấy dữ liệu news cho tất cả ticker")
    print("6. 🔍 Kiểm tra Sentiment Coverage")
    
    choice = input("\nNhập lựa chọn (1-6): ")
    
    if choice == '1':
        ticker = input(f"Nhập ticker ({', '.join(SUPPORTED_TICKERS)}): ").upper()
        start_date = input("Nhập ngày bắt đầu (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        end_date = input("Nhập ngày kết thúc (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        
        df = fetcher.get_stock_data_by_ticker(
            ticker=ticker,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        
        if not df.empty:
            print(f"\n📊 Mẫu dữ liệu:\n")
            print(df.head(10))
            
            export = input("\nBạn có muốn export ra CSV? (y/n): ")
            if export.lower() == 'y':
                fetcher.export_to_csv(df, f"{ticker}_stock_data.csv")
    
    elif choice == '2':
        ticker = input(f"Nhập ticker ({', '.join(SUPPORTED_TICKERS)}): ").upper()
        year_input = input("Nhập năm (2015-2025) hoặc Enter để bỏ qua: ").strip()
        year = int(year_input) if year_input else None
        
        df = fetcher.get_news_data_by_ticker(
            ticker=ticker,
            year=year
        )
        
        if not df.empty:
            print(f"\n📰 Mẫu dữ liệu:\n")
            # Hiển thị các cột quan trọng bao gồm sentiment scores
            display_cols = ['date', 'ticker', 'title', 'source', 'negative_score', 'positive_score', 'neutral_score']
            # Chỉ hiển thị các cột tồn tại trong DataFrame
            available_cols = [col for col in display_cols if col in df.columns]
            print(df[available_cols].head(10))
            
            export = input("\nBạn có muốn export ra CSV? (y/n): ")
            if export.lower() == 'y':
                fetcher.export_to_csv(df, f"{ticker}_news_data.csv")
    
    elif choice == '3':
        ticker = input(f"Nhập ticker ({', '.join(SUPPORTED_TICKERS)}): ").upper()
        start_date = input("Nhập ngày bắt đầu (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        end_date = input("Nhập ngày kết thúc (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        
        data = fetcher.get_combined_data_by_ticker(
            ticker=ticker,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        
        print(f"\n📊 Stock Data Sample:\n")
        print(data['stock'].head(5))
        print(f"\n📰 News Data Sample:\n")
        # Hiển thị title và sentiment scores nếu có
        news_display_cols = ['date', 'title', 'negative_score', 'positive_score', 'neutral_score']
        available_news_cols = [col for col in news_display_cols if col in data['news'].columns]
        print(data['news'][available_news_cols].head(5))
        
        export = input("\nBạn có muốn export ra CSV? (y/n): ")
        if export.lower() == 'y':
            fetcher.export_to_csv(data['stock'], f"{ticker}_stock_data.csv")
            fetcher.export_to_csv(data['news'], f"{ticker}_news_data.csv")
    
    elif choice == '4':
        start_date = input("Nhập ngày bắt đầu (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        end_date = input("Nhập ngày kết thúc (YYYY-MM-DD) hoặc Enter để bỏ qua: ").strip()
        
        results = fetcher.get_all_tickers_stock_data(
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        
        for ticker, df in results.items():
            if not df.empty:
                print(f"\n📊 {ticker} - Mẫu dữ liệu:")
                print(df.head(3))
        
        export = input("\nBạn có muốn export tất cả ra CSV? (y/n): ")
        if export.lower() == 'y':
            for ticker, df in results.items():
                if not df.empty:
                    fetcher.export_to_csv(df, f"{ticker}_stock_data.csv")
    
    elif choice == '5':
        year_input = input("Nhập năm (2015-2025) hoặc Enter để bỏ qua: ").strip()
        year = int(year_input) if year_input else None
        
        results = fetcher.get_all_tickers_news_data(year=year)
        
        for ticker, df in results.items():
            if not df.empty:
                print(f"\n📰 {ticker} - Mẫu dữ liệu:")
                # Hiển thị title và sentiment scores nếu có
                display_cols = ['date', 'title', 'negative_score', 'positive_score', 'neutral_score']
                available_cols = [col for col in display_cols if col in df.columns]
                print(df[available_cols].head(3))
        
        export = input("\nBạn có muốn export tất cả ra CSV? (y/n): ")
        if export.lower() == 'y':
            for ticker, df in results.items():
                if not df.empty:
                    fetcher.export_to_csv(df, f"{ticker}_news_data.csv")
    
    elif choice == '6':
        print("\n💡 Kiểm tra xem có bao nhiêu % dữ liệu đã có sentiment scores")
        ticker_input = input(f"Nhập ticker để kiểm tra cụ thể ({', '.join(SUPPORTED_TICKERS)}) hoặc Enter để kiểm tra tất cả: ").strip().upper()
        
        ticker = ticker_input if ticker_input and ticker_input in SUPPORTED_TICKERS else None
        
        result = fetcher.check_sentiment_coverage(ticker=ticker)
        
        # Gợi ý nếu có records thiếu
        if result and result.get('missing_sentiment', 0) > 0:
            print("\n💡 GỢI Ý:")
            print(f"  - Bạn có {result['missing_sentiment']} records chưa có sentiment scores")
            print(f"  - Chạy script 'analyze_news_sentiment.py' với option 6 để update!")
            print(f"  - Hoặc chạy: python analyze_news_sentiment.py")
    
    else:
        print("Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()
