"""
TEST SEPARATE CSV FILES
Test với 1 năm và ít pages để nhanh
"""
import sys
sys.path.insert(0, '/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode')

# Import from multi_source_crawler
from multi_source_crawler import *

# Override config for testing
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)
MAX_WORKERS = 3

print("="*70)
print("🧪 TEST SEPARATE CSV FILES")
print("="*70)
print(f"Testing: 1 year (2024), 3 workers, 5 pages per source")
print(f"Expected output: news_2024_2024_ACB.csv, news_2024_2024_BID.csv, etc.")
print("="*70)

# Test crawl
output_file = "news_2024_2024.csv"

# Clear existing test files
for ticker in TICKERS:
    ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
    if os.path.exists(ticker_file):
        os.remove(ticker_file)
        print(f"[CLEAN] Removed old file: {ticker_file}")

print("\n[START] Testing crawler with separate files...")
print("")

try:
    # Override get_article_links to limit pages
    original_vnexpress = VnExpressCrawler.get_article_links
    
    def limited_vnexpress(ticker, year, max_pages=50):
        return original_vnexpress(ticker, year, max_pages=5)  # Only 5 pages
    
    VnExpressCrawler.get_article_links = limited_vnexpress
    
    # Run crawler for 1 ticker only to test
    batch = []
    total = 0
    
    for ticker in ["ACB"]:  # Test with ACB only
        print(f"\n[TEST] Crawling {ticker} 2024...")
        
        links = VnExpressCrawler.get_article_links(ticker, 2024, max_pages=5)
        print(f"  Found {len(links)} links")
        
        # Process first 10 articles
        for i, (source, url) in enumerate(links[:10]):
            result = process_article(source, url, ticker)
            if result:
                batch.append(result)
                total += 1
        
        print(f"  Processed {total} articles")
        
        # Save batch
        if batch:
            save_batch_to_csv(batch, output_file, write_header=True)
            print(f"  ✅ Saved to file")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETED")
    print("="*70)
    
    # Check results
    print("\n📊 Results:")
    for ticker in TICKERS:
        ticker_file = output_file.replace('.csv', f'_{ticker}.csv')
        if os.path.exists(ticker_file):
            with open(ticker_file, 'r', encoding='utf-8') as f:
                count = sum(1 for line in f) - 1
            print(f"  ✅ {ticker}: {count} articles → {ticker_file}")
        else:
            print(f"  ❌ {ticker}: File not created")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
