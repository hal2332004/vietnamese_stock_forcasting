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

# Danh sách mã cổ phiếu ngân hàng
TICKERS = ["ACB", "BID", "VCB", "MBB", "FPT"]
# Khoảng thời gian lấy tin (dùng để filter, không loop từng ngày)
START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2025, 10, 30)

# Nguồn tin tức: cafef.vn (có thể mở rộng thêm)
BASE_URL = "https://cafef.vn"
SEARCH_URL = "https://cafef.vn/tim-kiem.chn?query={query}&sfrom={sfrom}&sto={sto}&page={page}"

# Các query search để lấy nhiều tin nhất
SEARCH_QUERIES = [
    "ngân hàng",
    "chứng khoán",
    "cổ phiếu",
    "tài chính",
]

# Cấu hình tối ưu
MAX_WORKERS = 5  # Số thread đồng thời
BATCH_SIZE = 50  # Lưu sau mỗi 50 bài báo
MAX_RETRIES = 3  # Số lần thử lại khi lỗi
REQUEST_DELAY = 0.15  # Delay giữa các request (giây)
MAX_PAGES_PER_QUERY = 50  # Số trang tối đa cho mỗi query

# Thread-safe
csv_lock = Lock()
seen_urls = set()  # Tránh trùng lặp

# Hàm crawl TẤT CẢ tin tức - chia nhỏ theo năm
def get_all_article_links(max_pages=MAX_PAGES_PER_QUERY):
    """
    Crawl TẤT CẢ bài báo bằng cách:
    1. Chia nhỏ date range theo NĂM (2015, 2016, ..., 2025)
    2. Với mỗi năm, dùng nhiều search queries
    3. Filter theo ticker trong nội dung
    """
    all_links = set()  # Dùng set để tự động loại trùng
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://cafef.vn/',
    }
    
    # Chia theo NĂM
    start_year = START_DATE.year
    end_year = END_DATE.year
    
    print(f"\n[INFO] 🔍 Crawling by YEAR from {start_year} to {end_year}", file=sys.stderr)
    print(f"[INFO] Queries per year: {len(SEARCH_QUERIES)}", file=sys.stderr)
    print(f"[INFO] Target tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Max pages per query: {max_pages}", file=sys.stderr)
    
    # Loop qua từng NĂM
    for year in range(start_year, end_year + 1):
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31) if year < end_year else END_DATE
        
        sfrom = year_start.strftime("%d/%m/%Y")
        sto = year_end.strftime("%d/%m/%Y")
        
        print(f"\n{'#'*70}", file=sys.stderr)
        print(f"[YEAR] 📅 {year}: {sfrom} to {sto}", file=sys.stderr)
        print(f"{'#'*70}", file=sys.stderr)
        
        year_links_before = len(all_links)
        
        # Với mỗi năm, dùng nhiều queries
        for query_idx, query in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[INFO] Query {query_idx}/{len(SEARCH_QUERIES)}: '{query}'", file=sys.stderr)
            
            query_links = 0
            consecutive_empty = 0
            
            for page in range(1, max_pages + 1):
                # Dừng nếu 3 trang liên tiếp không có link mới
                if consecutive_empty >= 3:
                    break
                    
                url = SEARCH_URL.format(query=query, sfrom=sfrom, sto=sto, page=page)
                
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                    
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        if consecutive_empty >= 3:
                            break
                        time.sleep(0.5)
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # Tìm TẤT CẢ article links
                    page_links = soup.find_all('a', href=True)
                    new_count = 0
                    
                    for a in page_links:
                        href = a.get('href', '')
                        
                        # Filter: CafeF article format
                        if '.chn' in href and '188' in href:
                            if not href.startswith('http'):
                                href = BASE_URL + href
                            
                            if href not in all_links:
                                all_links.add(href)
                                query_links += 1
                                new_count += 1
                    
                    if new_count == 0:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
            
            if query_links > 0:
                print(f"  ✅ +{query_links} new links", file=sys.stderr)
        
        year_links_added = len(all_links) - year_links_before
        print(f"\n[YEAR {year}] ✅ Total: +{year_links_added} links (cumulative: {len(all_links)})", file=sys.stderr)
    
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"[SUCCESS] ✅ Total: {len(all_links)} unique article links", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)
    return list(all_links)

# Hàm parse date từ string sang ISO format
def parse_date(date_str):
    """
    Parse date từ nhiều format khác nhau về ISO format: YYYY-MM-DD HH:MM:SS
    """
    if not date_str:
        return ""
    
    # Loại bỏ khoảng trắng thừa
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    # Thử các format khác nhau
    formats = [
        "%d/%m/%Y %H:%M",           # 30/10/2025 14:30
        "%d/%m/%Y - %H:%M",         # 30/10/2025 - 14:30
        "%d/%m/%Y %I:%M %p",        # 30/10/2025 02:30 PM
        "%d-%m-%Y %H:%M",           # 30-10-2025 14:30
        "%d/%m/%Y",                 # 30/10/2025
        "%Y-%m-%d %H:%M:%S",        # 2025-10-30 14:30:00 (already ISO)
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    # Nếu không parse được, trả về string gốc
    return date_str

# Hàm lấy nội dung TOÀN BỘ bài báo với retry
def get_article_content(url, retries=MAX_RETRIES):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[WARNING] HTTP {resp.status_code} for {url}", file=sys.stderr)
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return None, None, None
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # ============= LẤY TITLE =============
            title = ""
            title_selectors = [
                ".title-detail", ".detail-title", ".title",
                "h1.title", "h1", ".main-title",
                ".article-title", ".post-title"
            ]
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # ============= LẤY TOÀN BỘ NỘI DUNG =============
            content = ""
            
            # Phương pháp 1: Tìm container chính của nội dung
            content_containers = [
                ".detail-content", ".main-content", ".content-detail",
                ".article-content", ".post-content", ".entry-content",
                "#mainContent", ".detail-contentmain", ".sapo-detail"
            ]
            
            content_found = False
            for container_selector in content_containers:
                container = soup.select_one(container_selector)
                if container:
                    # Lấy TOÀN BỘ text từ container (bao gồm cả sub-elements)
                    # Loại bỏ scripts, styles, ads
                    for unwanted in container.select("script, style, .ads, .advertisement, .related-news"):
                        unwanted.decompose()
                    
                    # Lấy tất cả text nodes
                    content_parts = []
                    
                    # Ưu tiên lấy từ các thẻ paragraph
                    paragraphs = container.select("p")
                    if paragraphs:
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:  # Lọc các đoạn quá ngắn
                                content_parts.append(text)
                    
                    # Nếu không có paragraph, lấy toàn bộ text từ container
                    if not content_parts:
                        full_text = container.get_text(separator="\n", strip=True)
                        # Loại bỏ các dòng trống và dòng quá ngắn
                        lines = [line.strip() for line in full_text.split("\n") if len(line.strip()) > 20]
                        content_parts.extend(lines)
                    
                    if content_parts:
                        content = " ".join(content_parts)
                        content_found = True
                        break
            
            # Phương pháp 2: Nếu không tìm thấy container, tìm trực tiếp các paragraphs
            if not content_found:
                all_selectors = [
                    "article p", ".article p", ".post p",
                    ".content p", "main p", ".body p"
                ]
                for selector in all_selectors:
                    paragraphs = soup.select(selector)
                    if paragraphs:
                        content_parts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:
                                content_parts.append(text)
                        if content_parts:
                            content = " ".join(content_parts)
                            content_found = True
                            break
            
            # ============= LẤY DATE/TIME =============
            date_str = ""
            date_selectors = [
                ".date", ".pdate", ".time", ".publish-time",
                ".post-time", ".date-time", "time", ".article-date",
                ".timeago", "[datetime]"
            ]
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    # Thử lấy từ attribute datetime trước
                    date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
                    if date_str:
                        break
            
            # Parse date sang ISO format
            parsed_date = parse_date(date_str)
            
            # ============= VALIDATION =============
            # Yêu cầu nội dung tối thiểu 100 ký tự
            if len(content) < 100:
                print(f"[WARNING] Content too short ({len(content)} chars) from {url}", file=sys.stderr)
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
            
            if not title:
                print(f"[WARNING] No title found for {url}", file=sys.stderr)
            
            if not content:
                print(f"[WARNING] No content found for {url}", file=sys.stderr)
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
            
            # Log độ dài content để debug
            if content:
                print(f"[INFO] Extracted {len(content)} chars from {url[:50]}...", file=sys.stderr)
                
            return title, content, parsed_date
            
        except Exception as e:
            if attempt < retries - 1:
                print(f"[WARNING] Retry {attempt+1}/{retries} for {url}: {e}", file=sys.stderr)
                time.sleep(2)
            else:
                print(f"[ERROR] Failed to get content from {url}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                return None, None, None
    
    return None, None, None

# Hàm lưu batch vào CSV (thread-safe)
def save_batch_to_csv(batch, output_file, write_header=False):
    with csv_lock:
        mode = 'w' if write_header else 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

# Hàm detect ticker nào được mention trong bài báo
def detect_tickers_in_content(title, content):
    """
    Phát hiện ticker nào được nhắc đến trong title/content
    Returns: list of tickers found
    """
    text = (title + " " + content).upper()
    found_tickers = []
    
    for ticker in TICKERS:
        # Check ticker name và các biến thể
        ticker_patterns = [
            ticker,  # VD: "ACB"
            f" {ticker} ",  # Word boundary
            f"({ticker})",  # In parentheses
            f"{ticker},",  # With comma
        ]
        
        if any(pattern in text for pattern in ticker_patterns):
            found_tickers.append(ticker)
    
    return found_tickers

# Hàm xử lý 1 article URL (KHÔNG filter ticker ở đây)
def process_article(url):
    # Kiểm tra duplicate
    if url in seen_urls:
        return []
    
    seen_urls.add(url)
    
    title, content, date_str = get_article_content(url)
    
    # Yêu cầu nội dung tối thiểu
    if not content or len(content) < 100:
        return []
    
    # Tách date và time
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
    
    # Nếu không có title, dùng 50 ký tự đầu
    if not title:
        title = content[:50] + "..." if len(content) > 50 else content
    
    # PHÁT HIỆN ticker nào được mention
    mentioned_tickers = detect_tickers_in_content(title, content)
    
    if not mentioned_tickers:
        return []
    
    # Tạo 1 record cho MỖI ticker được mention
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

# Hàm crawl toàn bộ dữ liệu (NEW APPROACH - crawl ALL then filter)
def crawl_news(output_file):
    batch = []
    
    # Khởi tạo file CSV
    save_batch_to_csv([], output_file, write_header=True)
    
    print("\n" + "="*70, file=sys.stderr)
    print(f"[STEP 1] 🔍 CRAWLING ALL ARTICLE LINKS", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    # Lấy TẤT CẢ links (không filter ticker)
    all_links = get_all_article_links(max_pages=MAX_PAGES_PER_QUERY)
    
    if not all_links:
        print("[ERROR] ❌ No links found!", file=sys.stderr)
        return 0
    
    print("\n" + "="*70, file=sys.stderr)
    print(f"[STEP 2] 📝 PROCESSING {len(all_links)} ARTICLES", file=sys.stderr)
    print(f"[INFO] Filtering by tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    # Xử lý song song TẤT CẢ links
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
                results = future.result()  # Can return multiple records
                
                if results:
                    for result in results:
                        batch.append(result)
                        total_records += 1
                        ticker_stats[result['ticker']] += 1
                        
                        # Lưu batch
                        if len(batch) >= BATCH_SIZE:
                            save_batch_to_csv(batch, output_file)
                            print(f"[SAVE] ✅ Saved batch of {len(batch)} records. Total: {total_records}", file=sys.stderr)
                            batch = []
                            
            except Exception as e:
                print(f"[ERROR] {e}", file=sys.stderr)
    
    # Lưu batch cuối
    if batch:
        save_batch_to_csv(batch, output_file)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Thống kê
    print("\n" + "="*70, file=sys.stderr)
    print("📊 STATISTICS BY TICKER:", file=sys.stderr)
    for ticker in TICKERS:
        count = ticker_stats[ticker]
        print(f"  {ticker}: {count:>5} articles", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    return total_records

if __name__ == "__main__":
    print("="*70)
    print("🚀 VIETNAMESE STOCK NEWS CRAWLER - OPTIMIZED VERSION")
    print("="*70)
    print(f"[INFO] Date range: {START_DATE.date()} to {END_DATE.date()}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Max workers: {MAX_WORKERS}, Batch size: {BATCH_SIZE}", file=sys.stderr)
    
    # Tên file output
    output_file = f"news_fulltext_{START_DATE.year}_{END_DATE.year}.csv"
    
    # Kiểm tra file đã tồn tại
    if os.path.exists(output_file):
        print(f"\n[WARNING] File {output_file} đã tồn tại!")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled by user")
            sys.exit(0)
    
    # Bắt đầu crawl
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
        
        # Thống kê theo ticker
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                ticker_counts = {}
                for row in reader:
                    ticker = row['ticker']
                    ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
            
            print("\n📊 Thống kê theo mã cổ phiếu:")
            for ticker in TICKERS:
                count = ticker_counts.get(ticker, 0)
                print(f"  {ticker}: {count:>5} bài báo")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Crawl bị ngắt bởi người dùng")
        print(f"[INFO] Dữ liệu đã crawl được lưu trong {output_file}")
    except Exception as e:
        print(f"\n[ERROR] ❌ Lỗi: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
