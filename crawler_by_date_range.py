"""
DATE-RANGE NEWS CRAWLER FOR MODEL INFERENCE
Crawl tin tức theo range ngày cụ thể để phục vụ inference
Usage:
    python crawler_by_date_range.py --start 2024-01-01 --end 2024-01-31 --tickers ACB,BID,VCB
    python crawler_by_date_range.py --start 2024-01-01 --days 7  # Crawl 7 ngày từ start date
    python crawler_by_date_range.py --date 2024-01-15  # Crawl chỉ 1 ngày
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os
import argparse

# Thread-safe
csv_lock = Lock()
seen_urls = set()

# Configuration
MAX_WORKERS = 3
BATCH_SIZE = 50
REQUEST_DELAY = 0.2

class VnExpressCrawler:
    BASE_URL = "https://vnexpress.net"
    SEARCH_URL = "https://timkiem.vnexpress.net/?q={query}&date_from={date_from}&date_to={date_to}&media_type=all&page={page}"
    
    @staticmethod
    def get_article_links(ticker, start_date, end_date, max_pages=30):
        """Crawl article links từ VnExpress cho date range cụ thể"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # Tên đầy đủ của tickers
        ticker_names = {
            "ACB": ["ACB", "ngân hàng ACB"],
            "BID": ["BIDV", "ngân hàng BIDV"],
            "VCB": ["Vietcombank", "VCB"],
            "MBB": ["MB Bank", "MBB"],
            "FPT": ["FPT", "FPT Corporation"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = VnExpressCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    date_from=start_date.strftime("%Y-%m-%d"),
                    date_to=end_date.strftime("%Y-%m-%d"),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.find_all('h3', class_='title-news')
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    for article in articles:
                        a_tag = article.find('a', href=True)
                        if a_tag:
                            href = a_tag.get('href', '')
                            if href.startswith('http'):
                                links.append(href)
                            elif href.startswith('/'):
                                links.append(VnExpressCrawler.BASE_URL + href)
                    
                    consecutive_empty = 0
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract title, content, date từ VnExpress article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.title-detail")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("article.fck_detail")
            if content_elem:
                paragraphs = content_elem.select("p.Normal")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("span.date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

def parse_date(date_str):
    """Parse date to ISO format"""
    if not date_str:
        return ""
    
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d/%m/%Y, %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    return date_str

def extract_date_only(date_str):
    """Extract only date part (YYYY-MM-DD)"""
    if not date_str:
        return ""
    
    try:
        if len(date_str) >= 10:
            return date_str[:10]
    except:
        pass
    
    return date_str

def detect_ticker_in_content(title, content, ticker):
    """Check if ticker is mentioned in content"""
    text = (title + " " + content).upper()
    
    patterns = [
        ticker,
        f" {ticker} ",
        f"({ticker})",
        f"{ticker},",
    ]
    
    return any(pattern in text for pattern in patterns)

def process_article(url, ticker, target_date):
    """Process single article and verify date match"""
    if url in seen_urls:
        return None
    
    seen_urls.add(url)
    
    title, content, date_str = VnExpressCrawler.extract_content(url)
    
    # Validate content
    if not content or len(content) < 100:
        return None
    
    # Check ticker mention
    if not detect_ticker_in_content(title or "", content, ticker):
        return None
    
    # Parse and validate date
    parsed_date = parse_date(date_str)
    article_date = extract_date_only(parsed_date)
    
    # Verify article is from target date
    if target_date and article_date != target_date:
        return None
    
    # Split date and time
    try:
        if parsed_date and ' ' in parsed_date:
            date_part, time_part = parsed_date.split(' ', 1)
        else:
            date_part = article_date
            time_part = ""
    except:
        date_part = article_date
        time_part = ""
    
    if not title:
        title = content[:50] + "..."
    
    return {
        "date": date_part,
        "time": time_part,
        "title": title,
        "content": content,
        "ticker": ticker,
        "source": url
    }

def save_to_csv(batch, output_file, write_header=False):
    """Save batch to CSV (thread-safe)"""
    with csv_lock:
        mode = 'w' if write_header else 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

def crawl_by_date_range(tickers, start_date, end_date, output_file):
    """Crawl tin tức cho date range cụ thể"""
    batch = []
    save_to_csv([], output_file, write_header=True)
    
    total_records = 0
    ticker_stats = {ticker: 0 for ticker in tickers}
    date_stats = {}
    
    print("\n" + "="*70)
    print("📅 DATE-RANGE NEWS CRAWLER FOR INFERENCE")
    print("="*70)
    print(f"[INFO] Date range: {start_date.date()} to {end_date.date()}")
    print(f"[INFO] Duration: {(end_date - start_date).days + 1} day(s)")
    print(f"[INFO] Tickers: {', '.join(tickers)}")
    print(f"[INFO] Output: {output_file}")
    
    # Crawl từng NGÀY
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n{'='*70}")
        print(f"[DATE] 📅 {date_str}")
        print(f"{'='*70}")
        
        date_count = 0
        
        for ticker in tickers:
            print(f"\n[{date_str}] 💼 {ticker}:")
            
            # Get links for this specific date
            print(f"  📰 Crawling VnExpress...", file=sys.stderr)
            links = VnExpressCrawler.get_article_links(ticker, current_date, current_date, max_pages=30)
            print(f"    ✅ Found {len(links)} links", file=sys.stderr)
            
            if not links:
                print(f"    ⚠️  No articles found")
                continue
            
            # Process articles
            ticker_date_count = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(process_article, url, ticker, date_str): url for url in links}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch.append(result)
                            total_records += 1
                            ticker_date_count += 1
                            ticker_stats[ticker] += 1
                            date_count += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                save_to_csv(batch, output_file)
                                print(f"[SAVE] ✅ Saved {len(batch)} records. Total: {total_records}", file=sys.stderr)
                                batch = []
                    except Exception as e:
                        pass
            
            if ticker_date_count > 0:
                print(f"    ✅ Extracted {ticker_date_count} articles")
        
        date_stats[date_str] = date_count
        if date_count > 0:
            print(f"\n[{date_str}] Total: {date_count} articles")
        else:
            print(f"\n[{date_str}] ⚠️  No articles found for any ticker")
        
        current_date += timedelta(days=1)
    
    # Save final batch
    if batch:
        save_to_csv(batch, output_file)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 SUMMARY BY TICKER:")
    print("="*70)
    for ticker in tickers:
        count = ticker_stats[ticker]
        print(f"  {ticker}: {count:>4} articles")
    
    print("\n" + "="*70)
    print("📊 SUMMARY BY DATE:")
    print("="*70)
    for date_str in sorted(date_stats.keys()):
        count = date_stats[date_str]
        status = "✅" if count > 0 else "⚠️ "
        print(f"  {status} {date_str}: {count:>3} articles")
    
    return total_records

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Crawl Vietnamese stock news for specific date range',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl từ 2024-01-01 đến 2024-01-31 cho ACB và BID
  python crawler_by_date_range.py --start 2024-01-01 --end 2024-01-31 --tickers ACB,BID
  
  # Crawl 7 ngày từ 2024-01-01
  python crawler_by_date_range.py --start 2024-01-01 --days 7 --tickers VCB
  
  # Crawl chỉ 1 ngày
  python crawler_by_date_range.py --date 2024-01-15 --tickers ACB,BID,VCB,MBB,FPT
  
  # Crawl tuần trước (7 ngày)
  python crawler_by_date_range.py --last-week --tickers ACB,BID,VCB
  
  # Crawl tháng trước
  python crawler_by_date_range.py --last-month --tickers ACB,BID,VCB,MBB,FPT
        """
    )
    
    # Date options
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    date_group.add_argument('--date', type=str, help='Single date to crawl (YYYY-MM-DD)')
    date_group.add_argument('--last-week', action='store_true', help='Crawl last 7 days')
    date_group.add_argument('--last-month', action='store_true', help='Crawl last 30 days')
    date_group.add_argument('--today', action='store_true', help='Crawl today only')
    
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD), required if --start is used')
    parser.add_argument('--days', type=int, help='Number of days from start date')
    
    # Tickers
    parser.add_argument('--tickers', type=str, default='ACB,BID,VCB,MBB,FPT',
                        help='Comma-separated list of tickers (default: ACB,BID,VCB,MBB,FPT)')
    
    # Output
    parser.add_argument('--output', type=str, help='Output CSV filename (auto-generated if not specified)')
    
    args = parser.parse_args()
    
    # Validate and process dates
    today = datetime.now().date()
    
    if args.today:
        start_date = datetime.combine(today, datetime.min.time())
        end_date = start_date
    elif args.date:
        start_date = datetime.strptime(args.date, "%Y-%m-%d")
        end_date = start_date
    elif args.last_week:
        end_date = datetime.combine(today, datetime.min.time())
        start_date = end_date - timedelta(days=6)
    elif args.last_month:
        end_date = datetime.combine(today, datetime.min.time())
        start_date = end_date - timedelta(days=29)
    elif args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        if args.end:
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        elif args.days:
            end_date = start_date + timedelta(days=args.days - 1)
        else:
            parser.error("--start requires either --end or --days")
    else:
        parser.error("Must specify date range")
    
    # Validate date range
    if end_date < start_date:
        parser.error("End date must be >= start date")
    
    # Process tickers
    tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Generate output filename if not specified
    if not args.output:
        if start_date == end_date:
            output = f"news_{start_date.strftime('%Y%m%d')}_{'_'.join(tickers)}.csv"
        else:
            output = f"news_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}_{'_'.join(tickers)}.csv"
    else:
        output = args.output
    
    return start_date, end_date, tickers, output

if __name__ == "__main__":
    try:
        start_date, end_date, tickers, output_file = parse_arguments()
    except SystemExit:
        sys.exit(1)
    
    print("="*70)
    print("📅 DATE-RANGE NEWS CRAWLER")
    print("="*70)
    
    # Confirm if file exists
    if os.path.exists(output_file):
        print(f"\n[WARNING] File {output_file} already exists!")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        total = crawl_by_date_range(tickers, start_date, end_date, output_file)
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print(f"[SUCCESS] ✅ Saved {total} articles to {output_file}")
        print(f"[TIME] ⏱️  Duration: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
        if elapsed > 0:
            print(f"[SPEED] 🚄 Speed: {total/(elapsed/60):.1f} articles/minute")
        print("="*70)
        
        # File info
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"\n📄 Output file: {output_file} ({file_size:.2f} MB)")
        
        print("\n✅ Data ready for model inference!")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Interrupted by user")
        print(f"[INFO] Partial data saved to {output_file}")
    except Exception as e:
        print(f"\n[ERROR] ❌ {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
