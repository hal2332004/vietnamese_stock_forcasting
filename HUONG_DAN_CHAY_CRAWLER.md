# 📋 HƯỚNG DẪN CHẠY CRAWLER FULL 10 NĂM

## 🎯 Mục tiêu
Crawl tin tức cho 5 tickers (ACB, BID, VCB, MBB, FPT) từ 2015-2025, lưu thành 5 file CSV riêng biệt.

## 📊 Kết quả mong đợi
- **5 file CSV**: `news_ACB_2015_2025.csv`, `news_BID_2015_2025.csv`, ...
- **250+ bài/ticker/năm** = ~2,500-3,000 bài/ticker
- **Tổng cộng**: ~12,000-15,000 articles
- **Thời gian**: 20-30 phút

## 🚀 CÁCH 1: Chạy trực tiếp (Có thể theo dõi)

```bash
# 1. Kích hoạt virtual environment
cd "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode"
source "/mnt/d/Ky 4/financial-news-sentiment-main/venv/bin/activate"

# 2. Chạy crawler
python multi_source_crawler.py

# Khi được hỏi "Overwrite all? (y/n):" → nhấn 'y' và Enter
```

**Ưu điểm**: Xem output trực tiếp, dễ debug  
**Nhược điểm**: Phải giữ terminal mở

---

## 🌙 CÁCH 2: Chạy background (Tự động chạy)

```bash
# 1. Kích hoạt virtual environment và chuyển thư mục
cd "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode"
source "/mnt/d/Ky 4/financial-news-sentiment-main/venv/bin/activate"

# 2. Chạy trong background với nohup
nohup python multi_source_crawler.py > crawler_full.log 2>&1 << EOF &
y
EOF

# 3. Lấy PID (Process ID)
echo $! > crawler.pid
echo "Crawler started with PID: $(cat crawler.pid)"
```

**Ưu điểm**: Chạy background, có thể đóng terminal  
**Nhược điểm**: Không thấy output trực tiếp

### Theo dõi tiến độ:
```bash
# Xem log real-time
tail -f crawler_full.log

# Xem 50 dòng cuối
tail -50 crawler_full.log

# Xem tiến độ (YEAR, articles saved)
tail -100 crawler_full.log | grep -E "(YEAR|✅.*articles|SAVE)"

# Kiểm tra crawler còn chạy không
ps aux | grep multi_source_crawler | grep -v grep
```

### Dừng crawler (nếu cần):
```bash
# Đọc PID từ file
kill $(cat crawler.pid)

# Hoặc dừng trực tiếp
pkill -f multi_source_crawler.py
```

---

## 📈 Theo dõi tiến độ trong khi chạy

### Kiểm tra số lượng bài đã crawl:
```bash
# Đếm số dòng từng file (trừ header)
wc -l news_*_2015_2025.csv

# Xem chi tiết từng ticker
for ticker in ACB BID VCB MBB FPT; do
    file="news_${ticker}_2015_2025.csv"
    if [ -f "$file" ]; then
        count=$(($(wc -l < "$file") - 1))
        echo "$ticker: $count articles"
    fi
done
```

### Kiểm tra tiến độ theo năm:
```bash
# ACB - đếm theo năm
for year in {2015..2025}; do
    count=$(grep -c "^$year-" news_ACB_2015_2025.csv 2>/dev/null || echo "0")
    echo "ACB $year: $count articles"
done
```

### Xem 10 bài mới nhất:
```bash
tail -10 news_ACB_2015_2025.csv
```

---

## 📊 Sau khi crawl xong

### 1. Kiểm tra kết quả:
```bash
# Xem thống kê cuối cùng từ log
tail -100 crawler_full.log

# Hoặc tạo thống kê mới
python << EOF
import csv

tickers = ["ACB", "BID", "VCB", "MBB", "FPT"]
print("="*60)
print("📊 FINAL STATISTICS")
print("="*60)

total = 0
for ticker in tickers:
    filename = f"news_{ticker}_2015_2025.csv"
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            count = sum(1 for _ in f) - 1  # Subtract header
            total += count
            size_mb = os.path.getsize(filename) / (1024*1024)
            print(f"{ticker}: {count:>5} articles | {size_mb:>6.2f} MB")
    except:
        print(f"{ticker}: File not found")

print("="*60)
print(f"TOTAL: {total:>5} articles")
EOF
```

### 2. Validate dữ liệu:
```bash
# Kiểm tra file có đúng format không
head -5 news_ACB_2015_2025.csv

# Kiểm tra có bài trùng không (so sánh source column)
python << EOF
import csv

def check_duplicates(ticker):
    filename = f"news_{ticker}_2015_2025.csv"
    urls = set()
    duplicates = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['source']
            if url in urls:
                duplicates += 1
            urls.add(url)
    
    print(f"{ticker}: {len(urls)} unique URLs, {duplicates} duplicates")

for ticker in ["ACB", "BID", "VCB", "MBB", "FPT"]:
    check_duplicates(ticker)
EOF
```

---

## 🔧 Xử lý lỗi

### Nếu crawler bị dừng giữa chừng:
```bash
# Kiểm tra log để xem lỗi gì
tail -100 crawler_full.log

# Chạy lại - crawler sẽ hỏi có overwrite không
# Nếu muốn tiếp tục thêm vào file cũ, cần chỉnh code
```

### Nếu thiếu packages:
```bash
pip install requests beautifulsoup4
```

### Nếu bị timeout:
- Tăng `REQUEST_DELAY` trong code (từ 0.2 → 0.5)
- Giảm `MAX_WORKERS` (từ 5 → 3)

---

## 💾 Backup dữ liệu

```bash
# Nén tất cả CSV files
tar -czf news_backup_$(date +%Y%m%d).tar.gz news_*_2015_2025.csv

# Copy sang thư mục khác
mkdir -p ../backup
cp news_*_2015_2025.csv ../backup/
```

---

## 📝 Notes

1. **Crawler sẽ tự động**:
   - Loại bỏ duplicate URLs
   - Validate content (min 100 chars)
   - Filter theo ticker mentions trong content
   - Retry khi gặp lỗi

2. **File format**:
   - Columns: `date`, `time`, `title`, `content`, `ticker`, `source`
   - Encoding: UTF-8
   - Newline: CRLF (Windows) hoặc LF (Linux)

3. **Thời gian ước tính**:
   - 2015-2019: ~15-20 phút (ít tin hơn)
   - 2020-2025: ~10-15 phút (nhiều tin hơn)
   - Total: 25-35 phút

4. **Nếu muốn crawl lại 1 ticker**:
   ```bash
   # Xóa file cũ
   rm news_ACB_2015_2025.csv
   
   # Sửa code để chỉ crawl ACB
   # TICKERS = ["ACB"]
   
   # Chạy lại
   python multi_source_crawler.py
   ```

---

## ✅ CHECKLIST

Trước khi chạy:
- [ ] Virtual environment đã activate
- [ ] Thư mục đúng: `/Source/recode`
- [ ] Internet connection ổn định
- [ ] Đủ dung lượng ổ đĩa (~500MB)

Trong khi chạy:
- [ ] Theo dõi log định kỳ
- [ ] Kiểm tra file size tăng
- [ ] Monitor memory usage (nếu cần)

Sau khi xong:
- [ ] Validate 5 files CSV
- [ ] Check statistics
- [ ] Backup dữ liệu
- [ ] Test đọc file bằng pandas

---

## 🎉 Kết quả mong đợi

Sau khi hoàn thành, bạn sẽ có:

```
news_ACB_2015_2025.csv  (~100MB, 2,500-3,000 articles)
news_BID_2015_2025.csv  (~80MB,  2,000-2,500 articles)  
news_VCB_2015_2025.csv  (~120MB, 3,000-3,500 articles)
news_MBB_2015_2025.csv  (~90MB,  2,000-2,500 articles)
news_FPT_2015_2025.csv  (~100MB, 2,500-3,000 articles)
```

**TỔNG**: ~500MB, 12,000-15,000 articles

Mỗi file sẵn sàng để:
- Phân tích sentiment
- Training models
- Time series analysis
- Text mining
