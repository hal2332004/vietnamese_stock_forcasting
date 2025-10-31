"""
TEST DATE PARSING
"""
import re
from datetime import datetime

def parse_date(date_str):
    """Parse date to ISO format - FIXED để xử lý format Việt Nam"""
    if not date_str:
        return ""
    
    # Xóa "Thứ hai, Thứ ba,..." và khoảng trắng thừa
    date_str = re.sub(r'Thứ\s+(hai|ba|tư|năm|sáu|bảy|CN),?\s*', '', date_str, flags=re.IGNORECASE)
    date_str = re.sub(r'\(GMT\+\d+\)', '', date_str)  # Xóa (GMT+7)
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    formats = [
        "%d/%m/%Y, %H:%M",      # 15/7/2014, 17:45
        "%d/%m/%Y %H:%M",       # 15/7/2014 17:45
        "%Y-%m-%d %H:%M:%S",    # 2015-01-01 10:30:00
        "%d/%m/%Y",             # 15/7/2014
        "%d-%m-%Y",             # 15-7-2014
        "%Y-%m-%d",             # 2015-01-01
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            continue
    
    # Nếu không parse được, thử extract năm bằng regex
    year_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if year_match:
        day, month, year = year_match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d 00:00:00")
        except:
            pass
    
    return ""  # Trả về rỗng nếu không parse được


# Test cases
test_dates = [
    "Thứ ba, 15/7/2014, 17:45 (GMT+7)",
    "Thứ sáu, 16/10/2020, 18:40 (GMT+7)",
    "Thứ tư, 7/7/2021, 09:30 (GMT+7)",
    "Thứ ba, 5/8/2025, 16:50 (GMT+7)",
    "15/7/2014, 17:45",
    "2024-01-15 10:30:00",
    "Invalid date string",
]

print("="*70)
print("DATE PARSING TEST")
print("="*70)

for date_str in test_dates:
    parsed = parse_date(date_str)
    year = parsed[:4] if parsed and len(parsed) >= 4 else "N/A"
    print(f"\nInput:  {date_str}")
    print(f"Output: {parsed}")
    print(f"Year:   {year}")
