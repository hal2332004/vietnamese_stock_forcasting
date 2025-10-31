"""
MULTI-SOURCE NEWS CRAWLER - FIXED VERSION
Fix: 
1. Ticker detection - flexible matching với tên đầy đủ
2. seen_urls per ticker - tránh bỏ qua bài viết giữa các ticker
3. Year validation - check article date để đảm bảo đúng năm
4. Content validation - giảm threshold xuống 50 chars
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
seen_urls_lock = Lock()

# TICKER PATTERNS - Đầy đủ để detect chính xác
TICKER_FULL_NAMES = {
    "ACB": ["ACB", "Á Châu", "Asia Commercial Bank", "ngân hàng ACB", "NH ACB"],
    "BID": ["BID", "BIDV", "Đầu tư và Phát triển", "ngân hàng BIDV", "NH BIDV", "Đầu Tư Phát Triển"],
    "VCB": ["VCB", "Vietcombank", "ngân hàng Vietcombank", "Ngoại thương", "NH Vietcombank", "NH Ngoại Thương"],
    "MBB": ["MBB", "MB Bank", "MB", "ngân hàng MB", "Military Bank", "Quân Đội", "NH Quân Đội"],
    "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT", "cổ phiếu FPT", "Công ty FPT"],
}

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
        
        # Tạo nhiều queries từ tên đầy đủ
        base_queries = TICKER_FULL_NAMES.get(ticker, [ticker])
        queries = []
        for name in base_queries:
            queries.extend([
                name,
                f"{name} lợi nhuận",
                f"{name} cổ phiếu",
                f"{name} kinh doanh",
                f"{name} tăng trưởng",
            ])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 3:
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
                    
                    page_has_link = False
                    for article in articles:
                        a_tag = article.find('a', href=True)
                        if a_tag:
                            href = a_tag.get('href', '')
                            if href.startswith('http'):
                                links.append(('vnexpress', href))
                                page_has_link = True
                            elif href.startswith('/'):
                                links.append(('vnexpress', VnExpressCrawler.BASE_URL + href))
                                page_has_link = True
                    
                    if page_has_link:
                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                    
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
        
        base_queries = TICKER_FULL_NAMES.get(ticker, [ticker])
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
                if consecutive_empty >= 3:
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
                    
                    page_has_link = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Accept all - check year later when extracting
                        if href.startswith('http'):
                            links.append(('dantri', href))
                            page_has_link = True
                        elif href.startswith('/'):
                            links.append(('dantri', DanTriCrawler.BASE_URL + href))
                            page_has_link = True
                    
                    if page_has_link:
                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                    
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
        
        queries = TICKER_FULL_NAMES.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 3:
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
                    
                    page_has_link = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Accept all
                        if href.startswith('http'):
                            links.append(('thanhnien', href))
                            page_has_link = True
                        elif href.startswith('/'):
                            links.append(('thanhnien', ThanhNienCrawler.BASE_URL + href))
                            page_has_link = True
                    
                    if page_has_link:
                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                    
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

# ============= HELPER FUNCTIONS =============
def parse_date(date_str):
    """Parse date to ISO format - FIXED để xử lý format Việt Nam"""
    if not date_str:
        return ""
    
    # Xóa "Thứ hai, Thứ ba,..." và khoảng trắng thừa
    date_str = re.sub(r'Thứ\s+(hai|ba|tư|năm|sáu|bảy|CN),?\s*', '', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\(GMT\+\d+\)', '', date_str)  # Xóa (GMT+7)
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d/%m/%Y, %H:%M",      # 15/7/2014, 17:45
        "%d/%m/%Y %H:%M",       # 15/7/2014 17:45
        "%Y-%m-%d %H:%M:%S",    # 2015-01-01 10:30:00
        "%d/%m/%Y",             # 15/7/2014
        "%d-%m-%Y",             # 15-7-2014
        "%Y-%m-%d",             # 2015-01-01
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    # Nếu không parse được, thử extract năm bằng regex
    year_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if year_match:
        day, month, year = year_match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d 00:00:00")
        except:
            pass
    
    return ""  # Trả về rỗng nếu không parse được

def extract_year_from_date(date_str):
    """Extract year from date string"""
    if not date_str:
        return None
    
    try:
        if len(date_str) >= 10:
            year = int(date_str[:4])
            return year
    except:
        pass
    
    return None

def detect_ticker_in_content(title, content, ticker):
    """Check if ticker is mentioned in content - FLEXIBLE MATCHING"""
    text = (title + " " + content).upper()
    
    # Get all possible names for this ticker
    possible_names = TICKER_FULL_NAMES.get(ticker, [ticker])
    
    # Check if any name appears in text
    for name in possible_names:
        if name.upper() in text:
            return True
    
    return False

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

def process_article(source, url, ticker, target_year, seen_urls_for_ticker):
    """Process single article from any source"""
    # Check if already seen (per ticker)
    with seen_urls_lock:
        if url in seen_urls_for_ticker:
            return None
        seen_urls_for_ticker.add(url)
    
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
    
    # Validate content length - GIẢM THRESHOLD
    if not content or len(content) < 50:
        return None
    
    # Validate ticker detection - FLEXIBLE
    if not detect_ticker_in_content(title or "", content, ticker):
        return None
    
    # Parse date
    parsed_date = parse_date(date_str)
    
    # Skip if cannot parse date
    if not parsed_date or len(parsed_date) < 10:
        return None
    
    # Validate year
    article_year = extract_year_from_date(parsed_date)
    if not article_year:
        # Skip if cannot extract year
        return None
    
    if article_year != target_year:
        # Skip if wrong year
        return None
    
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
    
    print(f"[INFO] ✅ {source.upper()}: {ticker} {target_year} | {title[:50]}...", file=sys.stderr)
    
    return {
        "date": date_part,
        "time": time_part,
        "title": title,
        "content": content,
        "ticker": ticker,
        "source": f"{source}:{url}"
    }

def save_batch_to_csv(batch, output_file, write_header=False):
    """Save batch to CSV (thread-safe)"""
    with csv_lock:
        mode = 'w' if write_header else 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

def crawl_multi_source(output_file):
    """Main crawler - crawl từ nhiều nguồn với SEPARATE seen_urls per ticker"""
    batch = []
    save_batch_to_csv([], output_file, write_header=True)
    
    total_records = 0
    ticker_year_stats = {}
    
    print("\n" + "="*70, file=sys.stderr)
    print("🌐 MULTI-SOURCE NEWS CRAWLER - FIXED", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"[INFO] Sources: VnExpress, Dân Trí, ThanhNien, CafeF", file=sys.stderr)
    print(f"[INFO] Period: {START_DATE.year}-{END_DATE.year}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Target: 250+ articles/ticker/year", file=sys.stderr)
    print(f"[FIX] Flexible ticker detection, per-ticker seen_urls, year validation", file=sys.stderr)
    
    # Crawl theo từng NĂM và TICKER
    for year in range(START_DATE.year, END_DATE.year + 1):
        print(f"\n{'#'*70}", file=sys.stderr)
        print(f"[YEAR] 📅 {year}", file=sys.stderr)
        print(f"{'#'*70}", file=sys.stderr)
        
        for ticker in TICKERS:
            print(f"\n[{year}] 💼 Ticker: {ticker}", file=sys.stderr)
            
            # SEPARATE seen_urls for each ticker
            seen_urls_for_ticker = set()
            
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
            
            # Process articles with year validation
            ticker_year_count = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(process_article, source, url, ticker, year, seen_urls_for_ticker): (source, url) 
                    for source, url in all_links
                }
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch.append(result)
                            total_records += 1
                            ticker_year_count += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                save_batch_to_csv(batch, output_file)
                                print(f"[SAVE] ✅ Saved {len(batch)} records. Total: {total_records}", file=sys.stderr)
                                batch = []
                    except Exception as e:
                        pass
            
            ticker_year_stats[f"{year}_{ticker}"] = ticker_year_count
            print(f"  ✅ {ticker} {year}: {ticker_year_count} articles", file=sys.stderr)
    
    # Save final batch
    if batch:
        save_batch_to_csv(batch, output_file)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Print summary
    print("\n" + "="*70, file=sys.stderr)
    print("📊 SUMMARY BY YEAR AND TICKER:", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    for year in range(START_DATE.year, END_DATE.year + 1):
        year_total = 0
        print(f"\n{year}:", file=sys.stderr)
        for ticker in TICKERS:
            count = ticker_year_stats.get(f"{year}_{ticker}", 0)
            year_total += count
            print(f"  {ticker}: {count:>4} articles", file=sys.stderr)
        print(f"  TOTAL: {year_total:>4} articles", file=sys.stderr)
    
    return total_records

if __name__ == "__main__":
    print("="*70)
    print("🌐 MULTI-SOURCE VIETNAMESE STOCK NEWS CRAWLER - FIXED VERSION")
    print("="*70)
    print(f"[INFO] Date range: {START_DATE.date()} to {END_DATE.date()}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    
    output_file = f"multi_source_news_{START_DATE.year}_{END_DATE.year}_fixed.csv"
    
    if os.path.exists(output_file):
        print(f"\n[WARNING] File {output_file} already exists!")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        total = crawl_multi_source(output_file)
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print(f"[SUCCESS] ✅ Saved {total} articles to {output_file}")
        print(f"[TIME] ⏱️  Duration: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
        print(f"[SPEED] 🚄 Speed: {total/(elapsed/60):.1f} articles/minute")
        print("="*70)
        
        # Final statistics
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            ticker_counts = {}
            year_counts = {}
            for row in reader:
                ticker = row['ticker']
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
                
                # Count by year
                date_str = row['date']
                if date_str and len(date_str) >= 4:
                    year = date_str[:4]
                    year_counts[year] = year_counts.get(year, 0) + 1
        
        print("\n📊 Final Statistics by Ticker:")
        for ticker in TICKERS:
            count = ticker_counts.get(ticker, 0)
            print(f"  {ticker}: {count:>5} articles")
        
        print("\n📊 Final Statistics by Year:")
        for year in sorted(year_counts.keys()):
            count = year_counts[year]
            print(f"  {year}: {count:>5} articles")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] ❌ {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
