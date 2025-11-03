"""
STOCK MARKET NEWS CRAWLER V2
Cào TẤT CẢ tin tức về "chứng khoán" từ VnExpress (date_format=all)
Lọc những bài có nhắc đến FPT hoặc BID/BIDV
"""

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import time
import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os

# ============= CONFIGURATION =============
# SEARCH_KEYWORDS = [
#     "cổ phiếu",
#     "VN-Index",
#     "chứng khoán",

# ]

SEARCH_KEYWORDS = [
    # Thị trường & chỉ số
    "chứng khoán",
    "VN-Index",
    "HNX-Index",
    "UPCOM-Index",
    "Sàn giao dịch",
    "thị trường tài chính",
    "giá cổ phiếu",
    "nhận định thị trường",

    # Doanh nghiệp & ngành
    "cổ phiếu ngân hàng",
    "cổ phiếu công nghệ",
    "cổ phiếu dầu khí",
    "cổ phiếu bất động sản",
    "cổ phiếu chứng khoán",
    "cổ phiếu thép",
    "cổ phiếu bán lẻ",
    "cổ phiếu viễn thông",
    "cổ phiếu năng lượng",
    "cổ phiếu điện",
    "cổ phiếu phân bón",
    "cổ phiếu logistics",
    "cổ phiếu hàng không",
    "cổ phiếu du lịch",
    "cổ phiếu vật liệu xây dựng",
    "cổ phiếu tiêu dùng",
    "cổ phiếu bảo hiểm",

    # Dòng tiền & hành vi
    "đầu tư",
    "dòng tiền",

    # Tâm lý & cảm xúc thị trường
    "tâm lý thị trường",
    "nhà đầu tư",
    "kinh tế",
    "vi mô",
    "vĩ mô",
    "báo cáo tài chính",
    "lợi nhuận doanh nghiệp",
    "cổ tức",
    "Ngân hàng Nhà nước",
    "trái phiếu",
    "lãi suất",
    "công cụ đầu tư",
    "phân tích kỹ thuật",
]


TARGET_TICKERS = ["FPT", "BID", "BIDV"]

START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2025, 10, 30)

MAX_WORKERS = 8
BATCH_SIZE = 100
REQUEST_DELAY = 0.2

# Thread-safe
csv_lock = Lock()
seen_urls = set()
stats_lock = Lock()

# Statistics
total_articles_found = 0
total_articles_with_tickers = 0

# ============= HELPER FUNCTIONS =============
def contains_target_ticker(text):
    """Check if text mentions FPT, BID, or BIDV"""
    if not text:
        return False, []
    
    text_upper = text.upper()
    matched = []
    
    ticker_patterns = {
        "FPT": [
            r'\bFPT\b',
            r'CỔ PHIẾU FPT',
            r'FPT CORPORATION',
            r'TẬP ĐOÀN FPT',
            r'\(FPT\)',
        ],
        "BID": [
            r'\bBID\b',
            r'\bBIDV\b',
            r'CỔ PHIẾU BID',
            r'CỔ PHIẾU BIDV',
            r'NGÂN HÀNG BIDV',
            r'ĐẦU TƯ VÀ PHÁT TRIỂN',
            r'\(BID\)',
            r'\(BIDV\)',
        ],
    }
    
    for ticker, patterns in ticker_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_upper):
                if ticker not in matched:
                    matched.append(ticker)
                break
    
    return len(matched) > 0, matched

def parse_date(date_str):
    """Parse date to ISO format (chỉ ngày tháng năm, không có thứ)"""
    if not date_str:
        return ""
    
    # Remove day of week (Thứ 2, Thứ 3, ..., Chủ nhật, etc.)
    date_str = re.sub(r'(Thứ\s+\d+|Chủ\s+nhật|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]*', '', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d/%m/%Y, %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%H:%M %d/%m/%Y",
        "%H:%M, %d/%m/%Y",
        "%H:%M - %d/%m/%Y",
        "%d/%m/%Y - %H:%M",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    return date_str

def is_date_in_range(date_str):
    """Check if date is within START_DATE and END_DATE"""
    if not date_str:
        return True  # Keep if can't determine date
    
    try:
        # Try to parse the date
        parsed = parse_date(date_str)
        if not parsed or len(parsed) < 10:
            return True
        
        date_part = parsed[:10]
        article_date = datetime.strptime(date_part, "%Y-%m-%d")
        
        return START_DATE <= article_date <= END_DATE
    except:
        return True  # Keep if can't parse

# ============= VNEXPRESS CRAWLER =============
class VnExpressCrawler:
    BASE_URL = "https://vnexpress.net"
    # URL đúng: date_format=all, fromdate=0, todate=0
    SEARCH_URL = "https://timkiem.vnexpress.net/?q={query}&media_type=text&fromdate=0&todate=0&latest=&cate_code=&search_f=title,tag_list&date_format=all&page={page}"
    
    @staticmethod
    def get_all_article_links(keyword, max_pages=1000):
        """
        Crawl TẤT CẢ article links cho keyword (all time)
        """
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"\n  🔍 Keyword: '{keyword}'", file=sys.stderr)
        
        consecutive_empty = 0
        for page in range(1, max_pages + 1):
            if consecutive_empty >= 5:
                print(f"    ⚠️  Stopped at page {page-1} (no more results)", file=sys.stderr)
                break
            
            url = VnExpressCrawler.SEARCH_URL.format(
                query=keyword.replace(' ', '+'),
                page=page
            )
            
            try:
                resp = requests.get(url, headers=headers, timeout=45)
                if resp.status_code != 200:
                    consecutive_empty += 1
                    time.sleep(1)
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                articles = soup.find_all('h3', class_='title-news')
                
                if not articles:
                    consecutive_empty += 1
                    continue
                
                consecutive_empty = 0
                page_links = 0
                
                for article in articles:
                    a_tag = article.find('a', href=True)
                    if a_tag:
                        href = a_tag.get('href', '')
                        if href.startswith('http'):
                            links.append(('vnexpress', href))
                            page_links += 1
                        elif href.startswith('/'):
                            links.append(('vnexpress', VnExpressCrawler.BASE_URL + href))
                            page_links += 1
                
                if page % 20 == 0:  # Progress every 20 pages
                    print(f"    📄 Page {page}: {page_links} links | Total: {len(links)}", file=sys.stderr)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"    ⚠️  Error page {page}: {e}", file=sys.stderr)
                consecutive_empty += 1
                time.sleep(1)
        
        print(f"    ✅ Total: {len(links)} links from {page-1} pages", file=sys.stderr)
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract title, content, date from VnExpress article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=45)
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

# ============= DANTRI CRAWLER =============
class DanTriCrawler:
    BASE_URL = "https://dantri.com.vn"
    # URL đúng: https://dantri.com.vn/tim-kiem/{query}.htm
    SEARCH_URL = "https://dantri.com.vn/tim-kiem/{query}.htm?page={page}"
    
    @staticmethod
    def get_all_article_links(keyword, max_pages=500):
        """
        Crawl TẤT CẢ article links cho keyword từ Dân Trí (all time)
        """
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"\n  🔍 Keyword: '{keyword}'", file=sys.stderr)
        
        # Replace spaces with hyphens for URL
        query_formatted = keyword.replace(' ', '-')
        
        consecutive_empty = 0
        for page in range(1, max_pages + 1):
            if consecutive_empty >= 5:
                print(f"    ⚠️  Stopped at page {page-1} (no more results)", file=sys.stderr)
                break
            
            url = DanTriCrawler.SEARCH_URL.format(
                query=query_formatted,
                page=page
            )
            
            try:
                resp = requests.get(url, headers=headers, timeout=45)
                if resp.status_code != 200:
                    consecutive_empty += 1
                    time.sleep(1)
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                articles = soup.select("h3.article-title a, h4.article-title a, a.article-title")
                
                if not articles:
                    consecutive_empty += 1
                    continue
                
                consecutive_empty = 0
                page_links = 0
                
                for article in articles:
                    href = article.get('href', '')
                    if href:
                        if href.startswith('http'):
                            links.append(('dantri', href))
                            page_links += 1
                        elif href.startswith('/'):
                            links.append(('dantri', DanTriCrawler.BASE_URL + href))
                            page_links += 1
                
                if page % 20 == 0:  # Progress every 20 pages
                    print(f"    📄 Page {page}: {page_links} links | Total: {len(links)}", file=sys.stderr)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"    ⚠️  Error page {page}: {e}", file=sys.stderr)
                consecutive_empty += 1
                time.sleep(1)
        
        print(f"    ✅ Total: {len(links)} links from {page-1} pages", file=sys.stderr)
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract title, content, date from Dân Trí article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.title-page, h1.article-title, h1.dt-news__title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("div.singular-content, div.article-content, div.dt-news__content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("time.author-time, span.author-time, time, span.dt-news__time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= CAFEF CRAWLER =============
class CafeFCrawler:
    BASE_URL = "https://cafef.vn"
    SEARCH_URL = "https://cafef.vn/tim-kiem.chn?keywords={query}&page={page}"
    
    @staticmethod
    def get_all_article_links(keyword, max_pages=500):
        """
        Crawl TẤT CẢ article links cho keyword từ CafeF (all time)
        """
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"\n  🔍 Keyword: '{keyword}'", file=sys.stderr)
        
        consecutive_empty = 0
        for page in range(1, max_pages + 1):
            if consecutive_empty >= 5:
                print(f"    ⚠️  Stopped at page {page-1} (no more results)", file=sys.stderr)
                break
            
            url = CafeFCrawler.SEARCH_URL.format(
                query=keyword.replace(' ', '+'),
                page=page
            )
            
            try:
                resp = requests.get(url, headers=headers, timeout=45)
                if resp.status_code != 200:
                    consecutive_empty += 1
                    time.sleep(1)
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                all_links = soup.find_all('a', href=True)
                
                found_articles = False
                for a in all_links:
                    href = a.get('href', '')
                    
                    # Check if link contains news article pattern
                    if '.chn' in href:
                        found_articles = True
                        if not href.startswith('http'):
                            href = CafeFCrawler.BASE_URL + href
                        links.append(('cafef', href))
                
                if not found_articles:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0
                
                if page % 20 == 0:  # Progress every 20 pages
                    print(f"    📄 Page {page}: found links | Total: {len(links)}", file=sys.stderr)
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                print(f"    ⚠️  Error page {page}: {e}", file=sys.stderr)
                consecutive_empty += 1
                time.sleep(1)
        
        print(f"    ✅ Total: {len(links)} links from {page-1} pages", file=sys.stderr)
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract title, content, date from CafeF article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one(".title-detail, h1, h1.title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one(".detail-content, .main-content, #mainContent")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one(".date, time, span.time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= ARTICLE PROCESSING =============
def process_article(source, url):
    """Process single article"""
    global total_articles_found, total_articles_with_tickers
    
    if url in seen_urls:
        return None
    
    seen_urls.add(url)
    
    # Extract content based on source
    if source == 'vnexpress':
        title, content, date_str = VnExpressCrawler.extract_content(url)
    elif source == 'dantri':
        title, content, date_str = DanTriCrawler.extract_content(url)
    elif source == 'cafef':
        title, content, date_str = CafeFCrawler.extract_content(url)
    else:
        return None
    
    # Validate
    if not content or len(content) < 100:
        return None
    
    # Check date range
    if not is_date_in_range(date_str):
        return None
    
    with stats_lock:
        total_articles_found += 1
    
    # Check if mentions FPT, BID, or BIDV
    full_text = f"{title} {content}"
    has_ticker, matched_tickers = contains_target_ticker(full_text)
    
    if not has_ticker:
        return None
    
    with stats_lock:
        total_articles_with_tickers += 1
    
    # Parse date
    parsed_date = parse_date(date_str)
    
    if not title:
        title = content[:50] + "..."
    
    tickers_str = ",".join(matched_tickers)
    print(f"[FOUND] ✅ {tickers_str} | {parsed_date} | {title[:60]}...", file=sys.stderr)
    
    return {
        "date": parsed_date,
        "title": title,
        "content": content,
        "tickers": tickers_str,
        "source": f"{source}:{url}"
    }

def save_batch_to_csv(batch, output_file):
    """Save batch to CSV (thread-safe)"""
    with csv_lock:
        file_exists = os.path.exists(output_file)
        
        with open(output_file, 'a', encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "title", "content", "tickers", "source"])
            if not file_exists:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

# ============= MAIN CRAWLER =============
current_batch = []

def crawl_vnexpress_all_time(output_file):
    """Main crawler - cào TẤT CẢ từ VnExpress"""
    global current_batch
    batch = []
    current_batch = batch
    
    if os.path.exists(output_file):
        os.remove(output_file)
    
    total_records = 0
    
    print("\n" + "="*80, file=sys.stderr)
    print("📈 VNEXPRESS + DÂN TRÍ STOCK NEWS CRAWLER - ALL TIME", file=sys.stderr)
    print("="*80, file=sys.stderr)
    print(f"[INFO] Strategy: Crawl ALL pages (no date filter on search)", file=sys.stderr)
    print(f"[INFO] Sources: VnExpress + Dân Trí", file=sys.stderr)
    print(f"[INFO] Filter: 2015-01-01 to 2025-10-30, FPT/BID mention", file=sys.stderr)
    print(f"[INFO] Keywords: {', '.join(SEARCH_KEYWORDS)}", file=sys.stderr)
    print(f"[INFO] Output: {output_file}", file=sys.stderr)
    print("="*80, file=sys.stderr)
    
    # Crawl by KEYWORD
    for keyword in SEARCH_KEYWORDS:
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"🔍 CRAWLING KEYWORD: '{keyword}'", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        # Get all links from VnExpress
        print(f"\n📰 Source: VNEXPRESS", file=sys.stderr)
        vnexpress_links = VnExpressCrawler.get_all_article_links(keyword, max_pages=300)
        
        # Get all links from Dân Trí
        print(f"\n📰 Source: DÂN TRÍ", file=sys.stderr)
        dantri_links = DanTriCrawler.get_all_article_links(keyword, max_pages=300)
        dantri_links = []
        
        # Get all links from CafeF
        print(f"\n📰 Source: CAFEF", file=sys.stderr)
        cafef_links = CafeFCrawler.get_all_article_links(keyword, max_pages=300)

        # Combine all links
        links = vnexpress_links + dantri_links + cafef_links
        
        if not links:
            print(f"  ⚠️  No links found for '{keyword}'", file=sys.stderr)
            continue
        
        print(f"\n  📊 Total links: {len(links)} (VnExpress: {len(vnexpress_links)}, CafeF: {len(cafef_links)})", file=sys.stderr)
        
        # Process articles
        print(f"\n  🔄 Processing {len(links)} articles...", file=sys.stderr)
        
        processed = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_article, source, url): (source, url) 
                for source, url in links
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        batch.append(result)
                        total_records += 1
                        
                        if len(batch) >= BATCH_SIZE:
                            save_batch_to_csv(batch, output_file)
                            print(f"  [SAVE] 💾 Saved {len(batch)} records. Total: {total_records}", file=sys.stderr)
                            batch = []
                            current_batch = batch
                    
                    processed += 1
                    if processed % 500 == 0:
                        print(f"  📊 Processed: {processed}/{len(links)}, Found: {total_records}", file=sys.stderr)
                        
                except Exception as e:
                    pass
        
        print(f"\n  ✅ Keyword '{keyword}' done: {total_records} articles saved", file=sys.stderr)
    
    # Save final batch
    if batch:
        save_batch_to_csv(batch, output_file)
        print(f"\n[SAVE] 💾 Saved final {len(batch)} records", file=sys.stderr)
    
    return total_records

# ============= MAIN =============
if __name__ == "__main__":
    print("="*80)
    print("📈 STOCK MARKET NEWS CRAWLER V2 (VnExpress + Dân Trí + CafeF)")
    print("="*80)
    print(f"[INFO] Sources: VnExpress + Dân Trí + CafeF (all time, no date filter)")
    print(f"[INFO] Filter: 2015-2025, FPT/BID mentions")
    
    data_folder = "data"
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    
    output_file = os.path.join(data_folder, "stock_market_news_fpt_bid_2015_2025.csv")
    
    if os.path.exists(output_file):
        print(f"\n[WARNING] ⚠️  File exists: {output_file}")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Cancelled")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    try:
        total = crawl_vnexpress_all_time(output_file)
        
        elapsed = time.time() - start_time
        print("\n" + "="*80)
        print(f"[SUCCESS] ✅ Crawl completed!")
        print(f"[STATS] 📊 Articles processed: {total_articles_found}")
        print(f"[STATS] 📊 Articles with FPT/BID: {total_articles_with_tickers}")
        print(f"[STATS] 📊 Articles saved: {total}")
        print(f"[STATS] 📊 Filter rate: {total_articles_with_tickers/total_articles_found*100:.1f}%" if total_articles_found > 0 else "")
        print(f"[TIME] ⏱️  Duration: {elapsed/60:.2f} minutes")
        print(f"[SPEED] 🚄 Speed: {total/(elapsed/60):.1f} articles/min" if elapsed > 0 else "")
        print(f"[FILE] 📁 {output_file}")
        print("="*80)
        
        # Ticker distribution
        if os.path.exists(output_file):
            print("\n📊 Ticker Distribution:")
            ticker_counts = {"FPT": 0, "BID": 0, "BOTH": 0}
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tickers = row.get('tickers', '')
                    if 'FPT' in tickers and 'BID' in tickers:
                        ticker_counts["BOTH"] += 1
                    elif 'FPT' in tickers:
                        ticker_counts["FPT"] += 1
                    elif 'BID' in tickers:
                        ticker_counts["BID"] += 1
            
            print(f"  FPT only: {ticker_counts['FPT']:>5} articles")
            print(f"  BID only: {ticker_counts['BID']:>5} articles")
            print(f"  Both:     {ticker_counts['BOTH']:>5} articles")
            print(f"  Total:    {sum(ticker_counts.values()):>5} articles")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Interrupted by user")
        if current_batch:
            save_batch_to_csv(current_batch, output_file)
            print(f"[SAVE] 💾 Saved {len(current_batch)} records before exit")
    except Exception as e:
        print(f"\n[ERROR] ❌ {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
