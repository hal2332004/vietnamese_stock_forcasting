"""
Add News Features from Filtered News Dataset
============================================

This script extracts sentiment and news-based features from the filtered news CSV
and merges them with the existing stock features.

Features created:
- Ticker-specific: news_count, sentiment_score, has_news (1d, 3d, 7d)
- Market-wide: macro_sentiment, macro_news_count (1d, 3d, 7d)
- Advanced: sentiment_momentum, news_volatility

Author: Stock Forecasting Project
Date: October 30, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Load PhoBERT Vietnamese sentiment model
from transformers import pipeline
print("Loading PhoBERT Vietnamese sentiment model...")
sentiment_pipeline = pipeline("text-classification", model="mr4/phobert-base-vi-sentiment-analysis")
print("Model loaded successfully!")

def calculate_sentiment_vietnamese(text):
    """
    Calculate sentiment score for Vietnamese text using PhoBERT model
    with financial keyword boosting for neutral classifications.
    
    Returns:
        float: Sentiment score between -1 (negative) and +1 (positive)
    """
    if pd.isna(text) or text == '':
        return 0.0
    
    text = str(text).strip()
    
    # Handle very short text
    if len(text) < 10:
        return 0.0
    
    try:
        # Use PhoBERT for sentiment analysis
        result = sentiment_pipeline(text[:512])[0]  # Limit to 512 chars for speed
        
        label = result['label']
        score = result['score']  # Confidence score
        
        # Debug: Print first few results to understand format
        if not hasattr(calculate_sentiment_vietnamese, '_debug_count'):
            calculate_sentiment_vietnamese._debug_count = 0
        if calculate_sentiment_vietnamese._debug_count < 3:
            print(f"   Sample {calculate_sentiment_vietnamese._debug_count + 1}: Label='{label}', Score={score:.3f}, Text='{text[:60]}...'")
            calculate_sentiment_vietnamese._debug_count += 1
        
        # PhoBERT returns Vietnamese labels
        label_lower = label.lower()
        
        # Base sentiment from PhoBERT
        base_sentiment = 0.0
        
        if 'tích cực' in label_lower or 'pos' in label_lower:
            # Positive: map score to 0 to +1
            base_sentiment = (score - 0.5) * 2  # 0.5->0, 1.0->+1.0
        elif 'tiêu cực' in label_lower or 'neg' in label_lower:
            # Negative: map score to 0 to -1
            base_sentiment = -((score - 0.5) * 2)  # 0.5->0, 1.0->-1.0
        else:
            # Neutral - apply financial keyword analysis
            text_lower = text.lower()
            
            # Strong positive financial keywords
            strong_positive = ['tăng trưởng', 'lợi nhuận', 'tăng mạnh', 'bứt phá', 'kỷ lục', 
                              'cao nhất', 'thành công', 'hồi phục', 'tăng vọt', 'bùng nổ']
            # Strong negative financial keywords  
            strong_negative = ['giảm sâu', 'thua lỗ', 'sụt giảm', 'khủng hoảng', 'bán tháo',
                              'sụp đổ', 'thấp nhất', 'hoảng loạn', 'rơi', 'mất']
            
            # Moderate positive keywords
            moderate_positive = ['tăng', 'lãi', 'tích cực', 'tốt', 'khả quan', 'cải thiện',
                               'dẫn dắt', 'hút', 'mạnh', 'ưu đãi']
            # Moderate negative keywords
            moderate_negative = ['giảm', 'lỗ', 'tiêu cực', 'xấu', 'bi quan', 'rủi ro',
                               'cảnh báo', 'yếu', 'kém', 'hạn chế']
            
            # Count keywords
            strong_pos = sum(1 for kw in strong_positive if kw in text_lower)
            strong_neg = sum(1 for kw in strong_negative if kw in text_lower)
            mod_pos = sum(1 for kw in moderate_positive if kw in text_lower)
            mod_neg = sum(1 for kw in moderate_negative if kw in text_lower)
            
            # Weighted score
            pos_score = strong_pos * 2 + mod_pos * 1
            neg_score = strong_neg * 2 + mod_neg * 1
            total = pos_score + neg_score
            
            if total > 0:
                # Apply keyword-based sentiment for neutral PhoBERT classifications
                base_sentiment = (pos_score - neg_score) / (total * 2)  # Normalize to -0.5 to +0.5
        
        return np.clip(base_sentiment, -1.0, 1.0)
            
    except Exception as e:
        print(f"Warning: Sentiment analysis failed for text: {text[:50]}... Error: {e}")
        return 0.0

def extract_tickers_from_matched(matched_str):
    """
    Extract list of tickers from matched_tickers column.
    Handles formats like: 'FPT', 'BID, VCB', 'ACB, FPT'
    """
    if pd.isna(matched_str) or matched_str == '':
        return []
    
    tickers = [t.strip() for t in str(matched_str).split(',')]
    return [t for t in tickers if t]  # Remove empty strings

def create_news_features(news_csv_path, stock_csv_path, output_path):
    """
    Create news-based features and merge with stock data.
    
    Args:
        news_csv_path: Path to filtered news CSV
        stock_csv_path: Path to stock features CSV
        output_path: Path to save enhanced features
    """
    print("=" * 60)
    print("ADDING NEWS FEATURES FROM FILTERED NEWS DATASET")
    print("=" * 60)
    
    # Load data
    print("\n1. Loading data...")
    news_df = pd.read_csv(news_csv_path)
    stock_df = pd.read_csv(stock_csv_path)
    
    print(f"   News articles: {len(news_df)}")
    print(f"   Stock records: {len(stock_df)}")
    
    # Parse dates
    news_df['date'] = pd.to_datetime(news_df['date']).dt.date
    
    # Stock data uses 'time' column, not 'date'
    if 'time' in stock_df.columns:
        stock_df['date'] = pd.to_datetime(stock_df['time']).dt.date
    else:
        stock_df['date'] = pd.to_datetime(stock_df['date']).dt.date
    
    # Calculate sentiment for each article
    print("\n2. Calculating sentiment scores...")
    news_df['sentiment'] = news_df.apply(
        lambda row: calculate_sentiment_vietnamese(
            str(row.get('title', '')) + ' ' + str(row.get('description', ''))
        ), 
        axis=1
    )
    
    print(f"   Average sentiment: {news_df['sentiment'].mean():.3f}")
    print(f"   Sentiment std: {news_df['sentiment'].std():.3f}")
    print(f"   Positive news: {(news_df['sentiment'] > 0).sum()}")
    print(f"   Negative news: {(news_df['sentiment'] < 0).sum()}")
    print(f"   Neutral news: {(news_df['sentiment'] == 0).sum()}")
    
    # Extract tickers from matched_tickers column
    print("\n3. Processing ticker-specific news...")
    news_df['tickers'] = news_df['matched_tickers'].apply(extract_tickers_from_matched)
    
    # Explode to create one row per ticker
    ticker_news = []
    for _, row in news_df.iterrows():
        if row['tickers']:  # Has matched tickers
            for ticker in row['tickers']:
                ticker_news.append({
                    'date': row['date'],
                    'symbol': ticker,
                    'sentiment': row['sentiment'],
                    'is_ticker_specific': 1
                })
    
    ticker_news_df = pd.DataFrame(ticker_news)
    print(f"   Ticker-specific news records: {len(ticker_news_df)}")
    
    if len(ticker_news_df) > 0:
        print("   News per ticker:")
        for ticker in sorted(ticker_news_df['symbol'].unique()):
            count = (ticker_news_df['symbol'] == ticker).sum()
            print(f"     {ticker}: {count}")
    
    # Create macro news dataframe (news without specific tickers)
    print("\n4. Processing market-wide macro news...")
    macro_news = news_df[news_df['matched_tickers'].isna() | (news_df['matched_tickers'] == '')].copy()
    print(f"   Macro news articles: {len(macro_news)}")
    
    # Initialize all news features in stock_df
    print("\n5. Creating news feature columns...")
    
    feature_windows = [1, 3, 7]
    
    # Ticker-specific features
    for window in feature_windows:
        stock_df[f'news_count_{window}d'] = 0
        stock_df[f'sentiment_{window}d'] = 0.0
        stock_df[f'has_news_{window}d'] = 0
    
    # Macro features
    for window in feature_windows:
        stock_df[f'macro_news_count_{window}d'] = 0
        stock_df[f'macro_sentiment_{window}d'] = 0.0
    
    # Advanced features
    stock_df['sentiment_momentum'] = 0.0
    stock_df['news_volatility_3d'] = 0.0
    stock_df['news_volatility_7d'] = 0.0
    
    # Calculate features for each stock-date
    print("\n6. Calculating rolling news features...")
    print("   This may take a few minutes...")
    
    total_rows = len(stock_df)
    processed = 0
    
    for idx, row in stock_df.iterrows():
        current_date = row['date']
        symbol = row['symbol']
        
        # Progress indicator
        processed += 1
        if processed % 1000 == 0:
            print(f"   Processed {processed}/{total_rows} rows ({100*processed/total_rows:.1f}%)")
        
        # Calculate for each window
        for window in feature_windows:
            start_date = current_date - timedelta(days=window)
            
            # TICKER-SPECIFIC FEATURES
            if len(ticker_news_df) > 0:
                ticker_window_news = ticker_news_df[
                    (ticker_news_df['symbol'] == symbol) &
                    (ticker_news_df['date'] > start_date) &
                    (ticker_news_df['date'] <= current_date)
                ]
                
                news_count = len(ticker_window_news)
                stock_df.at[idx, f'news_count_{window}d'] = news_count
                
                if news_count > 0:
                    stock_df.at[idx, f'has_news_{window}d'] = 1
                    stock_df.at[idx, f'sentiment_{window}d'] = ticker_window_news['sentiment'].mean()
            
            # MACRO FEATURES
            if len(macro_news) > 0:
                macro_window_news = macro_news[
                    (macro_news['date'] > start_date) &
                    (macro_news['date'] <= current_date)
                ]
                
                macro_count = len(macro_window_news)
                stock_df.at[idx, f'macro_news_count_{window}d'] = macro_count
                
                if macro_count > 0:
                    stock_df.at[idx, f'macro_sentiment_{window}d'] = macro_window_news['sentiment'].mean()
        
        # SENTIMENT MOMENTUM (7d vs 3d change)
        sent_7d = stock_df.at[idx, 'sentiment_7d']
        sent_3d = stock_df.at[idx, 'sentiment_3d']
        if sent_3d != 0 or sent_7d != 0:
            stock_df.at[idx, 'sentiment_momentum'] = sent_3d - sent_7d
        
        # NEWS VOLATILITY (sentiment variance)
        if len(ticker_news_df) > 0:
            # 3-day volatility
            ticker_3d = ticker_news_df[
                (ticker_news_df['symbol'] == symbol) &
                (ticker_news_df['date'] > current_date - timedelta(days=3)) &
                (ticker_news_df['date'] <= current_date)
            ]
            if len(ticker_3d) >= 2:
                stock_df.at[idx, 'news_volatility_3d'] = ticker_3d['sentiment'].std()
            
            # 7-day volatility
            ticker_7d = ticker_news_df[
                (ticker_news_df['symbol'] == symbol) &
                (ticker_news_df['date'] > current_date - timedelta(days=7)) &
                (ticker_news_df['date'] <= current_date)
            ]
            if len(ticker_7d) >= 2:
                stock_df.at[idx, 'news_volatility_7d'] = ticker_7d['sentiment'].std()
    
    print(f"   Processed {total_rows}/{total_rows} rows (100.0%)")
    
    # Summary statistics
    print("\n7. Feature summary:")
    print(f"   Original features: {len([c for c in stock_df.columns if c not in ['date', 'symbol', 'target_return']])} ")
    
    news_features = [
        'news_count_1d', 'news_count_3d', 'news_count_7d',
        'sentiment_1d', 'sentiment_3d', 'sentiment_7d',
        'has_news_1d', 'has_news_3d', 'has_news_7d',
        'macro_news_count_1d', 'macro_news_count_3d', 'macro_news_count_7d',
        'macro_sentiment_1d', 'macro_sentiment_3d', 'macro_sentiment_7d',
        'sentiment_momentum', 'news_volatility_3d', 'news_volatility_7d'
    ]
    
    print(f"   News features added: {len(news_features)}")
    print("\n   Feature statistics:")
    for feature in news_features[:9]:  # Show first 9
        non_zero = (stock_df[feature] != 0).sum()
        pct = 100 * non_zero / len(stock_df)
        if 'sentiment' in feature:
            mean_val = stock_df[stock_df[feature] != 0][feature].mean()
            print(f"     {feature:25s}: {pct:5.1f}% non-zero, mean={mean_val:+.3f}")
        else:
            mean_val = stock_df[stock_df[feature] != 0][feature].mean()
            print(f"     {feature:25s}: {pct:5.1f}% non-zero, mean={mean_val:.2f}")
    
    # Save
    print(f"\n8. Saving enhanced dataset...")
    stock_df.to_csv(output_path, index=False)
    print(f"   Saved to: {output_path}")
    print(f"   Final shape: {stock_df.shape}")
    print(f"   Total features: {len(stock_df.columns) - 3}")  # Exclude date, symbol, target_return
    
    print("\n" + "=" * 60)
    print("NEWS FEATURES ADDED SUCCESSFULLY!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Update hyperparameter_tuning.py to use the new data file")
    print("2. Run: python hyperparameter_tuning.py")
    print("3. Expected improvement: +2-5% R², +1-3% Dir.Acc")
    print("\nExpected results with news features:")
    print("  - Test R²: 0.03-0.08 (vs current ~0.003)")
    print("  - Directional Accuracy: 49-52% (vs current ~47%)")
    
    return stock_df

if __name__ == "__main__":
    # Paths
    NEWS_CSV = "../news_filtered_20251030_223911.csv"
    STOCK_CSV = "data/processed/features_with_market.csv"
    OUTPUT_CSV = "data/processed/features_with_news.csv"
    
    print("\nConfiguration:")
    print(f"  News CSV: {NEWS_CSV}")
    print(f"  Stock CSV: {STOCK_CSV}")
    print(f"  Output CSV: {OUTPUT_CSV}")
    
    # Run
    try:
        enhanced_df = create_news_features(NEWS_CSV, STOCK_CSV, OUTPUT_CSV)
        print("\n✅ Process completed successfully!")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found - {e}")
        print("\nPlease check that the following files exist:")
        print(f"  1. {NEWS_CSV}")
        print(f"  2. {STOCK_CSV}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
