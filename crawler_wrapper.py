"""
NEWS CRAWLER WRAPPER FOR MODEL INFERENCE
Module để tích hợp vào code inference - tự động crawl tin tức theo ngày cần predict
"""

import subprocess
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

class NewsCrawlerForInference:
    """
    Wrapper class để crawl tin tức phục vụ inference
    """
    
    def __init__(self, crawler_script_path=None):
        """
        Args:
            crawler_script_path: Path to crawler_by_date_range.py
        """
        if crawler_script_path is None:
            # Auto-detect script path
            current_dir = Path(__file__).parent
            self.crawler_script = current_dir / "crawler_by_date_range.py"
        else:
            self.crawler_script = Path(crawler_script_path)
        
        if not self.crawler_script.exists():
            raise FileNotFoundError(f"Crawler script not found: {self.crawler_script}")
    
    def crawl_for_date(self, date, tickers=None, output_dir=None):
        """
        Crawl tin tức cho 1 ngày cụ thể
        
        Args:
            date: datetime object hoặc string 'YYYY-MM-DD'
            tickers: list of tickers (mặc định: ['ACB', 'BID', 'VCB', 'MBB', 'FPT'])
            output_dir: thư mục lưu output (mặc định: current dir)
        
        Returns:
            str: path to output CSV file
        """
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d")
        
        if tickers is None:
            tickers = ['ACB', 'BID', 'VCB', 'MBB', 'FPT']
        
        date_str = date.strftime("%Y-%m-%d")
        tickers_str = ','.join(tickers)
        
        # Generate output filename
        if output_dir:
            output_file = os.path.join(output_dir, f"news_{date.strftime('%Y%m%d')}.csv")
        else:
            output_file = f"news_{date.strftime('%Y%m%d')}.csv"
        
        # Build command
        cmd = [
            'python',
            str(self.crawler_script),
            '--date', date_str,
            '--tickers', tickers_str,
            '--output', output_file
        ]
        
        print(f"[INFO] Crawling news for {date_str}...")
        
        # Run crawler
        try:
            # Auto answer 'y' to overwrite prompt
            result = subprocess.run(
                cmd,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                print(f"[SUCCESS] Crawled {date_str} -> {output_file}")
                return output_file
            else:
                print(f"[ERROR] Crawler failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[ERROR] Crawler timeout for {date_str}")
            return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def crawl_for_date_range(self, start_date, end_date, tickers=None, output_dir=None):
        """
        Crawl tin tức cho range ngày
        
        Args:
            start_date: datetime object hoặc string 'YYYY-MM-DD'
            end_date: datetime object hoặc string 'YYYY-MM-DD'
            tickers: list of tickers
            output_dir: thư mục lưu output
        
        Returns:
            str: path to output CSV file
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        if tickers is None:
            tickers = ['ACB', 'BID', 'VCB', 'MBB', 'FPT']
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        tickers_str = ','.join(tickers)
        
        # Generate output filename
        if output_dir:
            output_file = os.path.join(
                output_dir,
                f"news_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
            )
        else:
            output_file = f"news_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
        
        # Build command
        cmd = [
            'python',
            str(self.crawler_script),
            '--start', start_str,
            '--end', end_str,
            '--tickers', tickers_str,
            '--output', output_file
        ]
        
        print(f"[INFO] Crawling news from {start_str} to {end_str}...")
        
        # Run crawler
        try:
            result = subprocess.run(
                cmd,
                input='y\n',
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result.returncode == 0:
                print(f"[SUCCESS] Crawled {start_str} to {end_str} -> {output_file}")
                return output_file
            else:
                print(f"[ERROR] Crawler failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[ERROR] Crawler timeout")
            return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def crawl_last_n_days(self, n_days=7, tickers=None, output_dir=None):
        """
        Crawl tin tức n ngày gần đây
        
        Args:
            n_days: số ngày (mặc định: 7)
            tickers: list of tickers
            output_dir: thư mục lưu output
        
        Returns:
            str: path to output CSV file
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=n_days-1)
        
        return self.crawl_for_date_range(start_date, end_date, tickers, output_dir)
    
    def load_crawled_data(self, csv_file):
        """
        Load dữ liệu đã crawl từ CSV
        
        Args:
            csv_file: path to CSV file
        
        Returns:
            pandas DataFrame
        """
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        df = pd.read_csv(csv_file)
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        print(f"[INFO] Loaded {len(df)} articles from {csv_file}")
        print(f"[INFO] Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"[INFO] Tickers: {df['ticker'].unique()}")
        
        return df
    
    def prepare_for_inference(self, date, tickers=None, output_dir=None):
        """
        All-in-one: Crawl và load data cho inference
        
        Args:
            date: ngày cần predict
            tickers: list of tickers
            output_dir: thư mục lưu output
        
        Returns:
            pandas DataFrame hoặc None nếu crawl thất bại
        """
        csv_file = self.crawl_for_date(date, tickers, output_dir)
        
        if csv_file and os.path.exists(csv_file):
            return self.load_crawled_data(csv_file)
        else:
            print("[ERROR] Failed to crawl data")
            return None


# ============= USAGE EXAMPLES =============

def example_basic_usage():
    """Ví dụ sử dụng cơ bản"""
    crawler = NewsCrawlerForInference()
    
    # Crawl 1 ngày
    csv_file = crawler.crawl_for_date('2024-01-15', tickers=['ACB', 'VCB'])
    
    # Load data
    if csv_file:
        df = crawler.load_crawled_data(csv_file)
        print(df.head())


def example_inference_integration():
    """Ví dụ tích hợp vào code inference"""
    crawler = NewsCrawlerForInference()
    
    # Ngày cần predict
    predict_date = datetime(2024, 1, 15)
    
    # Tự động crawl data cho ngày đó
    news_df = crawler.prepare_for_inference(predict_date)
    
    if news_df is not None:
        # Tiến hành inference với news_df
        print(f"Ready for inference with {len(news_df)} articles")
        
        # Example: Group by ticker
        for ticker in news_df['ticker'].unique():
            ticker_news = news_df[news_df['ticker'] == ticker]
            print(f"{ticker}: {len(ticker_news)} articles")
            
            # TODO: Pass to model for prediction
            # predictions = model.predict(ticker_news)


def example_batch_inference():
    """Ví dụ inference cho nhiều ngày"""
    crawler = NewsCrawlerForInference()
    
    # Crawl 7 ngày gần đây
    csv_file = crawler.crawl_last_n_days(n_days=7, tickers=['ACB', 'BID', 'VCB'])
    
    if csv_file:
        df = crawler.load_crawled_data(csv_file)
        
        # Inference cho từng ngày
        for date in df['date'].unique():
            daily_news = df[df['date'] == date]
            print(f"\n{date}: {len(daily_news)} articles")
            
            # TODO: Inference cho ngày này
            # predictions = model.predict(daily_news)


if __name__ == "__main__":
    print("="*70)
    print("NEWS CRAWLER WRAPPER FOR INFERENCE")
    print("="*70)
    print("\nExamples:")
    print("1. Basic usage")
    print("2. Inference integration")
    print("3. Batch inference")
    print("")
    
    choice = input("Run example (1-3, or 0 to skip): ")
    
    if choice == '1':
        example_basic_usage()
    elif choice == '2':
        example_inference_integration()
    elif choice == '3':
        example_batch_inference()
    else:
        print("\nTo use in your code:")
        print("  from crawler_wrapper import NewsCrawlerForInference")
        print("  crawler = NewsCrawlerForInference()")
        print("  df = crawler.prepare_for_inference('2024-01-15')")
