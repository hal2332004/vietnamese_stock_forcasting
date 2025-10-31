#!/bin/bash
# Script to run multi-source crawler in background

cd "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode"
source "/mnt/d/Ky 4/financial-news-sentiment-main/venv/bin/activate"

echo "🚀 Starting Multi-Source News Crawler..."
echo "📅 Period: 2015-2025"
echo "💼 Tickers: ACB, BID, VCB, MBB, FPT"
echo "🎯 Target: 250+ articles/ticker/year"
echo ""

# Run crawler and save output
nohup python multi_source_crawler.py << EOF > crawler_output.log 2>&1 &
y
EOF

# Get PID
CRAWLER_PID=$!

echo "✅ Crawler started with PID: $CRAWLER_PID"
echo "📝 Output: crawler_output.log"
echo ""
echo "To monitor progress:"
echo "  tail -f crawler_output.log"
echo ""
echo "To check status:"
echo "  ps aux | grep multi_source_crawler"
echo ""
echo "To stop:"
echo "  kill $CRAWLER_PID"
