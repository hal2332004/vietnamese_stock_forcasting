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

# Danh sách mã cổ phiếu
TICKERS = ["ACB", "BID", "VCB", "MBB", "FPT"]

# Khoảng thời gian lấy tin
START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2025, 10, 30)

# VnExpress URLs
BASE_URL = "https://vnexpress.net"
SEARCH_URL = "https://timkiem.vnexpress.net/?q={query}&date_from={date_from}&date_to={date_to}&media_type=all&cate_code=&latest=&page={page}"

# Các query search
SEARCH_QUERIES = [
    "ngân hàng",
    "chứng khoán",
    "cổ phiếu",
    "ACB",
    "BID", 
    "VCB",
    "MBB",
    "FPT",
]

# Cấu hình
MAX_WORKERS = 5
BATCH_SIZE = 50
MAX_RETRIES = 3
REQUEST_DELAY = 0.3
MAX_PAGES_PER_QUERY = 50

# Thread-safe
csv_lock = Lock()
seen_urls = set()

# Hàm crawl links từ VnExpress search - chia theo NĂM
def get_all_article_links(max_pages=MAX_PAGES_PER_QUERY):
    """
    Crawl TẤT CẢ bài báo từ VnExpress
    Chia theo NĂM để lấy nhiều kết quả
    """
    all_links = set()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://vnexpress.net/',
    }
    
    start_year = START_DATE.year
    end_year = END_DATE.year
    
    print(f"\n[INFO] 🔍 Crawling VnExpress from {start_year} to {end_year}", file=sys.stderr)
    print(f"[INFO] Queries: {len(SEARCH_QUERIES)}", file=sys.stderr)
    print(f"[INFO] Target tickers: {', '.join(TICKERS)}", file=sys.stderr)
    
    # Loop qua từng NĂM
    for year in range(start_year, end_year + 1):
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31) if year < end_year else END_DATE
        
        date_from = year_start.strftime("%Y-%m-%d")
        date_to = year_end.strftime("%Y-%m-%d")
        
        print(f"\n{'#'*70}", file=sys.stderr)
        print(f"[YEAR] 📅 {year}: {date_from} to {date_to}", file=sys.stderr)
        print(f"{'#'*70}", file=sys.stderr)
        
        year_links_before = len(all_links)
        
        # Với mỗi năm, dùng nhiều queries
        for query in SEARCH_QUERIES:
            print(f"\n[INFO] Query: '{query}'", file=sys.stderr)
            
            query_links = 0
            consecutive_empty = 0
            
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 3:
                    break
                
                url = SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    date_from=date_from,
                    date_to=date_to,
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                    
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        if consecutive_empty >= 3:
                            break
                        time.sleep(1)
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # VnExpress: articles trong <h3 class="title-news">
                    articles = soup.find_all('h3', class_='title-news')
                    
                    new_count = 0
                    for article in articles:
                        a_tag = article.find('a', href=True)
                        if a_tag:
                            href = a_tag.get('href', '')
                            
                            # Construct full URL
                            if href.startswith('http'):
                                full_url = href
                            elif href.startswith('/'):
                                full_url = BASE_URL + href
                            else:
                                continue
                            
                            # Check duplicate
                            if full_url not in all_links:
                                all_links.add(full_url)
                                query_links += 1
                                new_count += 1
                    
                    if new_count == 0:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    print(f"[ERROR] Page {page}: {e}", file=sys.stderr)
                    consecutive_empty += 1
                    time.sleep(1)
            
            if query_links > 0:
                print(f"  ✅ +{query_links} new links", file=sys.stderr)
        
        year_links_added = len(all_links) - year_links_before
        print(f"\n[YEAR {year}] ✅ Total: +{year_links_added} links (cumulative: {len(all_links)})", file=sys.stderr)
    
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"[SUCCESS] ✅ Total: {len(all_links)} unique article links", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)
    return list(all_links)

# Hàm parse date
def parse_date(date_str):
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

# Hàm lấy nội dung bài báo VnExpress
def get_article_content(url, retries=MAX_RETRIES):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None, None, None
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # ============= TITLE =============
            title = ""
            title_selectors = [
                "h1.title-detail",
                "h1.title_news_detail",
                "h1",
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # ============= CONTENT =============
            content = ""
            
            # VnExpress content containers
            content_selectors = [
                "article.fck_detail",
                ".fck_detail",
                "article.content_detail",
                ".content_detail",
            ]
            
            for selector in content_selectors:
                container = soup.select_one(selector)
                if container:
                    # Remove unwanted elements
                    for unwanted in container.select("script, style, .box_brief_info, .box_category, .ads"):
                        unwanted.decompose()
                    
                    # Get all paragraphs
                    paragraphs = container.select("p.Normal")
                    if not paragraphs:
                        paragraphs = container.select("p")
                    
                    if paragraphs:
                        content_parts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:
                                content_parts.append(text)
                        content = " ".join(content_parts)
                        break
            
            # ============= DATE =============
            date_str = ""
            date_selectors = [
                "span.date",
                ".date",
                "time",
                "[datetime]",
            ]
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
                    if date_str:
                        break
            
            parsed_date = parse_date(date_str)
            
            # Validation
            if len(content) < 100:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
            
            if content:
                print(f"[INFO] Extracted {len(content)} chars from {url[:50]}...", file=sys.stderr)
                
            return title, content, parsed_date
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"[ERROR] Failed: {url}: {e}", file=sys.stderr)
                return None, None, None
    
    return None, None, None

# Hàm detect tickers trong content
def detect_tickers_in_content(title, content):
    text = (title + " " + content).upper()
    found_tickers = []
    
    for ticker in TICKERS:
        patterns = [
            ticker,
            f" {ticker} ",
            f"({ticker})",
            f"{ticker},",
        ]
        
        if any(pattern in text for pattern in patterns):
            found_tickers.append(ticker)
    
    return found_tickers

# Hàm xử lý 1 article
def process_article(url):
    if url in seen_urls:
        return []
    
    seen_urls.add(url)
    
    title, content, date_str = get_article_content(url)
    
    if not content or len(content) < 100:
        return []
    
    # Parse date/time
    try:
        if date_str and len(date_str) >= 10:
            if ' ' in date_str:
                date_part, time_part = date_str.split(' ', 1)
            else:
                date_part = date_str[:10]
                time_part = ""
        else:
            date_part = date_str
            time_part = ""
    except:
        date_part = date_str
        time_part = ""
    
    if not title:
        title = content[:50] + "..." if len(content) > 50 else content
    
    # Detect tickers
    mentioned_tickers = detect_tickers_in_content(title, content)
    
    if not mentioned_tickers:
        return []
    
    # Create records
    results = []
    for ticker in mentioned_tickers:
        results.append({
            "date": date_part,
            "time": time_part,
            "title": title,
            "content": content,
            "ticker": ticker,
            "source": url
        })
    
    if results:
        tickers_str = ", ".join(mentioned_tickers)
        print(f"[INFO] ✅ Article mentions: {tickers_str} | {title[:50]}...", file=sys.stderr)
    
    return results

# Hàm lưu batch
def save_batch_to_csv(batch, output_file, write_header=False):
    with csv_lock:
        mode = 'w' if write_header else 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

# Hàm crawl chính
def crawl_news(output_file):
    batch = []
    
    # Init file
    save_batch_to_csv([], output_file, write_header=True)
    
    print("\n" + "="*70, file=sys.stderr)
    print(f"[STEP 1] 🔍 CRAWLING ALL ARTICLE LINKS FROM VNEXPRESS", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    all_links = get_all_article_links(max_pages=MAX_PAGES_PER_QUERY)
    
    if not all_links:
        print("[ERROR] ❌ No links found!", file=sys.stderr)
        return 0
    
    print("\n" + "="*70, file=sys.stderr)
    print(f"[STEP 2] 📝 PROCESSING {len(all_links)} ARTICLES", file=sys.stderr)
    print(f"[INFO] Filtering by tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    total_records = 0
    ticker_stats = {ticker: 0 for ticker in TICKERS}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_article, url): url for url in all_links}
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            
            if completed % 50 == 0:
                print(f"[PROGRESS] Processed {completed}/{len(all_links)} articles ({total_records} records saved)", file=sys.stderr)
            
            try:
                results = future.result()
                
                if results:
                    for result in results:
                        batch.append(result)
                        total_records += 1
                        ticker_stats[result['ticker']] += 1
                        
                        if len(batch) >= BATCH_SIZE:
                            save_batch_to_csv(batch, output_file)
                            print(f"[SAVE] ✅ Saved batch of {len(batch)} records. Total: {total_records}", file=sys.stderr)
                            batch = []
                            
            except Exception as e:
                print(f"[ERROR] {e}", file=sys.stderr)
    
    # Save final batch
    if batch:
        save_batch_to_csv(batch, output_file)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Statistics
    print("\n" + "="*70, file=sys.stderr)
    print("📊 STATISTICS BY TICKER:", file=sys.stderr)
    for ticker in TICKERS:
        count = ticker_stats[ticker]
        print(f"  {ticker}: {count:>5} articles", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    return total_records

if __name__ == "__main__":
    print("="*70)
    print("🚀 VNEXPRESS NEWS CRAWLER")
    print("="*70)
    print(f"[INFO] Date range: {START_DATE.date()} to {END_DATE.date()}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Max workers: {MAX_WORKERS}, Batch size: {BATCH_SIZE}", file=sys.stderr)
    
    output_file = f"vnexpress_news_{START_DATE.year}_{END_DATE.year}.csv"
    
    if os.path.exists(output_file):
        print(f"\n[WARNING] File {output_file} đã tồn tại!")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled by user")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] Crawling started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        total = crawl_news(output_file)
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print(f"[SUCCESS] ✅ Đã lưu {total} bài báo vào {output_file}")
        print(f"[TIME] ⏱️  Thời gian: {elapsed/60:.2f} phút ({elapsed:.1f} giây)")
        print(f"[SPEED] 🚄 Tốc độ: {total/(elapsed/60):.1f} bài/phút")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Crawl bị ngắt bởi người dùng")
        print(f"[INFO] Dữ liệu đã crawl được lưu trong {output_file}")
    except Exception as e:
        print(f"\n[ERROR] ❌ Lỗi: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
