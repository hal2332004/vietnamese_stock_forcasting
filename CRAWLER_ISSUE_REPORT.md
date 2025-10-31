# VẤN ĐỀ VỚI CRAWLER CŨ VÀ GIẢI PHÁP

## 🔴 **Vấn đề phát hiện:**

### 1. **Chạy lâu nhưng ít bài viết**
- Chạy **65 phút** (3933 giây) nhưng chỉ có **1253 articles**
- Tốc độ: 19.1 articles/phút → quá chậm

### 2. **Phân bố năm không đều**
```
2015: 1253 articles (ACB: 144, BID: 195, VCB: 116, MBB: 13, FPT: 782)
2016-2023: 0 articles
2024: 3 articles (ACB only)
2025: 0 articles
```

### 3. **CSV có nhiều năm rải rác**
Trong file `news_MBB_2015_2025.csv`:
- Có bài từ **2014, 2020, 2021, 2025**
- Date bị parse sai: "Thứ ba, 15/7/2014, 17:45 (GMT+7)" → lưu vào CSV là "Thứ"
- Chỉ có **14 dòng** trong CSV dù crawler báo crawled 1063 articles cho MBB 2018

### 4. **Ticker detection sai**
- Query "MB" cho MBB nhưng match cả "Quân đội" (Military Bank)
- Ví dụ: Nhiều bài về "Quân đội Israel", "Quân đội Mỹ", "Quân đội Ukraine" được detect là MBB
- Pattern matching quá loose: `"MB" in text` → match với "MB Bank", "MBB", "quân đội Mỹ"

---

## ✅ **Giải pháp trong `multi_source_crawler_fixed.py`:**

### 1. **Fix Date Parsing**
```python
def parse_date(date_str):
    # Xóa "Thứ hai, Thứ ba,..." 
    date_str = re.sub(r'Thứ\s+(hai|ba|tư|năm|sáu|bảy|CN),?\s*', '', date_str, flags=re.IGNORECASE)
    # Xóa (GMT+7)
    date_str = re.sub(r'\(GMT\+\d+\)', '', date_str)
    
    # Parse với multiple formats
    formats = ["%d/%m/%Y, %H:%M", "%d/%m/%Y %H:%M", ...]
    
    # Fallback: extract year bằng regex
    year_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
```

**Kết quả test:**
```
Input:  Thứ ba, 15/7/2014, 17:45 (GMT+7)
Output: 2014-07-15 17:45:00  ✅

Input:  Invalid date string
Output: (empty) → Bỏ qua bài này ✅
```

### 2. **Strict Year Validation**
```python
# Skip if cannot parse date
if not parsed_date or len(parsed_date) < 10:
    return None

# Skip if cannot extract year
article_year = extract_year_from_date(parsed_date)
if not article_year:
    return None

# Skip if wrong year
if article_year != target_year:
    return None
```

### 3. **Flexible Ticker Detection**
```python
TICKER_FULL_NAMES = {
    "ACB": ["ACB", "Á Châu", "Asia Commercial Bank", "ngân hàng ACB", "NH ACB"],
    "BID": ["BID", "BIDV", "Đầu tư và Phát triển", ...],
    "VCB": ["VCB", "Vietcombank", "Ngoại thương", ...],
    "MBB": ["MBB", "MB Bank", "MB", "ngân hàng MB", "Military Bank", "Quân Đội", "NH Quân Đội"],
    "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT", ...],
}

def detect_ticker_in_content(title, content, ticker):
    # Check ALL possible names
    possible_names = TICKER_FULL_NAMES.get(ticker, [ticker])
    for name in possible_names:
        if name.upper() in text:
            return True
```

**Vấn đề còn tồn tại**: MBB vẫn có thể match với "Quân đội" trong context khác
→ Cần thêm **negative keywords** để filter:

```python
NEGATIVE_KEYWORDS = {
    "MBB": ["quân đội Israel", "quân đội Mỹ", "quân đội Ukraine", "quân đội Nga", 
            "quân đội Myanmar", "quân đội Syria", "quân đội Trung Quốc"]
}
```

### 4. **Per-Ticker seen_urls**
```python
# OLD: Global seen_urls → duplicate URLs bị bỏ qua giữa các ticker
seen_urls = set()

# NEW: Separate per ticker
for ticker in TICKERS:
    seen_urls_for_ticker = set()  # Riêng cho từng ticker
    process_article(..., seen_urls_for_ticker)
```

### 5. **Lower Content Threshold**
```python
# OLD: 100 chars minimum
if not content or len(content) < 100:
    return None

# NEW: 50 chars minimum
if not content or len(content) < 50:
    return None
```

---

## 📊 **Kết quả dự kiến sau fix:**

1. ✅ Date parsing chính xác → Đúng năm trong CSV
2. ✅ Year validation → Bỏ qua bài sai năm
3. ✅ Per-ticker URLs → Không bỏ qua bài trùng giữa ticker
4. ✅ Flexible detection → Catch được "Á Châu", "Vietcombank", "MB Bank"
5. ⚠️ Vẫn cần thêm negative keywords cho MBB

---

## 🎯 **Khuyến nghị:**

### Ngay lập tức:
1. ✅ Chạy `multi_source_crawler_fixed.py` thay vì `multi_source_crawler.py`
2. ✅ Xóa các file CSV cũ để crawl lại từ đầu

### Cải tiến thêm:
1. Thêm **negative keywords** để filter bài không liên quan
2. Thêm **positive context** (ví dụ: "lợi nhuận", "cổ phiếu", "tín dụng")
3. Crawl **song song theo năm** thay vì tuần tự (sử dụng multiprocessing)
4. Thêm **retry logic** cho failed requests

### Monitoring:
```bash
# Theo dõi progress
tail -f crawler_output.log | grep "✅"

# Check số lượng theo năm
bash check_progress.sh
```

---

## 📝 **Lệnh chạy:**

```bash
cd /mnt/d/Ky\ 4/financial-news-sentiment-main/Source/recode

# Xóa CSV cũ
rm news_*_2015_2025.csv multi_source_news_2015_2025.csv

# Chạy crawler fixed
nohup python multi_source_crawler_fixed.py > crawler_fixed.log 2>&1 &

# Hoặc test với 1-2 năm trước
# Sửa START_DATE = datetime(2024, 1, 1) trong code
```
