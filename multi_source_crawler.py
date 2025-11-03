"""
MULTI-SOURCE NEWS CRAWLER
Crawl tin tức từ nhiều nguồn để đảm bảo đủ dữ liệu cho 5 tickers trong 10 năm
Sources: VnExpress, Dân Trí, CafeF
"""

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

# ============= CONFIGURATION =============
TICKERS = ["BID", "FPT"]
START_DATE = datetime(2015, 1, 1)  # Full range 2015-2025
END_DATE = datetime(2025, 10, 30)

MAX_WORKERS = 5
BATCH_SIZE = 100
MAX_RETRIES = 3
REQUEST_DELAY = 0.2

# Thread-safe
csv_lock = Lock()
seen_urls = set()

# ============= VNEXPRESS CRAWLER =============
class VnExpressCrawler:
    BASE_URL = "https://vnexpress.net"
    SEARCH_URL = "https://timkiem.vnexpress.net/?q={query}&date_from={date_from}&date_to={date_to}&media_type=all&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=50):
        """Crawl article links từ VnExpress theo ticker và năm - NHIỀU QUERIES"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        year_start = datetime(year, 1, 1)
        year_end = datetime(year, 12, 31) if year < END_DATE.year else END_DATE
        
        # Tên đầy đủ của các ngân hàng
        ticker_names = {
            "ACB": ["ACB", "Á Châu", "ngân hàng ACB", "Asia Commercial Bank"],
            "BID": ["BID", "BIDV", "Đầu tư và Phát triển", "ngân hàng BIDV"],
            "VCB": ["VCB", "Vietcombank", "ngân hàng Vietcombank", "Ngoại thương"],
            "MBB": ["MBB", "MB Bank", "ngân hàng MB", "Military Bank"],
            "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT", "cổ phiếu FPT"],
        }
        
        # Tạo queries TẬP TRUNG VÀO TÀI CHÍNH
        base_queries = ticker_names.get(ticker, [ticker])
        queries = []
        for name in base_queries:
            queries.extend([
                # Tài chính cụ thể
                f"{name} báo cáo tài chính",
                f"{name} kết quả kinh doanh",
                f"{name} lợi nhuận",
                f"{name} doanh thu",
                f"{name} báo cáo quý",
            ])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = VnExpressCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    date_from=year_start.strftime("%Y-%m-%d"),
                    date_to=year_end.strftime("%Y-%m-%d"),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.find_all('h3', class_='title-news')
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    for article in articles:
                        a_tag = article.find('a', href=True)
                        if a_tag:
                            href = a_tag.get('href', '')
                            if href.startswith('http'):
                                links.append(('vnexpress', href))
                            elif href.startswith('/'):
                                links.append(('vnexpress', VnExpressCrawler.BASE_URL + href))
                    
                    consecutive_empty = 0
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract title, content, date từ VnExpress article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.title-detail")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("article.fck_detail")
            if content_elem:
                paragraphs = content_elem.select("p.Normal")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("span.date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= DÂN TRÍ CRAWLER =============
class DanTriCrawler:
    BASE_URL = "https://dantri.com.vn"
    SEARCH_URL = "https://dantri.com.vn/tim-kiem.htm?q={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=50):
        """Crawl article links từ Dân Trí - NHIỀU QUERIES"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "Á Châu", "Asia Commercial Bank"],
            "BID": ["BID", "BIDV", "ngân hàng BIDV"],
            "VCB": ["VCB", "Vietcombank", "ngân hàng Vietcombank"],
            "MBB": ["MBB", "MB Bank", "ngân hàng MB"],
            "FPT": ["FPT", "FPT Corporation", "Tập đoàn FPT"],
        }
        
        base_queries = ticker_names.get(ticker, [ticker])
        queries = []
        for name in base_queries:
            queries.extend([
                f"{name} báo cáo tài chính",
                f"{name} kết quả kinh doanh",
                f"{name} lợi nhuận",
                f"{name} doanh thu",
                f"{name} báo cáo quý",
            ])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = DanTriCrawler.SEARCH_URL.format(query=query.replace(' ', '+'), page=page)
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # Dân Trí search results
                    articles = soup.select("h3.article-title a, h4.article-title a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Check if article is from target year
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('dantri', href))
                            elif href.startswith('/'):
                                links.append(('dantri', DanTriCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Dân Trí article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.title-page, h1.article-title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("div.singular-content, div.article-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("time.author-time, span.author-time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= THANHNIEN CRAWLER =============
class ThanhNienCrawler:
    BASE_URL = "https://thanhnien.vn"
    SEARCH_URL = "https://thanhnien.vn/tim-kiem/?keywords={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ ThanhNien.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "ngân hàng ACB"],
            "BID": ["BIDV", "ngân hàng BIDV"],
            "VCB": ["Vietcombank", "ngân hàng Vietcombank"],
            "MBB": ["MB Bank", "ngân hàng MB"],
            "FPT": ["FPT", "FPT Corporation"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = ThanhNienCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # ThanhNien search results
                    articles = soup.select("h2.title-news a, h3.title-news a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        # Check if from target year
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('thanhnien', href))
                            elif href.startswith('/'):
                                links.append(('thanhnien', ThanhNienCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ ThanhNien article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Title
            title = ""
            title_elem = soup.select_one("h1.detail-title, h1.title-detail")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Content
            content = ""
            content_elem = soup.select_one("div.detail-content, div#contentbody")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            # Date
            date_str = ""
            date_elem = soup.select_one("div.detail-time, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= CAFEF CRAWLER =============
class CafeFCrawler:
    BASE_URL = "https://cafef.vn"
    SEARCH_URL = "https://cafef.vn/tim-kiem.chn?keywords={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=20):
        """Crawl từ CafeF - FINANCIAL FOCUSED"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # Financial-focused queries
        queries = [
            f"{ticker} báo cáo tài chính",
            f"{ticker} kết quả kinh doanh",
            f"{ticker} lợi nhuận",
            ticker  # Fallback to ticker only
        ]
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 3:
                    break
                
                url = CafeFCrawler.SEARCH_URL.format(query=query, page=page)
            
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    consecutive_empty += 1
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                all_links = soup.find_all('a', href=True)
                
                found_articles = False
                for a in all_links:
                    href = a.get('href', '')
                    text = a.get_text(strip=True).lower()
                    
                    # Check if link contains news article pattern and mentions ticker
                    if '.chn' in href and (ticker.lower() in text or ticker.lower() in href.lower()):
                        # Check if from correct year
                        if str(year) in href or f'{year % 100:02d}' in href:
                            found_articles = True
                            if not href.startswith('http'):
                                href = CafeFCrawler.BASE_URL + href
                            links.append(('cafef', href))
                
                if not found_articles:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                consecutive_empty += 1
                time.sleep(0.5)
        
        return links

# ============= VIETSTOCK CRAWLER =============
class VietstockCrawler:
    BASE_URL = "https://finance.vietstock.vn"
    SEARCH_URL = "https://finance.vietstock.vn/tim-kiem?keyword={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ Vietstock.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "Á Châu"],
            "BID": ["BID", "BIDV"],
            "VCB": ["VCB", "Vietcombank"],
            "MBB": ["MBB", "MB Bank"],
            "FPT": ["FPT", "FPT Corporation"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = VietstockCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2.news-title a, div.news-item a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('vietstock', href))
                            elif href.startswith('/'):
                                links.append(('vietstock', VietstockCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Vietstock article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.news-title, h1.detail-title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.detail-content, div.news-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.time, div.date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= STOCKBIZ CRAWLER =============
class StockbizCrawler:
    BASE_URL = "https://stockbiz.vn"
    SEARCH_URL = "https://stockbiz.vn/tim-kiem.html?q={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ Stockbiz.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "ngân hàng ACB"],
            "BID": ["BIDV", "ngân hàng BIDV"],
            "VCB": ["Vietcombank"],
            "MBB": ["MB Bank"],
            "FPT": ["FPT"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = StockbizCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2 a, div.article-item a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('stockbiz', href))
                            elif href.startswith('/'):
                                links.append(('stockbiz', StockbizCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Stockbiz article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.content, div.article-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= NDH CRAWLER =============
class NDHCrawler:
    BASE_URL = "https://ndh.vn"
    SEARCH_URL = "https://ndh.vn/tim-kiem?key={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ ndh.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        queries = [ticker]
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = NDHCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2 a, div.news-item a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('ndh', href))
                            elif href.startswith('/'):
                                links.append(('ndh', NDHCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ NDH article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.content, div.detail-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= TINNHANHCHUNGKHOAN CRAWLER =============
class TinnhanhchungkhoanCrawler:
    BASE_URL = "https://tinnhanhchungkhoan.vn"
    SEARCH_URL = "https://tinnhanhchungkhoan.vn/search?q={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ Tinnhanhchungkhoan.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        queries = [ticker]
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = TinnhanhchungkhoanCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2.title a, div.article a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('tinnhanhchungkhoan', href))
                            elif href.startswith('/'):
                                links.append(('tinnhanhchungkhoan', TinnhanhchungkhoanCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Tinnhanhchungkhoan article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.content, div.detail-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= BAODAUTU CRAWLER =============
class BaodautuCrawler:
    BASE_URL = "https://baodautu.vn"
    SEARCH_URL = "https://baodautu.vn/tim-kiem.html?q={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ baodautu.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        ticker_names = {
            "ACB": ["ACB", "Á Châu"],
            "BID": ["BIDV"],
            "VCB": ["Vietcombank"],
            "MBB": ["MB Bank"],
            "FPT": ["FPT"],
        }
        
        queries = ticker_names.get(ticker, [ticker])
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = BaodautuCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2.title a, div.news-item a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('baodautu', href))
                            elif href.startswith('/'):
                                links.append(('baodautu', BaodautuCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ Baodautu article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.content, div.detail-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= VIETFINANCE CRAWLER =============
class VietFinanceCrawler:
    BASE_URL = "https://vietfinance.vn"
    SEARCH_URL = "https://vietfinance.vn/tim-kiem?keyword={query}&page={page}"
    
    @staticmethod
    def get_article_links(ticker, year, max_pages=30):
        """Crawl từ VietFinance.vn"""
        links = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        queries = [ticker]
        
        for query in queries:
            consecutive_empty = 0
            for page in range(1, max_pages + 1):
                if consecutive_empty >= 2:
                    break
                
                url = VietFinanceCrawler.SEARCH_URL.format(
                    query=query.replace(' ', '+'),
                    page=page
                )
                
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        consecutive_empty += 1
                        continue
                    
                    soup = BeautifulSoup(resp.text, "html.parser")
                    articles = soup.select("h3 a, h2 a, div.article a")
                    
                    if not articles:
                        consecutive_empty += 1
                        continue
                    
                    found_year_match = False
                    for article in articles:
                        href = article.get('href', '')
                        
                        if str(year) in href or f"/{year % 100:02d}/" in href:
                            found_year_match = True
                            if href.startswith('http'):
                                links.append(('vietfinance', href))
                            elif href.startswith('/'):
                                links.append(('vietfinance', VietFinanceCrawler.BASE_URL + href))
                    
                    if not found_year_match:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    consecutive_empty += 1
                    time.sleep(0.5)
        
        return links
    
    @staticmethod
    def extract_content(url):
        """Extract content từ VietFinance article"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None, None, None
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            title = ""
            title_elem = soup.select_one("h1.title, h1")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            content = ""
            content_elem = soup.select_one("div.content, div.detail-content")
            if content_elem:
                paragraphs = content_elem.select("p")
                if paragraphs:
                    content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
            
            date_str = ""
            date_elem = soup.select_one("span.date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
            
            return title, content, date_str
            
        except Exception as e:
            return None, None, None

# ============= MAIN CRAWLER =============
def parse_date(date_str):
    """Parse date to ISO format"""
    if not date_str:
        return ""
    
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d/%m/%Y, %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    return date_str

# ============= FINANCIAL KEYWORDS FILTER =============
FINANCIAL_KEYWORDS = {
    "common": [
        # Báo cáo tài chính
        "báo cáo tài chính", "kết quả kinh doanh", "báo cáo quý", "báo cáo năm",
        "financial report", "quarterly", "annual report", "Q1", "Q2", "Q3", "Q4",
        
        # Lợi nhuận & Doanh thu
        "lợi nhuận", "doanh thu", "tăng trưởng", "EPS", "ROE", "ROA",
        "profit", "revenue", "earnings", "growth", "tỷ đồng", "nghìn tỷ",
        
        # Vốn & Cổ phiếu
        "vốn hóa", "cổ phiếu", "cổ đông", "phát hành", "chia cổ tức", "giá cổ phiếu",
        "market cap", "shares", "shareholder", "dividend", "stock price",
        
        # Giao dịch lớn
        "mua lại", "sáp nhập", "M&A", "hợp đồng", "thương vụ", "đầu tư",
        "acquisition", "merger", "deal", "contract", "investment",
        
        # Phân tích & Dự báo
        "định giá", "mục tiêu", "khuyến nghị", "triển vọng", "dự báo", "phân tích",
        "valuation", "target", "recommendation", "outlook", "forecast", "analysis",
        
        # Thị trường & Vĩ mô
        "FTSE", "nâng hạng", "upgrade", "downgrade", "rating",
        "vốn ngoại", "foreign", "institutional", "VN-Index", "HOSE", "HNX",
    ],
    
    "BID": [
        # Ngân hàng cụ thể
        "tín dụng", "nợ xấu", "NPL", "huy động", "cho vay", "tiền gửi",
        "credit", "bad debt", "loan", "deposit", "lending",
        
        # Chỉ số ngân hàng
        "tỷ lệ an toàn vốn", "CAR", "Basel", "NIM", "lãi suất", "interest rate",
        "dự phòng", "provision", "CIR", "chi phí hoạt động",
        
        # Hoạt động ngân hàng
        "tổng tài sản", "vốn chủ sở hữu", "lãi thuần", "thu nhập lãi",
    ],
    
    "FPT": [
        # Công nghệ & Dịch vụ
        "hợp đồng", "chuyển đổi số", "digital transformation",
        "AI", "cloud", "outsourcing", "phần mềm", "software",
        
        # Các công ty con
        "FPT Telecom", "FPT Software", "FPT IS", "FPT Retail", "Long Châu",
        "viễn thông", "telecom", "bán lẻ", "retail",
        
        # Mở rộng
        "xuất khẩu", "export", "overseas", "quốc tế", "international",
        "Nhật Bản", "Japan", "ASEAN", "Singapore", "Mỹ",
        
        # Dịch vụ
        "dịch vụ số", "công nghệ", "technology", "IT services",
    ]
}

EXCLUDE_KEYWORDS = [
    # Tin hành chính nhỏ không quan trọng
    "khai trương", "chi nhánh mới", "văn phòng mới", "thay đổi địa chỉ",
    "opening ceremony", "new branch", "new office",
    
    # Tin sự kiện xã hội
    "từ thiện", "charity", "CSR", "trách nhiệm xã hội",
    "tuyển dụng", "recruitment", "hiring", "tuyển sinh",
    
    # Tin quảng cáo marketing
    "khuyến mãi", "promotion", "sale", "giảm giá", "ưu đãi",
    "ra mắt sản phẩm", "new product launch" # trừ khi là sản phẩm tài chính lớn
]

def check_financial_relevance(title, content, ticker):
    """
    Kiểm tra xem tin có liên quan đến TÀI CHÍNH không
    Returns: (is_relevant, score, matched_keywords)
    """
    text = (title + " " + content[:1500]).upper()  # Chỉ check 1500 ký tự đầu
    
    # 1. Check exclude keywords trước (loại bỏ tin không quan trọng)
    for exclude_word in EXCLUDE_KEYWORDS:
        if exclude_word.upper() in text:
            return False, 0, []
    
    # 2. Count matched financial keywords
    matched_keywords = []
    score = 0
    
    # Common financial keywords (trọng số 1)
    for keyword in FINANCIAL_KEYWORDS["common"]:
        if keyword.upper() in text:
            matched_keywords.append(keyword)
            score += 1
    
    # Ticker-specific keywords (trọng số 2)
    if ticker in FINANCIAL_KEYWORDS:
        for keyword in FINANCIAL_KEYWORDS[ticker]:
            if keyword.upper() in text:
                matched_keywords.append(keyword)
                score += 2  # Keywords đặc thù có trọng số cao hơn
    
    # 3. Bonus nếu có số liệu cụ thể
    if any(pattern in text for pattern in ["TỶ ĐỒNG", "NGHÌN TỶ", "TRIỆU USD", "MILLION", "BILLION"]):
        score += 1
    
    # 4. Check ticker mention
    if ticker.upper() not in text:
        score = int(score * 0.3)  # Giảm mạnh score nếu không nhắc ticker
    
    # 5. Threshold: cần ít nhất 2 điểm
    is_relevant = score >= 2
    
    return is_relevant, score, matched_keywords[:5]  # Top 5 keywords

def detect_ticker_in_content(title, content, ticker):
    """Check if ticker is mentioned in content AND financially relevant"""
    # Check basic mention
    text = (title + " " + content).upper()
    
    patterns = [
        ticker,
        f" {ticker} ",
        f"({ticker})",
        f"{ticker},",
        f"{ticker}.",
    ]
    
    has_ticker = any(pattern in text for pattern in patterns)
    
    if not has_ticker:
        return False
    
    # Check financial relevance
    is_relevant, score, keywords = check_financial_relevance(title, content, ticker)
    
    return is_relevant

def process_article(source, url, ticker):
    """Process single article from any source"""
    if url in seen_urls:
        return None
    
    seen_urls.add(url)
    
    # Extract content based on source
    if source == 'vnexpress':
        title, content, date_str = VnExpressCrawler.extract_content(url)
    elif source == 'dantri':
        title, content, date_str = DanTriCrawler.extract_content(url)
    elif source == 'thanhnien':
        title, content, date_str = ThanhNienCrawler.extract_content(url)
    elif source == 'cafef':
        title, content, date_str = extract_cafef_content(url)
    elif source == 'vietstock':
        title, content, date_str = VietstockCrawler.extract_content(url)
    elif source == 'stockbiz':
        title, content, date_str = StockbizCrawler.extract_content(url)
    elif source == 'ndh':
        title, content, date_str = NDHCrawler.extract_content(url)
    elif source == 'tinnhanhchungkhoan':
        title, content, date_str = TinnhanhchungkhoanCrawler.extract_content(url)
    elif source == 'baodautu':
        title, content, date_str = BaodautuCrawler.extract_content(url)
    elif source == 'vietfinance':
        title, content, date_str = VietFinanceCrawler.extract_content(url)
    else:
        return None
    
    # Validate
    if not content or len(content) < 100:
        return None
    
    if not detect_ticker_in_content(title or "", content, ticker):
        return None
    
    # Parse date
    parsed_date = parse_date(date_str)
    
    try:
        if parsed_date and len(parsed_date) >= 10:
            if ' ' in parsed_date:
                date_part, time_part = parsed_date.split(' ', 1)
            else:
                date_part = parsed_date[:10]
                time_part = ""
        else:
            date_part = parsed_date
            time_part = ""
    except:
        date_part = parsed_date
        time_part = ""
    
    if not title:
        title = content[:50] + "..."
    
    print(f"[INFO] ✅ {source.upper()}: {ticker} | {title[:50]}...", file=sys.stderr)
    
    return {
        "date": date_part,
        "time": time_part,
        "title": title,
        "content": content,
        "ticker": ticker,
        "source": f"{source}:{url}"
    }

def extract_cafef_content(url):
    """Extract content from CafeF (backup source)"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None, None, None
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title = ""
        title_elem = soup.select_one(".title-detail, h1")
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        content = ""
        content_elem = soup.select_one(".detail-content, .main-content")
        if content_elem:
            paragraphs = content_elem.select("p")
            if paragraphs:
                content = " ".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])
        
        date_str = ""
        date_elem = soup.select_one(".date, time")
        if date_elem:
            date_str = date_elem.get_text(strip=True)
        
        return title, content, date_str
    except:
        return None, None, None

def save_batch_to_csv(batch, output_file, write_header=False):
    """Save batch to CSV (thread-safe) - SINGLE FILE"""
    with csv_lock:
        # Check if file exists to determine if header needed
        file_exists = os.path.exists(output_file)
        
        mode = 'a'
        with open(output_file, mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "time", "title", "content", "ticker", "source"])
            if not file_exists or write_header:
                writer.writeheader()
            for row in batch:
                writer.writerow(row)

def crawl_multi_source(output_file):
    """Main crawler - crawl từ nhiều nguồn - SAVE TO SINGLE FILE"""
    batch = []
    
    # Remove old file if exists
    if os.path.exists(output_file):
        os.remove(output_file)
    
    total_records = 0
    ticker_year_stats = {}
    
    print("\n" + "="*70, file=sys.stderr)
    print("🌐 MULTI-SOURCE NEWS CRAWLER", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"[INFO] Sources: VnExpress (80 pages), CafeF (50 pages)", file=sys.stderr)
    print(f"[INFO] Note: Only tested working sources included", file=sys.stderr)
    print(f"[INFO] Period: {START_DATE.year}-{END_DATE.year}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    print(f"[INFO] Target: 250+ articles/ticker/year", file=sys.stderr)
    print(f"[INFO] Output: Single CSV file → {output_file}", file=sys.stderr)
    
    # Crawl theo từng NĂM và TICKER
    for year in range(START_DATE.year, END_DATE.year + 1):
        print(f"\n{'#'*70}", file=sys.stderr)
        print(f"[YEAR] 📅 {year}", file=sys.stderr)
        print(f"{'#'*70}", file=sys.stderr)
        
        for ticker in TICKERS:
            print(f"\n[{year}] 💼 Ticker: {ticker}", file=sys.stderr)
            
            # Collect links from all sources
            all_links = []
            
            # VnExpress (80 pages - primary source)
            print(f"  📰 Crawling VnExpress...", file=sys.stderr)
            vnexpress_links = VnExpressCrawler.get_article_links(ticker, year, max_pages=80)
            all_links.extend(vnexpress_links)
            print(f"    ✅ Found {len(vnexpress_links)} links", file=sys.stderr)
            
            # CafeF (50 pages - secondary source)
            print(f"  📰 Crawling CafeF...", file=sys.stderr)
            cafef_links = CafeFCrawler.get_article_links(ticker, year, max_pages=50)
            all_links.extend(cafef_links)
            print(f"    ✅ Found {len(cafef_links)} links", file=sys.stderr)
            
            if not all_links:
                print(f"  ⚠️  No articles found for {ticker} in {year}", file=sys.stderr)
                continue
            
            print(f"  🔄 Processing {len(all_links)} articles...", file=sys.stderr)
            
            # Process articles
            ticker_year_count = 0
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(process_article, source, url, ticker): (source, url) for source, url in all_links}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            batch.append(result)
                            total_records += 1
                            ticker_year_count += 1
                            
                            if len(batch) >= BATCH_SIZE:
                                save_batch_to_csv(batch, output_file)
                                print(f"[SAVE] ✅ Saved {len(batch)} records. Total: {total_records}", file=sys.stderr)
                                batch = []
                    except Exception as e:
                        pass
            
            ticker_year_stats[f"{year}_{ticker}"] = ticker_year_count
            print(f"  ✅ {ticker} {year}: {ticker_year_count} articles", file=sys.stderr)
    
    # Save final batch
    if batch:
        save_batch_to_csv(batch, output_file)
        print(f"\n[SAVE] ✅ Saved final batch of {len(batch)} records", file=sys.stderr)
    
    # Print summary
    print("\n" + "="*70, file=sys.stderr)
    print("📊 SUMMARY BY YEAR AND TICKER:", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    for year in range(START_DATE.year, END_DATE.year + 1):
        print(f"\n{year}:", file=sys.stderr)
        for ticker in TICKERS:
            count = ticker_year_stats.get(f"{year}_{ticker}", 0)
            print(f"  {ticker}: {count:>4} articles", file=sys.stderr)
    
    return total_records

if __name__ == "__main__":
    print("="*70)
    print("🌐 MULTI-SOURCE VIETNAMESE STOCK NEWS CRAWLER")
    print("="*70)
    print(f"[INFO] Date range: {START_DATE.date()} to {END_DATE.date()}", file=sys.stderr)
    print(f"[INFO] Tickers: {', '.join(TICKERS)}", file=sys.stderr)
    
    # Create data folder if not exists
    data_folder = "data"
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    
    output_file = os.path.join(data_folder, f"news_{START_DATE.year}_{END_DATE.year}.csv")
    
    # Check if file exists
    if os.path.exists(output_file):
        print(f"\n[WARNING] Found existing file: {output_file}")
        choice = input("Overwrite? (y/n): ")
        if choice.lower() != 'y':
            print("[INFO] Crawl cancelled")
            sys.exit(0)
    
    start_time = time.time()
    print(f"\n[START] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        total = crawl_multi_source(output_file)
        
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print(f"[SUCCESS] ✅ Saved {total} articles")
        print(f"[TIME] ⏱️  Duration: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
        print(f"[SPEED] 🚄 Speed: {total/(elapsed/60):.1f} articles/minute")
        print("="*70)
        
        # Final statistics - Read from single file
        print("\n📊 Final Statistics:")
        if os.path.exists(output_file):
            ticker_counts = {ticker: 0 for ticker in TICKERS}
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get('ticker', '')
                    if ticker in ticker_counts:
                        ticker_counts[ticker] += 1
            
            total_articles = sum(ticker_counts.values())
            print(f"  Total articles: {total_articles}")
            for ticker in TICKERS:
                print(f"  {ticker}: {ticker_counts[ticker]:>5} articles")
            print(f"  File: {output_file}")
        
    except KeyboardInterrupt:
        print("\n[INFO] ⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] ❌ {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
