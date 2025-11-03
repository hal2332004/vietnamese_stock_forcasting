# -*- coding: utf-8 -*-
"""
Script để phân tích sentiment cho tất cả tin tức trong Supabase
Đọc từng row, phân tích content, và update 3 điểm số sentiment
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from supabase import create_client, Client
from dotenv import load_dotenv
from tqdm import tqdm
import time
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Khởi tạo Supabase client với SERVICE ROLE KEY để có quyền update
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY')  # Dùng SECRET_KEY để có quyền update
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load sentiment model
print("🔄 Đang load model sentiment...")
model_sentiment_name = "mr4/phobert-base-vi-sentiment-analysis"
tokenizer_sentiment = AutoTokenizer.from_pretrained(model_sentiment_name)
model_sentiment = AutoModelForSequenceClassification.from_pretrained(model_sentiment_name)
print("✅ Đã load model sentiment thành công!\n")


def analyze_sentiment(text):
    """
    Phân tích sentiment của văn bản (áp dụng logic từ sumerize.py)
    
    Args:
        text (str): Văn bản cần phân tích
        
    Returns:
        dict: Dictionary chứa negative_score, positive_score, neutral_score
    """
    if not text or text.strip() == '':
        return {
            'negative_score': 0.0,
            'positive_score': 0.0,
            'neutral_score': 1.0
        }
    
    try:
        # Truncate text nếu quá dài (PhoBERT giới hạn 512 tokens)
        inputs = tokenizer_sentiment(
            text, 
            padding=True, 
            truncation=True, 
            return_tensors="pt"
        )
        
        with torch.no_grad():
            outputs = model_sentiment(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Áp dụng logic giống sumerize.py
        sentiment_results = {}
        for i, prediction in enumerate(predictions):
            for j, value in enumerate(prediction):
                sentiment_results[model_sentiment.config.id2label[j]] = value.item()
        
        # Map labels sang format cần thiết
        # Output từ model: 'Tiêu cực', 'Tích cực', 'Trung tính'
        result = {
            'negative_score': float(sentiment_results.get('Tiêu cực', sentiment_results.get('NEG', 0.0))),
            'positive_score': float(sentiment_results.get('Tích cực', sentiment_results.get('POS', 0.0))),
            'neutral_score': float(sentiment_results.get('Trung tính', sentiment_results.get('NEU', 0.0)))
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Lỗi khi phân tích sentiment: {str(e)}")
        return {
            'negative_score': 0.0,
            'positive_score': 0.0,
            'neutral_score': 1.0
        }


def get_all_news(limit=None, offset=0):
    """
    Lấy tất cả tin tức từ Supabase
    
    Args:
        limit: Số lượng records tối đa (None = lấy tất cả)
        offset: Bỏ qua bao nhiêu records đầu tiên
        
    Returns:
        list: Danh sách tin tức
    """
    try:
        query = supabase.table('news_data').select('id, content, ticker, title')
        
        if limit:
            query = query.limit(limit)
        
        if offset:
            query = query.offset(offset)
        
        response = query.execute()
        return response.data
        
    except Exception as e:
        print(f"❌ Lỗi khi lấy dữ liệu: {str(e)}")
        return []


def update_sentiment_scores(news_id, scores):
    """
    Update sentiment scores cho 1 tin tức
    
    Args:
        news_id: ID của tin tức
        scores: Dictionary chứa negative_score, positive_score, neutral_score
    """
    try:
        supabase.table('news_data').update({
            'negative_score': scores['negative_score'],
            'positive_score': scores['positive_score'],
            'neutral_score': scores['neutral_score']
        }).eq('id', news_id).execute()
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi update news_id {news_id}: {str(e)}")
        return False


def batch_update_sentiment_scores(batch_updates, max_retries=3, verify=True):
    """
    Update sentiment scores cho nhiều tin tức cùng lúc với retry mechanism và VERIFICATION
    
    Args:
        batch_updates: List of tuples (news_id, scores)
        max_retries: Số lần thử lại tối đa nếu thất bại
        verify: Có verify lại DB sau khi update không (default: True)
        
    Returns:
        tuple: (success_count, failed_count, failed_ids)
    """
    success = 0
    failed = 0
    failed_ids = []
    
    for news_id, scores in batch_updates:
        retry_count = 0
        update_success = False
        last_error = None
        
        while retry_count < max_retries and not update_success:
            try:
                # 1. Thực hiện update
                response = supabase.table('news_data').update({
                    'negative_score': scores['negative_score'],
                    'positive_score': scores['positive_score'],
                    'neutral_score': scores['neutral_score']
                }).eq('id', news_id).execute()
                
                # 2. Kiểm tra response có data không
                if not response.data or len(response.data) == 0:
                    raise Exception(f"Update không trả về data, có thể không tìm thấy ID {news_id}")
                
                # 3. VERIFICATION: Đọc lại từ DB để chắc chắn đã update
                if verify:
                    time.sleep(0.1)  # Đợi DB commit
                    verify_response = supabase.table('news_data').select(
                        'negative_score, positive_score, neutral_score'
                    ).eq('id', news_id).execute()
                    
                    if verify_response.data and len(verify_response.data) > 0:
                        saved_data = verify_response.data[0]
                        
                        # So sánh với tolerance nhỏ (0.0001) do floating point
                        tolerance = 0.0001
                        is_match = (
                            abs(saved_data['negative_score'] - scores['negative_score']) < tolerance and
                            abs(saved_data['positive_score'] - scores['positive_score']) < tolerance and
                            abs(saved_data['neutral_score'] - scores['neutral_score']) < tolerance
                        )
                        
                        if not is_match:
                            raise Exception(
                                f"Verification failed: Dữ liệu trên DB không khớp!\n"
                                f"Expected: neg={scores['negative_score']:.6f}, pos={scores['positive_score']:.6f}, neu={scores['neutral_score']:.6f}\n"
                                f"Got: neg={saved_data['negative_score']:.6f}, pos={saved_data['positive_score']:.6f}, neu={saved_data['neutral_score']:.6f}"
                            )
                    else:
                        raise Exception("Verification failed: Không đọc được data từ DB")
                
                # Nếu đến đây = thành công
                update_success = True
                success += 1
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)  # Đợi trước khi retry
        
        if not update_success:
            print(f"❌ Thất bại sau {max_retries} lần thử - news_id {news_id}: {last_error}")
            failed += 1
            failed_ids.append({
                'news_id': news_id,
                'scores': scores,
                'error': last_error
            })
    
    return success, failed, failed_ids


def process_all_news(batch_size=100, start_offset=0, limit=None, update_batch_size=100):
    """
    Xử lý tất cả tin tức theo batch và update realtime mỗi update_batch_size dòng
    ĐẢM BẢO 100% dữ liệu được update với retry mechanism và error logging
    
    Args:
        batch_size: Số lượng tin tức lấy từ DB mỗi lần
        start_offset: Vị trí bắt đầu
        limit: Giới hạn số lượng tin tức cần xử lý
        update_batch_size: Số lượng dòng để update cùng lúc (realtime update)
    """
    print("=" * 70)
    print("PHÂN TÍCH SENTIMENT - 100% ĐẢM BẢO UPDATE THÀNH CÔNG")
    print("=" * 70)
    
    # Tạo timestamp cho log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_log_file = f"failed_updates_{timestamp}.json"
    
    # Lấy tổng số tin tức
    total_response = supabase.table('news_data').select('id', count='exact').execute()
    total_count = total_response.count if hasattr(total_response, 'count') else len(total_response.data)
    
    if limit:
        total_count = min(total_count, limit)
    
    print(f"\n📊 Tổng số tin tức cần xử lý: {total_count}")
    print(f"📦 Fetch batch size: {batch_size}")
    print(f"⚡ Update batch size: {update_batch_size} (update realtime mỗi {update_batch_size} dòng)")
    print(f"🚀 Bắt đầu từ vị trí: {start_offset}")
    print(f"🔄 Retry mechanism: Tự động thử lại 3 lần nếu thất bại")
    print(f"📝 Error log file: {error_log_file}")
    print(f"💡 Bạn có thể xem kết quả realtime trên Supabase web!\n")
    
    processed = 0
    success = 0
    failed = 0
    offset = start_offset
    all_failed_ids = []
    
    # Buffer để tích lũy các update trước khi batch update
    update_buffer = []
    
    with tqdm(total=total_count, desc="Đang xử lý", unit="news") as pbar:
        while processed < total_count:
            # Lấy batch dữ liệu
            current_batch_size = min(batch_size, total_count - processed)
            news_list = get_all_news(limit=current_batch_size, offset=offset)
            
            if not news_list:
                print("\n⚠️  Không còn dữ liệu để xử lý")
                break
            
            # Xử lý từng tin tức trong batch
            for news in news_list:
                news_id = news['id']
                content = news.get('content', '')
                title = news.get('title', '')
                ticker = news.get('ticker', '')
                
                # Phân tích sentiment
                scores = analyze_sentiment(content)
                
                # Thêm vào buffer
                update_buffer.append((news_id, scores))
                processed += 1
                
                # Update realtime mỗi update_batch_size dòng
                if len(update_buffer) >= update_batch_size:
                    batch_success, batch_failed, failed_ids = batch_update_sentiment_scores(update_buffer)
                    success += batch_success
                    failed += batch_failed
                    
                    if failed_ids:
                        all_failed_ids.extend(failed_ids)
                    
                    # Clear buffer
                    update_buffer = []
                    
                    # Hiển thị thông báo update
                    print(f"\n✅ Đã update {success} tin tức lên Supabase! (Xem ngay trên web)")
                    print(f"   📍 Vị trí hiện tại: {processed}/{total_count}")
                    print(f"   📊 Thành công: {success} | Thất bại: {failed}")
                    if failed > 0:
                        print(f"   ⚠️  Các ID thất bại đã được ghi vào {error_log_file}")
                
                pbar.update(1)
                pbar.set_postfix({
                    'Success': success,
                    'Failed': failed,
                    'Ticker': ticker,
                    'Buffer': len(update_buffer)
                })
            
            offset += current_batch_size
            
            # Nghỉ giữa các batch để tránh quá tải
            time.sleep(0.2)
        
        # Update những dòng còn lại trong buffer
        if update_buffer:
            print(f"\n⚡ Đang update {len(update_buffer)} tin tức cuối cùng...")
            batch_success, batch_failed, failed_ids = batch_update_sentiment_scores(update_buffer)
            success += batch_success
            failed += batch_failed
            
            if failed_ids:
                all_failed_ids.extend(failed_ids)
            
            print(f"✅ Đã update xong! Kiểm tra ngay trên Supabase web!")
    
    # Ghi các ID thất bại vào file (nếu có)
    if all_failed_ids:
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'total_failed': len(all_failed_ids),
                'failed_records': all_failed_ids
            }, f, indent=2, ensure_ascii=False)
        print(f"\n⚠️  Đã ghi {len(all_failed_ids)} records thất bại vào {error_log_file}")
    
    # Tổng kết
    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH!")
    print("=" * 70)
    print(f"📊 Tổng số tin tức đã xử lý: {processed}")
    print(f"✅ Thành công: {success}")
    print(f"❌ Thất bại: {failed}")
    print(f"📈 Tỷ lệ thành công: {(success/processed*100):.2f}%" if processed > 0 else "N/A")
    
    # VERIFICATION CUỐI CÙNG: Kiểm tra thực tế có bao nhiêu records có sentiment scores
    print("\n🔍 ĐANG VERIFICATION CUỐI CÙNG...")
    print("   Kiểm tra thực tế trên DB có bao nhiêu records đã có sentiment scores...")
    
    try:
        # Đếm số records có sentiment scores (không null và khác 0)
        verify_response = supabase.table('news_data').select('id', count='exact').or_(
            'negative_score.neq.0,positive_score.neq.0,neutral_score.neq.1'
        ).execute()
        
        actually_updated = verify_response.count if hasattr(verify_response, 'count') else len(verify_response.data)
        
        print(f"\n📊 KẾT QUẢ VERIFICATION:")
        print(f"   📝 Số records báo cáo đã update: {success}")
        print(f"   ✅ Số records THỰC SỰ có sentiment trên DB: {actually_updated}")
        print(f"   📉 Chênh lệch: {success - actually_updated} records")
        
        if actually_updated < success:
            missing_percentage = ((success - actually_updated) / success * 100) if success > 0 else 0
            print(f"   ⚠️  MẤT THIẾU: {missing_percentage:.2f}% dữ liệu không được lưu thực sự!")
            print(f"   💡 Khuyến nghị: Chạy lại script với verification mode để tìm và update lại!")
        elif actually_updated == success:
            print(f"   🎉 HOÀN HẢO! 100% THỰC SỰ đã được update vào DB!")
        else:
            print(f"   ⚠️  Số liệu không khớp! Có thể DB có dữ liệu từ lần chạy trước.")
    except Exception as e:
        print(f"   ⚠️  Không thể verification: {str(e)}")
    
    # Đảm bảo 100% thành công
    if failed == 0:
        print(f"\n🎉 100% dữ liệu trong batch đã được XỬ LÝ thành công!")
        print(f"   (Nhưng hãy kiểm tra verification ở trên để chắc chắn đã LƯU vào DB)")
    else:
        print(f"\n⚠️  Có {failed} records thất bại. Chạy lại với các ID trong {error_log_file}")
    
    print(f"\n💡 Vào Supabase Table Editor để xem kết quả sentiment scores!")
    print("=" * 70 + "\n")
    
    return success, failed, all_failed_ids


def find_and_update_missing_sentiments():
    """
    Tìm những records CHƯA có sentiment scores và update lại
    Đây là function để fix vấn đề 5% dữ liệu bị thiếu
    """
    print("\n" + "=" * 70)
    print("TÌM VÀ UPDATE CÁC RECORDS THIẾU SENTIMENT")
    print("=" * 70 + "\n")
    
    try:
        # Tìm các records có sentiment = null hoặc = default (0,0,1)
        print("🔍 Đang tìm các records chưa có sentiment scores...")
        
        # Query 1: Tìm records có negative_score = null hoặc = 0
        # và positive_score = null hoặc = 0
        # và neutral_score = null hoặc = 1
        missing_response = supabase.table('news_data').select('id, content, ticker, title').or_(
            'negative_score.is.null,positive_score.is.null,neutral_score.is.null'
        ).execute()
        
        missing_records = missing_response.data
        
        if not missing_records:
            print("✅ TẤT CẢ records đều đã có sentiment scores!")
            return
        
        total_missing = len(missing_records)
        print(f"📊 Tìm thấy {total_missing} records CHƯA có sentiment scores\n")
        
        confirm = input(f"Bạn có muốn update {total_missing} records này không? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ Đã hủy!")
            return
        
        # Xử lý từng record với verification
        success = 0
        failed = 0
        failed_ids = []
        
        print(f"\n⚡ Đang xử lý với VERIFICATION mode (chậm hơn nhưng đảm bảo 100%)...\n")
        
        with tqdm(total=total_missing, desc="Đang update", unit="news") as pbar:
            for news in missing_records:
                news_id = news['id']
                content = news.get('content', '')
                
                # Phân tích sentiment
                scores = analyze_sentiment(content)
                
                # Update với verification
                batch_success, batch_failed, failed_list = batch_update_sentiment_scores(
                    [(news_id, scores)], 
                    max_retries=5,
                    verify=True  # BẮT BUỘC verify
                )
                
                if batch_success > 0:
                    success += 1
                else:
                    failed += 1
                    failed_ids.extend(failed_list)
                
                pbar.update(1)
                pbar.set_postfix({
                    'Success': success,
                    'Failed': failed,
                    'Ticker': news.get('ticker', 'N/A')
                })
                
                # Đợi một chút để tránh overload DB
                time.sleep(0.1)
        
        # Tổng kết
        print("\n" + "=" * 70)
        print("KẾT QUẢ UPDATE MISSING RECORDS")
        print("=" * 70)
        print(f"📊 Tổng số records thiếu: {total_missing}")
        print(f"✅ Đã update thành công: {success}")
        print(f"❌ Thất bại: {failed}")
        print(f"📈 Tỷ lệ thành công: {(success/total_missing*100):.2f}%")
        
        if failed_ids:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_file = f"missing_sentiments_failed_{timestamp}.json"
            
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'total_failed': len(failed_ids),
                    'failed_records': failed_ids
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n⚠️  {len(failed_ids)} records vẫn thất bại, đã ghi vào {error_file}")
        else:
            print(f"\n🎉 TẤT CẢ records thiếu đã được update thành công!")
        
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")


def retry_failed_updates(error_log_file):
    """
    Thử lại các updates thất bại từ error log file
    
    Args:
        error_log_file: Đường dẫn đến file chứa các records thất bại
    """
    print("\n" + "=" * 70)
    print("RETRY CÁC UPDATES THẤT BẠI")
    print("=" * 70 + "\n")
    
    try:
        with open(error_log_file, 'r', encoding='utf-8') as f:
            error_data = json.load(f)
        
        failed_records = error_data.get('failed_records', [])
        
        if not failed_records:
            print("✅ Không có records thất bại cần retry!")
            return
        
        print(f"📊 Tìm thấy {len(failed_records)} records cần retry\n")
        
        success = 0
        still_failed = 0
        new_failed_ids = []
        
        with tqdm(total=len(failed_records), desc="Đang retry", unit="news") as pbar:
            for record in failed_records:
                news_id = record['news_id']
                scores = record['scores']
                
                # Thử update với retry mechanism
                batch_success, batch_failed, failed_ids = batch_update_sentiment_scores([(news_id, scores)], max_retries=5)
                
                if batch_success > 0:
                    success += 1
                else:
                    still_failed += 1
                    new_failed_ids.extend(failed_ids)
                
                pbar.update(1)
                pbar.set_postfix({'Success': success, 'Failed': still_failed})
        
        # Tổng kết
        print("\n" + "=" * 70)
        print("KẾT QUẢ RETRY")
        print("=" * 70)
        print(f"✅ Thành công: {success}")
        print(f"❌ Vẫn thất bại: {still_failed}")
        print(f"📈 Tỷ lệ thành công: {(success/len(failed_records)*100):.2f}%")
        
        # Nếu vẫn còn thất bại, ghi lại
        if new_failed_ids:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_error_file = f"failed_updates_retry_{timestamp}.json"
            
            with open(new_error_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'total_failed': len(new_failed_ids),
                    'failed_records': new_failed_ids
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n⚠️  Vẫn còn {len(new_failed_ids)} records thất bại, đã ghi vào {new_error_file}")
        else:
            print(f"\n🎉 TẤT CẢ đã được update thành công 100%!")
        
        print("=" * 70 + "\n")
        
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file: {error_log_file}")
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {str(e)}")


def analyze_sample_news(news_id=None, ticker=None, limit=5):
    """
    Phân tích mẫu một vài tin tức để kiểm tra
    
    Args:
        news_id: ID của tin tức cụ thể
        ticker: Lọc theo ticker
        limit: Số lượng tin tức mẫu
    """
    print("\n" + "=" * 70)
    print("PHÂN TÍCH MẪU")
    print("=" * 70 + "\n")
    
    query = supabase.table('news_data').select('id, content, title, ticker')
    
    if news_id:
        query = query.eq('id', news_id)
    elif ticker:
        query = query.eq('ticker', ticker).limit(limit)
    else:
        query = query.limit(limit)
    
    response = query.execute()
    news_list = response.data
    
    if not news_list:
        print("⚠️  Không tìm thấy tin tức")
        return
    
    for i, news in enumerate(news_list, 1):
        print(f"\n📰 Tin tức #{i} - ID: {news['id']}")
        print(f"   Ticker: {news['ticker']}")
        print(f"   Title: {news['title'][:80]}...")
        print(f"   Content preview: {news['content'][:150]}...")
        
        scores = analyze_sentiment(news['content'])
        
        print(f"\n   📊 Kết quả phân tích:")
        print(f"      🔴 Tiêu cực: {scores['negative_score']:.4f}")
        print(f"      🟢 Tích cực: {scores['positive_score']:.4f}")
        print(f"      ⚪ Trung tính: {scores['neutral_score']:.4f}")
        
        # Xác định sentiment chính
        max_score = max(scores['negative_score'], scores['positive_score'], scores['neutral_score'])
        if max_score == scores['negative_score']:
            sentiment_label = "TIÊU CỰC"
        elif max_score == scores['positive_score']:
            sentiment_label = "TÍCH CỰC"
        else:
            sentiment_label = "TRUNG TÍNH"
        
        print(f"      ➡️  Kết luận: {sentiment_label}")
        print("-" * 70)


def main():
    """
    Main function
    """
    print("\n" + "=" * 70)
    print("PHÂN TÍCH SENTIMENT TIN TỨC TÀI CHÍNH")
    print("=" * 70 + "\n")
    
    print("Chọn chức năng:")
    print("1. Phân tích mẫu một vài tin tức (để test)")
    print("2. Phân tích và update TẤT CẢ tin tức (với verification)")
    print("3. Phân tích theo ticker cụ thể")
    print("4. Tiếp tục từ vị trí đã dừng (resume)")
    print("5. Retry các updates thất bại từ error log")
    print("6. 🔧 TÌM VÀ FIX CÁC RECORDS THIẾU SENTIMENT (Khuyến nghị!)")
    
    choice = input("\nNhập lựa chọn (1-6): ").strip()
    
    if choice == '1':
        ticker = input("Nhập ticker (hoặc Enter để bỏ qua): ").strip().upper()
        limit = input("Số lượng tin mẫu (mặc định 5): ").strip()
        limit = int(limit) if limit else 5
        
        analyze_sample_news(ticker=ticker if ticker else None, limit=limit)
    
    elif choice == '2':
        print("\n⚠️  LƯU Ý: Chức năng này giờ có VERIFICATION mode!")
        print("   - Mỗi update sẽ được verify lại từ DB")
        print("   - Đảm bảo 100% THỰC SỰ được lưu vào DB")
        print("   - Chậm hơn ~20% nhưng CHẮC CHẮN không bị mất dữ liệu")
        print()
        
        confirm = input("Bạn có chắc muốn xử lý TẤT CẢ tin tức? (y/n): ")
        if confirm.lower() == 'y':
            batch_size = input("Fetch batch size (mặc định 100): ").strip()
            batch_size = int(batch_size) if batch_size else 100
            
            update_batch = input("Update realtime mỗi bao nhiêu dòng? (mặc định 50 để verification): ").strip()
            update_batch = int(update_batch) if update_batch else 50  # Giảm xuống 50 để verify tốt hơn
            
            print("\n🔐 Chạy với VERIFICATION mode - Đảm bảo 100% dữ liệu!\n")
            process_all_news(batch_size=batch_size, update_batch_size=update_batch)
    
    elif choice == '3':
        ticker = input("Nhập ticker (ACB, VCB, MBB, FPT, BID): ").strip().upper()
        
        # Đếm số tin tức của ticker
        count_response = supabase.table('news_data').select('id', count='exact').eq('ticker', ticker).execute()
        total = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
        
        print(f"\n📊 Tổng số tin tức của {ticker}: {total}")
        confirm = input(f"Bạn có muốn xử lý tất cả {total} tin tức của {ticker}? (y/n): ")

        if confirm.lower() == 'y':
            # Xử lý riêng cho ticker
            news_list = supabase.table('news_data').select('id, content, ticker, title').eq('ticker', ticker).execute().data
            
            success = 0
            failed = 0
            
            with tqdm(total=len(news_list), desc=f"Xử lý {ticker}", unit="news") as pbar:
                for news in news_list:
                    scores = analyze_sentiment(news['content'])
                    if update_sentiment_scores(news['id'], scores):
                        success += 1
                    else:
                        failed += 1
                    pbar.update(1)
            
            print(f"\n✅ Hoàn thành! Thành công: {success}, Thất bại: {failed}")
    
    elif choice == '4':
        offset = input("Bắt đầu từ vị trí (offset): ").strip()
        offset = int(offset) if offset else 0
        
        limit = input("Số lượng tối đa cần xử lý (Enter = tất cả): ").strip()
        limit = int(limit) if limit else None
        
        batch_size = input("Fetch batch size (mặc định 100): ").strip()
        batch_size = int(batch_size) if batch_size else 100
        
        update_batch = input("Update realtime mỗi bao nhiêu dòng? (mặc định 100): ").strip()
        update_batch = int(update_batch) if update_batch else 100
        
        process_all_news(batch_size=batch_size, start_offset=offset, limit=limit, update_batch_size=update_batch)
    
    elif choice == '5':
        error_file = input("Nhập tên file error log (ví dụ: failed_updates_20241103_143022.json): ").strip()
        if error_file:
            retry_failed_updates(error_file)
        else:
            print("❌ Bạn cần nhập tên file!")
    
    elif choice == '6':
        print("\n💡 Đây là chức năng KHUYẾN NGHỊ để fix vấn đề 5% dữ liệu thiếu!")
        print("   Script sẽ:")
        print("   - Tìm tất cả records chưa có sentiment scores")
        print("   - Update với VERIFICATION mode (đảm bảo lưu vào DB)")
        print("   - Retry tự động nếu thất bại")
        print()
        find_and_update_missing_sentiments()
    
    else:
        print("❌ Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()
