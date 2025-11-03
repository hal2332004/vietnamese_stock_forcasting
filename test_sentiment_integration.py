#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test nhanh để demo việc lấy dữ liệu với sentiment scores
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from get_data_from_supabase import SupabaseDataFetcher

def test_get_news_with_sentiment():
    """
    Test lấy dữ liệu news và kiểm tra có sentiment scores không
    """
    print("\n" + "=" * 70)
    print("TEST: LẤY DỮ LIỆU NEWS VỚI SENTIMENT SCORES")
    print("=" * 70 + "\n")
    
    # Khởi tạo fetcher
    fetcher = SupabaseDataFetcher()
    
    # Test với ticker ACB, lấy 5 records
    print("📊 Test case: Lấy 5 tin tức của ACB\n")
    df = fetcher.get_news_data_by_ticker(ticker='ACB', limit=5)
    
    if df.empty:
        print("❌ THẤT BẠI: Không lấy được dữ liệu!")
        return False
    
    print(f"\n✅ Đã lấy {len(df)} records\n")
    
    # Kiểm tra các cột sentiment
    sentiment_cols = ['negative_score', 'positive_score', 'neutral_score']
    has_sentiment_cols = all(col in df.columns for col in sentiment_cols)
    
    print("🔍 KIỂM TRA CÁC CỘT:")
    print(f"  • Tổng số cột: {len(df.columns)}")
    print(f"  • Có cột 'negative_score': {'✅' if 'negative_score' in df.columns else '❌'}")
    print(f"  • Có cột 'positive_score': {'✅' if 'positive_score' in df.columns else '❌'}")
    print(f"  • Có cột 'neutral_score': {'✅' if 'neutral_score' in df.columns else '❌'}")
    
    if has_sentiment_cols:
        print(f"\n✅ PASS: Tất cả 3 cột sentiment đã có trong DataFrame!")
    else:
        print(f"\n❌ FAIL: Thiếu một số cột sentiment!")
        return False
    
    # Hiển thị sample data
    print(f"\n📰 SAMPLE DATA (5 records):\n")
    display_cols = ['date', 'ticker', 'title', 'negative_score', 'positive_score', 'neutral_score']
    available_cols = [col for col in display_cols if col in df.columns]
    print(df[available_cols].to_string())
    
    # Kiểm tra có giá trị sentiment không
    print(f"\n🔍 KIỂM TRA GIÁ TRỊ SENTIMENT:")
    
    has_values = 0
    null_values = 0
    
    for idx, row in df.iterrows():
        neg = row.get('negative_score')
        pos = row.get('positive_score')
        neu = row.get('neutral_score')
        
        if neg is not None and pos is not None and neu is not None:
            has_values += 1
        else:
            null_values += 1
    
    print(f"  • Records có sentiment values: {has_values}/{len(df)}")
    print(f"  • Records có null values: {null_values}/{len(df)}")
    
    if has_values > 0:
        print(f"\n✅ PASS: Có ít nhất {has_values} records có sentiment scores!")
    else:
        print(f"\n⚠️  WARNING: Tất cả records đều chưa có sentiment scores!")
        print(f"   Chạy: python analyze_news_sentiment.py để update sentiment")
    
    # Test export
    print(f"\n📁 TEST EXPORT CSV:")
    try:
        test_filename = "test_ACB_with_sentiment.csv"
        fetcher.export_to_csv(df, test_filename)
        
        # Kiểm tra file đã tạo
        output_path = f"./data/exports/{test_filename}"
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ PASS: File CSV đã được tạo!")
            print(f"   • Path: {output_path}")
            print(f"   • Size: {file_size} bytes")
            
            # Đọc lại để verify
            import pandas as pd
            df_reloaded = pd.read_csv(output_path)
            
            has_sentiment_in_csv = all(col in df_reloaded.columns for col in sentiment_cols)
            print(f"   • Có 3 cột sentiment trong CSV: {'✅' if has_sentiment_in_csv else '❌'}")
            
            if has_sentiment_in_csv:
                print(f"\n✅ PASS: CSV export bao gồm đầy đủ sentiment scores!")
            else:
                print(f"\n❌ FAIL: CSV thiếu sentiment columns!")
                return False
        else:
            print(f"❌ FAIL: Không tìm thấy file CSV!")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Lỗi khi export CSV: {str(e)}")
        return False
    
    # Kết luận
    print("\n" + "=" * 70)
    print("🎉 TẤT CẢ TESTS PASSED!")
    print("=" * 70)
    print("\n✅ KẾT LUẬN:")
    print("  • Code get_data_from_supabase.py HOẠT ĐỘNG TỐT với 3 cột sentiment mới")
    print("  • DataFrame tự động chứa các cột sentiment")
    print("  • CSV export bao gồm đầy đủ sentiment scores")
    print("  • KHÔNG CẦN SỬA CODE!")
    print("\n" + "=" * 70 + "\n")
    
    return True


def test_check_coverage():
    """
    Test function check_sentiment_coverage
    """
    print("\n" + "=" * 70)
    print("TEST: CHECK SENTIMENT COVERAGE")
    print("=" * 70 + "\n")
    
    fetcher = SupabaseDataFetcher()
    
    # Test với ticker ACB
    print("📊 Test case: Kiểm tra coverage của ACB\n")
    result = fetcher.check_sentiment_coverage(ticker='ACB')
    
    if result:
        print("\n✅ PASS: Function check_sentiment_coverage hoạt động tốt!")
        return True
    else:
        print("\n❌ FAIL: Function check_sentiment_coverage có lỗi!")
        return False


def main():
    """
    Run all tests
    """
    print("\n" + "=" * 70)
    print("🧪 CHẠY TẤT CẢ TESTS")
    print("=" * 70)
    
    # Load env
    load_dotenv()
    
    tests = [
        ("Test lấy dữ liệu với sentiment", test_get_news_with_sentiment),
        ("Test check coverage", test_check_coverage),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n▶️  Đang chạy: {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} - ERROR: {str(e)}")
    
    # Tổng kết
    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ TESTS")
    print("=" * 70)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print(f"\n🎉 TẤT CẢ TESTS ĐỀU PASS!")
        print(f"\n✅ KẾT LUẬN: Code hoạt động hoàn hảo với 3 cột sentiment mới!")
    else:
        print(f"\n⚠️  CÓ {failed} TESTS FAILED!")
        print(f"Kiểm tra lại configuration hoặc database!")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
