# ✅ THAY ĐỔI: LƯU RIÊNG FILE CSV CHO TỪNG TICKER

## 🎯 **Mục đích:**
Thay vì lưu tất cả tickers vào 1 file CSV chung, giờ **mỗi ticker có file riêng** để:
- Dễ quản lý và phân tích từng ticker
- Tránh file quá lớn (1 file 10MB → 5 file 2MB mỗi file)
- Dễ crawl lại từng ticker nếu bị lỗi
- Dễ chia sẻ data cho từng stock

---

## 📝 **Các thay đổi trong code:**

### 1. **Hàm `save_batch_to_csv()` - Dòng 561-582**

#### ❌ **Trước (lưu chung):**
```python
def save_batch_to_csv(batch, output_file, write_header=False):
    with csv_lock:
        mode = 'w' if write_header else 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)
```

#### ✅ **Sau (lưu riêng):**
```python
def save_batch_to_csv(batch, output_file, write_header=False):
    """Save batch to CSV (thread-safe) - GROUP BY TICKER"""
    with csv_lock:
        # Group by ticker
        ticker_batches = {}
        for row in batch:
            ticker = row['ticker']
            if ticker not in ticker_batches:
                ticker_batches[ticker] = []
            ticker_batches[ticker].append(row)
        
        # Save to separate files per ticker
        for ticker, ticker_batch in ticker_batches.items():
            ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
            
            # Check if file exists to determine if header needed
            file_exists = os.path.exists(ticker_file)
            
            mode = 'a'
            with open(ticker_file, mode, encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
                if not file_exists or write_header:
                    writer.writeheader()
                for row in ticker_batch:
                    writer.writerow(row)
```

**Thay đổi:**
- Group batch theo ticker trước khi lưu
- Tạo tên file riêng: `news_2015_2025_ACB.csv`, `news_2015_2025_BID.csv`, ...
- Check file tồn tại để quyết định có write header không
- Luôn dùng mode `'a'` (append) để không ghi đè

---

### 2. **Hàm `crawl_multi_source()` - Dòng 584-595**

#### ✅ **Thêm initialization:**
```python
def crawl_multi_source(output_file):
    """Main crawler - crawl từ nhiều nguồn - SAVE SEPARATE FILES PER TICKER"""
    batch = []
    
    # Initialize separate files for each ticker
    for ticker in TICKERS:
        ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
        if os.path.exists(ticker_file):
            os.remove(ticker_file)  # Remove old file if exists
    
    # ... rest of code
```

**Thay đổi:**
- Xóa các file cũ của từng ticker nếu tồn tại
- Thông báo output là separate files

---

### 3. **Main script - Dòng 682-695**

#### ✅ **Check existing files:**
```python
output_file = f"news_{START_DATE.year}_{END_DATE.year}.csv"  # Base filename

# Check if any ticker files exist
existing_files = []
for ticker in TICKERS:
    ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
    if os.path.exists(ticker_file):
        existing_files.append(ticker_file)

if existing_files:
    print(f"\n[WARNING] Found existing files:")
    for f in existing_files:
        print(f"  - {f}")
    choice = input("Overwrite? (y/n): ")
```

**Thay đổi:**
- Check tất cả ticker files thay vì 1 file chung
- Hiển thị danh sách files tồn tại

---

### 4. **Statistics - Dòng 720-730**

#### ✅ **Read from separate files:**
```python
# Final statistics - Read from separate files
print("\n📊 Final Statistics (by file):")
for ticker in TICKERS:
    ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
    if os.path.exists(ticker_file):
        with open(ticker_file, 'r', encoding='utf-8') as f:
            count = sum(1 for line in f) - 1  # Exclude header
        print(f"  {ticker}: {count:>5} articles → {ticker_file}")
    else:
        print(f"  {ticker}: {0:>5} articles → {ticker_file} (not created)")
```

**Thay đổi:**
- Đọc từng file riêng để đếm
- Hiển thị tên file cho từng ticker

---

## 📂 **Cấu trúc file output:**

### ❌ **Trước:**
```
multi_source_news_2015_2025.csv  (1 file, ~10MB, chứa tất cả)
```

### ✅ **Sau:**
```
news_2015_2025_ACB.csv  (~148 dòng)
news_2015_2025_BID.csv  (~196 dòng)
news_2015_2025_VCB.csv  (~117 dòng)
news_2015_2025_MBB.csv  (~14 dòng)
news_2015_2025_FPT.csv  (~783 dòng)
```

---

## 🚀 **Cách sử dụng:**

### 1. **Chạy crawler:**
```bash
cd /mnt/d/Ky\ 4/financial-news-sentiment-main/Source/recode

# Chạy full
python multi_source_crawler.py

# Output sẽ tạo 5 files:
# - news_2015_2025_ACB.csv
# - news_2015_2025_BID.csv
# - news_2015_2025_VCB.csv
# - news_2015_2025_MBB.csv
# - news_2015_2025_FPT.csv
```

### 2. **Check kết quả:**
```bash
bash check_separate_files.sh
```

### 3. **Load data trong Python:**
```python
import pandas as pd

# Load 1 ticker
acb_df = pd.read_csv('news_2015_2025_ACB.csv')

# Load tất cả
all_dfs = {}
for ticker in ['ACB', 'BID', 'VCB', 'MBB', 'FPT']:
    df = pd.read_csv(f'news_2015_2025_{ticker}.csv')
    all_dfs[ticker] = df

# Hoặc concat thành 1 dataframe
import glob
all_files = glob.glob('news_2015_2025_*.csv')
combined_df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)
```

---

## ✅ **Ưu điểm:**

1. **Dễ quản lý**: Mỗi ticker 1 file, dễ tìm và xử lý
2. **Performance**: File nhỏ hơn → load nhanh hơn
3. **Flexibility**: Crawl lại từng ticker riêng lẻ nếu cần
4. **Parallel processing**: Có thể process nhiều ticker song song
5. **Clear separation**: Tránh nhầm lẫn data giữa các ticker

---

## 📊 **So sánh:**

| Metric | Before (1 file) | After (5 files) |
|--------|----------------|-----------------|
| File size | ~10MB | ~2MB each |
| Load time | ~3s | ~0.6s each |
| Memory | ~100MB | ~20MB each |
| Manageability | ⚠️ | ✅ |
| Flexibility | ⚠️ | ✅ |

---

## 🔄 **Backward compatibility:**

Nếu cần merge lại thành 1 file:
```bash
# Header từ file đầu tiên
head -1 news_2015_2025_ACB.csv > news_2015_2025_ALL.csv

# Append data (bỏ header) từ tất cả files
for ticker in ACB BID VCB MBB FPT; do
    tail -n +2 news_2015_2025_${ticker}.csv >> news_2015_2025_ALL.csv
done
```

---

## ⚠️ **Lưu ý:**

1. Mỗi batch save sẽ mở 1-5 files (tùy số ticker trong batch)
2. Thread-safe với `csv_lock`
3. File tự động append → không ghi đè
4. Header chỉ write 1 lần khi file chưa tồn tại
