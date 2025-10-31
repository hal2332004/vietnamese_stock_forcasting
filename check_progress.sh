#!/bin/bash
# Monitor crawler progress and statistics

OUTPUT_FILE="multi_source_news_2015_2025.csv"
LOG_FILE="crawler_output.log"

echo "======================================================================="
echo "📊 CRAWLER PROGRESS MONITOR"
echo "======================================================================="
echo ""

# Check if crawler is running
if ps aux | grep -q "[m]ulti_source_crawler.py"; then
    echo "✅ Status: RUNNING"
else
    echo "⚠️  Status: NOT RUNNING"
fi

echo ""
echo "📝 Latest log entries:"
echo "-----------------------------------------------------------------------"
tail -20 "$LOG_FILE" | grep -E "(YEAR|Ticker:|Found|articles|SAVE)"
echo ""

# Check CSV file statistics
if [ -f "$OUTPUT_FILE" ]; then
    echo "======================================================================="
    echo "📈 CURRENT STATISTICS"
    echo "======================================================================="
    
    # Count total articles
    TOTAL=$(wc -l < "$OUTPUT_FILE")
    TOTAL=$((TOTAL - 1))  # Subtract header
    echo "Total articles collected: $TOTAL"
    echo ""
    
    # Count by ticker
    echo "By Ticker:"
    for TICKER in ACB BID VCB MBB FPT; do
        COUNT=$(grep -c ",$TICKER," "$OUTPUT_FILE" 2>/dev/null || echo "0")
        echo "  $TICKER: $COUNT articles"
    done
    echo ""
    
    # Count by year (from date column)
    echo "By Year:"
    for YEAR in {2015..2025}; do
        COUNT=$(grep -c "^$YEAR-" "$OUTPUT_FILE" 2>/dev/null || echo "0")
        if [ "$COUNT" -gt 0 ]; then
            echo "  $YEAR: $COUNT articles"
        fi
    done
    
else
    echo "⚠️  CSV file not found yet"
fi

echo ""
echo "======================================================================="
echo "Commands:"
echo "  Watch live: tail -f $LOG_FILE"
echo "  Stop crawler: pkill -f multi_source_crawler.py"
echo "======================================================================="
