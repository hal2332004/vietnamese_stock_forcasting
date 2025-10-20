import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time

# Danh sách mã cổ phiếu ngân hàng
TICKERS = ["ACB", "BID", "VCB", "MBB"]
# Khoảng thời gian lấy tin
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 10, 1)

# Nguồn tin tức: cafef.vn (có thể mở rộng thêm)
BASE_URL = "https://cafef.vn"
SEARCH_URL = "https://cafef.vn/tim-kiem.chn?query={query}&sfrom={sfrom}&sto={sto}&page={page}"

# Hàm lấy danh sách link bài báo theo ticker và ngày

def get_article_links(ticker, sfrom, sto, max_pages=5):
    links = []
    for page in range(1, max_pages+1):
        url = SEARCH_URL.format(query=ticker, sfrom=sfrom, sto=sto, page=page)
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select(".searchnew .box-category-item")
        if not articles:
            break
        for art in articles:
            a = art.select_one("a")
            if a and a.get("href"):
                links.append(BASE_URL + a.get("href"))
        time.sleep(0.5)
    return links

# Hàm lấy nội dung bài báo

def get_article_content(url):
    try:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.select_one(".title, .main-title, h1").get_text(strip=True)
        content = " ".join([p.get_text(strip=True) for p in soup.select(".detail-content p, .main-content p")])
        date = soup.select_one(".pdate, .date, .time").get_text(strip=True)
        return title, content, date
    except Exception as e:
        return None, None, None

# Hàm crawl toàn bộ dữ liệu

def crawl_news():
    results = []
    for ticker in TICKERS:
        cur_date = START_DATE
        while cur_date < END_DATE:
            sfrom = cur_date.strftime("%d/%m/%Y")
            sto = (cur_date + timedelta(days=1)).strftime("%d/%m/%Y")
            links = get_article_links(ticker, sfrom, sto)
            for url in links:
                title, content, date = get_article_content(url)
                if title and content:
                    results.append({
                        "time": date,
                        "title": title,
                        "content": content,
                        "ticker": ticker,
                        "source": url
                    })
            cur_date += timedelta(days=1)
            time.sleep(1)
    return results

if __name__ == "__main__":
    data = crawl_news()
    with open("news_fulltext_2025.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["time", "title", "content", "ticker", "source"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"Đã lưu {len(data)} bài báo vào news_fulltext_2025.csv")
