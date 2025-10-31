#!/bin/bash
# Helper script để crawl news theo date range cho inference

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="/mnt/d/Ky 4/financial-news-sentiment-main/venv/bin/activate"

cd "$SCRIPT_DIR"
source "$VENV_PATH"

echo "======================================================================="
echo "📅 NEWS CRAWLER FOR MODEL INFERENCE"
echo "======================================================================="
echo ""
echo "Chọn chế độ crawl:"
echo "  1. Hôm nay (today)"
echo "  2. 7 ngày gần đây (last week)"
echo "  3. 30 ngày gần đây (last month)"
echo "  4. Tùy chỉnh (custom date range)"
echo ""
read -p "Chọn (1-4): " mode

case $mode in
    1)
        echo "Crawling hôm nay..."
        python crawler_by_date_range.py --today --tickers ACB,BID,VCB,MBB,FPT
        ;;
    2)
        echo "Crawling 7 ngày gần đây..."
        python crawler_by_date_range.py --last-week --tickers ACB,BID,VCB,MBB,FPT
        ;;
    3)
        echo "Crawling 30 ngày gần đây..."
        python crawler_by_date_range.py --last-month --tickers ACB,BID,VCB,MBB,FPT
        ;;
    4)
        echo ""
        read -p "Nhập ngày bắt đầu (YYYY-MM-DD): " start_date
        read -p "Nhập ngày kết thúc (YYYY-MM-DD): " end_date
        read -p "Nhập tickers (mặc định: ACB,BID,VCB,MBB,FPT): " tickers
        
        if [ -z "$tickers" ]; then
            tickers="ACB,BID,VCB,MBB,FPT"
        fi
        
        echo "Crawling từ $start_date đến $end_date cho $tickers..."
        python crawler_by_date_range.py --start "$start_date" --end "$end_date" --tickers "$tickers"
        ;;
    *)
        echo "Lựa chọn không hợp lệ!"
        exit 1
        ;;
esac

echo ""
echo "======================================================================="
echo "✅ Hoàn tất! File CSV đã sẵn sàng cho inference."
echo "======================================================================="
