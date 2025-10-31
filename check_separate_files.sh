#!/bin/bash

# CHECK SEPARATE CSV FILES
echo "========================================================================"
echo "📊 CHECK SEPARATE CSV FILES FOR EACH TICKER"
echo "========================================================================"
echo ""

BASE_DIR="/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode"
cd "$BASE_DIR"

TICKERS=("ACB" "BID" "VCB" "MBB" "FPT")

echo "Checking for files: news_2015_2025_*.csv"
echo ""

total_articles=0

for ticker in "${TICKERS[@]}"; do
    file="news_2015_2025_${ticker}.csv"
    
    if [ -f "$file" ]; then
        # Count lines (excluding header)
        count=$(($(wc -l < "$file") - 1))
        total_articles=$((total_articles + count))
        
        echo "✅ $ticker: $count articles"
        echo "   File: $file"
        
        # Show first 2 lines
        echo "   Sample:"
        head -2 "$file" | tail -1 | cut -c1-100
        echo ""
    else
        echo "❌ $ticker: File not found"
        echo "   Expected: $file"
        echo ""
    fi
done

echo "========================================================================"
echo "📈 TOTAL: $total_articles articles across all tickers"
echo "========================================================================"

# Check if old combined file exists
if [ -f "multi_source_news_2015_2025.csv" ]; then
    old_count=$(($(wc -l < "multi_source_news_2015_2025.csv") - 1))
    echo ""
    echo "⚠️  Old combined file still exists: multi_source_news_2015_2025.csv ($old_count articles)"
    echo "   Consider deleting it to avoid confusion"
fi
