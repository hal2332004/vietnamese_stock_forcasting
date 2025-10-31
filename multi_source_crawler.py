"""
MULTI-SOURCE NEWS CRAWLER
Crawl tin tức từ nhiều nguồn để đảm bảo đủ dữ liệu cho 5 tickers trong 10 năm
Sources: VnExpress, Dân Trí, CafeF
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

# ============= CONFIGURATION =============
TICKERS = ["ACB", "BID", "VCB", "MBB", "FPT"]
START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2025, 10, 30)

MAX_WORKERS = 5
BATCH_SIZE = 100
MAX_RETRIES = 3
REQUEST_DELAY = 0.2

# Thread-safe
csv_lock = Lock()
seen_urls = set()

# ============= VNEXPRESS CRAWLER =============
class VnExpressCrawler:
    BASE_URL = "https://vnexpress.net"
    SEARCH_URL = "https://timkiem.vnexpress.net/?q={query}&date_from={date_from}&date_to={date_to}&media_type=all&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=50):
        """Crawl article links từ VnExpress theo ticker và năm - NHIỀU QUERIES"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31) if year < END_DATE.year else END_DATE
        
        # Tên đầy đủ của các ngân hàng
        ticker_names = {
            "ACB": ["ACB", "Á Châu", "ngân hàng ACB", "Asia Commercial Bank"],
            "BID": ["BID", "BIDV", "Đầu tư và Phát triển", "ngân hàng BIDV"],
            "VCB": ["VCB", "Vietcombank", "ngân hàng Vietcombank", "Ngoại thương"],
            "MBB": ["MBB", "MB Bank", "ngân hàng MB", "Military Bank"],
            "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT", "cổ phiếu FPT"],
        }
        
        # Tạo nhiều queries để tăng coverage
        base_queries = ticker_names.get(ticker, [ticker])
        queries = []
        for name in base_queries:
            queries.extend([
                name,
                f"{name} lợi nhuận",
                f"{name} cổ phiếu",
                f"{name} kinh doanh",
            ])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = VnExpressCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    date_from=year_start.strftime("%Y-%m-%d"),
                    date_to=year_end.strftime("%Y-%m-%d"),
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
                                links.append(('vnexpress', href))
                            elif href.startswith('/'):
                                links.append(('vnexpress', VnExpressCrawler.BASE_URL + href))
                    
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

# ============= DÂN TRÍ CRAWLER =============
class DanTriCrawler:
    BASE_URL = "https://dantri.com.vn"
    SEARCH_URL = "https://dantri.com.vn/tim-kiem.htm?q={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=50):
        """Crawl article links từ Dân Trí - NHIỀU QUERIES"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "Á Châu", "Asia Commercial Bank"],
            "BID": ["BID", "BIDV", "ngân hàng BIDV"],
            "VCB": ["VCB", "Vietcombank", "ngân hàng Vietcombank"],
            "MBB": ["MBB", "MB Bank", "ngân hàng MB"],
            "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT"],
        }
        
        base_queries = ticker_names.get(ticker, [ticker])
        queries = []
        for name in base_queries:
            queries.extend([
                name,
                f"{name} lợi nhuận",
                f"{name} kinh doanh",
            ])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = DanTriCrawler.SEARCH_URL.format(query=query.replace(' ', '+'), page=page)
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # Dân Trí search results
                    articles = soup.select("h3.article-title a, h4.article-title a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Check if article is from target year
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('dantri', href))
                            elif href.startswith('/'):
                                links.append(('dantri', DanTriCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Dân Trí article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.title-page, h1.article-title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("div.singular-content, div.article-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("time.author-time, span.author-time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= THANHNIEN CRAWLER =============
class ThanhNienCrawler:
    BASE_URL = "https://thanhnien.vn"
    SEARCH_URL = "https://thanhnien.vn/tim-kiem/?keywords={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ ThanhNien.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "ngân hàng ACB"],
            "BID": ["BIDV", "ngân hàng BIDV"],
            "VCB": ["Vietcombank", "ngân hàng Vietcombank"],
            "MBB": ["MB Bank", "ngân hàng MB"],
            "FPT": ["FPT", "FPT Corporation"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = ThanhNienCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # ThanhNien search results
                    articles = soup.select("h2.title-news a, h3.title-news a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Check if from target year
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('thanhnien', href))
                            elif href.startswith('/'):
                                links.append(('thanhnien', ThanhNienCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ ThanhNien article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.detail-title, h1.title-detail")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("div.detail-content, div#contentbody")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("div.detail-time, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= CAFEF CRAWLER (backup) =============
class CafeFCrawler:
    BASE_URL = "https://cafef.vn"
    SEARCH_URL = "https://cafef.vn/tim-kiem.chn?query={query}&sfrom={sfrom}&sto={sto}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=10):
        """Crawl từ CafeF (chỉ lấy tin gần đây)"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31) if year < END_DATE.year else END_DATE
        
        url = CafeFCrawler.SEARCH_URL.format(
            query=ticker,
            sfrom=year_start.strftime("%d/%m/%Y"),
            sto=year_end.strftime("%d/%m/%Y"),
            page=1
        )
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                all_links = soup.find_all('a', href=True)
                
                for a in all_links:
                    href = a.get('href', '')
                    if '.chn' in href and '188' in href:
                        if not href.startswith('http'):
                            href = CafeFCrawler.BASE_URL + href
                        links.append(('cafef', href))
        except:
            pass
        
        return links

# ============= MAIN CRAWLER =============
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
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    return date_str

def detect_ticker_in_content(title, content, ticker):
    """Check if ticker is mentioned in content"""
    text = (title + " " + content).upper()
    
    patterns = [
        ticker,
        f" {ticker} ",
        f"({ticker})",
        f"{ticker},",
        f"{ticker}.",
    ]
    
    return any(pattern in text for pattern in patterns)

def process_article(source, url, ticker):
    """Process single article from any source"""
    if url in seen_urls:
        return None
    
    seen_urls.add(url)
    
    # Extract content based on source
    if source == 'vnexpress':
        title, content, date_str = VnExpressCrawler.extract_content(url)
    elif source == 'dantri':
        title, content, date_str = DanTriCrawler.extract_content(url)
    elif source == 'thanhnien':
        title, content, date_str = ThanhNienCrawler.extract_content(url)
    elif source == 'cafef':
        title, content, date_str = extract_cafef_content(url)
    else:
        return None
    
    # Validate
    if not content or len(content) < 100:
        return None
    
    if not detect_ticker_in_content(title or "", content, ticker):
        return None
    
    # Parse date
    parsed_date = parse_date(date_str)
    
    try:
        if parsed_date and len(parsed_date) >= 10:
            if ' ' in parsed_date:
                date_part, time_part = parsed_date.split(' ', 1)
            else:
                date_part = parsed_date[:10]
                time_part = ""
        else:
            date_part = parsed_date
            time_part = ""
    except:
        date_part = parsed_date
        time_part = ""
    
    if not title:
        title = content[:50] + "..."
    
    print(f"[INFO] ✅ {source.upper()}: {ticker} | {title[:50]}...", file=sys.stderr)
    
    return {
        "date": date_part,
        "time": time_part,
        "title": title,
        "content": content,
        "ticker": ticker,
        "source": f"{source}:{url}"
    }

def extract_cafef_content(url):
    """Extract content from CafeF (backup source)"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, None, None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title = ""
        title_elem = soup.select_one(".title-detail, h1")
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        content = ""
        content_elem = soup.select_one(".detail-content, .main-content")
        if content_elem:
            paragraphs = content_elem.select("p")
            if paragraphs:
                content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
        
        date_str = ""
        date_elem = soup.select_one(".date, time")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
        
        return title, content, date_str
    except:
        return None, None, None

def save_batch_to_csv(batch, output_files, write_header=False):
    """Save batch to CSV (thread-safe) - separate file for each ticker"""
    with csv_lock:
        # Group by ticker
        ticker_batches = {}
        for row in batch:
            ticker = row['ticker']
            if ticker not in ticker_batches:
                ticker_batches[ticker] = []
            ticker_batches[ticker].append(row)
        
        # Save each ticker to its own file
        for ticker, rows in ticker_batches.items():
            output_file = output_files.get(ticker)
            if not output_file:
                continue
            
            mode = 'w' if write_header else 'a'
            with open(output_file, mode, encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
                if write_header:
                    writer.writeheader()
                for row in rows:
                    writer.writerow(row)

def crawl_multi_source(output_files):
    """Main crawler - crawl từ nhiều nguồn - SEPARATE FILES"""
    batch = []
    
    # Initialize all ticker files with headers
    for ticker, output_file in output_files.items():
        with open(output_file, 'w', encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            writer.writeheader()
    
    total_records = 0
    ticker_year_stats = {}
    ticker_totals = {ticker: 0 for ticker in TICKERS}
    
    print("\n" + "="*70, file=sys.stderr)
    print("🌐 MULTI-SOURCE NEWS CRAWLER", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"[INFO] Sources: VnExpress, Dân Trí, ThanhNien, CafeF", file=sys.stderr)
    print(f"[INFO] Period: {START_DATE.year}-{END_DATE.year}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Target: 250+ articles/ticker/year", file=sys.stderr)
    print(f"[INFO] Output: Separate CSV file for each ticker", file=sys.stderr)
    
    # Crawl theo từng NĂM và TICKER
    for year in range(START_DATE.year, END_DATE.year + 1):
        print(f"\n{'#'*70}", file=sys.stderr)
        print(f"[YEAR] 📅 {year}", file=sys.stderr)
        print(f"{'#'*70}", file=sys.stderr)
        
        for ticker in TICKERS:
            print(f"\n[{year}] 💼 Ticker: {ticker}", file=sys.stderr)
            
            # Collect links from all sources
            all_links = []
            
            # VnExpress (50 pages)
            print(f"  📰 Crawling VnExpress...", file=sys.stderr)
            vnexpress_links = VnExpressCrawler.get_article_links(ticker, year, max_pages=50)
            all_links.extend(vnexpress_links)
            print(f"    ✅ Found {len(vnexpress_links)} links", file=sys.stderr)
            
            # Dân Trí (50 pages)
            print(f"  📰 Crawling Dân Trí...", file=sys.stderr)
            dantri_links = DanTriCrawler.get_article_links(ticker, year, max_pages=50)
            all_links.extend(dantri_links)
            print(f"    ✅ Found {len(dantri_links)} links", file=sys.stderr)
            
            # ThanhNien (30 pages)
            print(f"  📰 Crawling ThanhNien...", file=sys.stderr)
            thanhnien_links = ThanhNienCrawler.get_article_links(ticker, year, max_pages=30)
            all_links.extend(thanhnien_links)
            print(f"    ✅ Found {len(thanhnien_links)} links", file=sys.stderr)
            
            # CafeF (only for recent years)
            if year >= 2024:
                print(f"  📰 Crawling CafeF...", file=sys.stderr)
                cafef_links = CafeFCrawler.get_article_links(ticker, year, max_pages=5)
                all_links.extend(cafef_links)
                print(f"    ✅ Found {len(cafef_links)} links", file=sys.stderr)
            
            if not all_links:
                print(f"  ⚠️  No articles found for {ticker} in {year}", file=sys.stderr)
                continue
            
            print(f"  🔄 Processing {len(all_links)} articles...", file=sys.stderr)
            
            # Process articles
            ticker_year_count = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(process_article, source, url, ticker): (source, url) for source, url in all_links}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch.append(result)
                            total_records += 1
                            ticker_year_count += 1
                            ticker_totals[result['ticker']] += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                save_batch_to_csv(batch, output_files)
                                print(f"[SAVE] ✅ Saved {len(batch)} records. Total: {total_records}", file=sys.stderr)
                                batch = []
                    except Exception as e:
                        pass
            
            ticker_year_stats[f"{year}_{ticker}"] = ticker_year_count
            print(f"  ✅ {ticker} {year}: {ticker_year_count} articles", file=sys.stderr)
    
    # Save final batch
    if batch:
        save_batch_to_csv(batch, output_files)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Print summary by year
    print("\n" + "="*70, file=sys.stderr)
    print("📊 SUMMARY BY YEAR AND TICKER:", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    for year in range(START_DATE.year, END_DATE.year + 1):
        print(f"\n{year}:", file=sys.stderr)
        for ticker in TICKERS:
            count = ticker_year_stats.get(f"{year}_{ticker}", 0)
            print(f"  {ticker}: {count:>4} articles", file=sys.stderr)
    
    # Print total by ticker
    print("\n" + "="*70, file=sys.stderr)
    print("📊 TOTAL BY TICKER (ALL YEARS):", file=sys.stderr)
    print("="*70, file=sys.stderr)
    for ticker in TICKERS:
        count = ticker_totals[ticker]
        avg_per_year = count / (END_DATE.year - START_DATE.year + 1)
        print(f"  {ticker}: {count:>5} articles ({avg_per_year:.1f}/year)", file=sys.stderr)
    
    return total_records, ticker_totals

if __name__ == "__main__":
    print("="*70)
    print("🌐 MULTI-SOURCE VIETNAMESE STOCK NEWS CRAWLER")
    print("="*70)
    print(f"[INFO] Date range: {START_DATE.date()} to {END_DATE.date()}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    
    # Create output file dictionary - one file per ticker
    output_files = {}
    for ticker in TICKERS:
        output_files[ticker] = f"news_{ticker}_{START_DATE.year}_{END_DATE.year}.csv"
    
    print(f"\n[INFO] Output files:")
    for ticker, filename in output_files.items():
        print(f"  {ticker}: {filename}")
    
    # Check if any files exist
    existing_files = [f for f in output_files.values() if os.path.exists(f)]
    if existing_files:
        print(f"\n[WARNING] {len(existing_files)} file(s) already exist:")
        for f in existing_files:
            print(f"  - {f}")
        choice = input("Overwrite all? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        total, ticker_totals = crawl_multi_source(output_files)
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print(f"[SUCCESS] ✅ Saved {total} articles to {len(TICKERS)} files")
        print(f"[TIME] ⏱️  Duration: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
        print(f"[SPEED] 🚄 Speed: {total/(elapsed/60):.1f} articles/minute")
        print("="*70)
        
        # Final statistics with file sizes
        print("\n📊 Final Statistics by File:")
        for ticker in TICKERS:
            filename = output_files[ticker]
            count = ticker_totals[ticker]
            
            # Get file size
            if os.path.exists(filename):
                file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
                print(f"  {ticker}: {count:>5} articles | {file_size:>6.2f} MB | {filename}")
            else:
                print(f"  {ticker}: {count:>5} articles | File not created")
        
        print("\n✅ All done! Each ticker has its own CSV file for easy processing.")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Interrupted by user")
        print("[INFO] Partial data saved to individual ticker files")
    except Exception as e:
        print(f"\n[ERROR] ❌ {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
