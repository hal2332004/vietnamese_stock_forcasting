"""
Script to clean and merge stock market news data
- Check and remove NaN and duplicate values
- Split rows with multiple tickers into separate rows
- Keep only records with dates between 2015 and 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

def parse_vietnamese_date(date_str):
    """
    Parse Vietnamese date format to datetime
    Example: "Thứ ba, 26/12/2023, 15:59 (GMT+7)"
    """
    try:
        # Extract the date part (DD/MM/YYYY)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_str)
        if date_match:
            date_part = date_match.group(1)
            # Parse to datetime
            dt = datetime.strptime(date_part, '%d/%m/%Y')
            return dt
        return None
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def clean_ticker_string(ticker_str):
    """
    Clean and normalize ticker string
    Remove extra spaces, convert to uppercase
    """
    if pd.isna(ticker_str):
        return []
    
    # Convert to string and clean
    ticker_str = str(ticker_str).strip()
    
    # Split by comma and clean each ticker
    tickers = [t.strip().upper() for t in ticker_str.split(',')]
    
    # Remove empty strings
    tickers = [t for t in tickers if t]
    
    return tickers

def process_stock_news_data(input_files, output_file):
    """
    Main function to process stock market news data from multiple files
    
    Args:
        input_files: List of input CSV file paths
        output_file: Output CSV file path
    """
    print(f"Reading data from {len(input_files)} files:")
    for f in input_files:
        print(f"  - {f}")
    
    # Read and concatenate all CSV files
    dfs = []
    for input_file in input_files:
        df_temp = pd.read_csv(input_file)
        print(f"  Loaded {df_temp.shape[0]} rows from {input_file.split('/')[-1]}")
        dfs.append(df_temp)
    
    df = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined data shape: {df.shape}")
    
    print(f"Original data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Step 1: Remove rows with NaN values in critical columns
    print("\n=== Step 1: Removing NaN values ===")
    print(f"NaN values before cleaning:\n{df.isna().sum()}")
    
    # Remove rows where any critical column is NaN
    df_clean = df.dropna(subset=['date', 'title', 'content', 'tickers'])
    
    print(f"Shape after removing NaN: {df_clean.shape}")
    print(f"Removed {df.shape[0] - df_clean.shape[0]} rows with NaN values")
    
    # Step 2: Remove duplicate rows
    print("\n=== Step 2: Removing duplicates ===")
    df_clean = df_clean.drop_duplicates(subset=['date', 'title', 'content'], keep='first')
    
    print(f"Shape after removing duplicates: {df_clean.shape}")
    
    # Step 3: Parse dates and filter by year range (2015-2025)
    print("\n=== Step 3: Filtering by date range (2015-2025) ===")
    
    # Parse dates
    df_clean['parsed_date'] = df_clean['date'].apply(parse_vietnamese_date)
    
    # Remove rows where date parsing failed
    df_clean = df_clean[df_clean['parsed_date'].notna()]
    
    # Extract year
    df_clean['year'] = df_clean['parsed_date'].dt.year
    
    # Filter by year range
    df_clean = df_clean[(df_clean['year'] >= 2015) & (df_clean['year'] <= 2025)]
    
    print(f"Shape after date filtering: {df_clean.shape}")
    print(f"Year distribution:\n{df_clean['year'].value_counts().sort_index()}")
    
    # Step 4: Split rows with multiple tickers
    print("\n=== Step 4: Splitting multiple tickers into separate rows ===")
    
    # Create a list to store expanded rows
    expanded_rows = []
    
    for idx, row in df_clean.iterrows():
        tickers = clean_ticker_string(row['tickers'])
        
        if len(tickers) == 0:
            # Skip rows with no valid tickers
            continue
        elif len(tickers) == 1:
            # Single ticker - keep as is
            new_row = row.copy()
            new_row['ticker'] = tickers[0]
            expanded_rows.append(new_row)
        else:
            # Multiple tickers - create separate rows
            for ticker in tickers:
                new_row = row.copy()
                new_row['ticker'] = ticker
                expanded_rows.append(new_row)
    
    # Create new dataframe from expanded rows
    df_expanded = pd.DataFrame(expanded_rows)
    
    print(f"Shape after splitting tickers: {df_expanded.shape}")
    print(f"Number of unique tickers: {df_expanded['ticker'].nunique()}")
    print(f"Top tickers:\n{df_expanded['ticker'].value_counts().head(10)}")
    
    # Step 5: Select and reorder columns for final output
    print("\n=== Step 5: Preparing final output ===")
    
    # Select columns for output
    output_columns = ['date', 'year', 'ticker', 'title', 'content', 'source']
    
    # Check if 'source' column exists
    if 'source' not in df_expanded.columns:
        df_expanded['source'] = df_expanded.get('tickers', '')
    
    df_final = df_expanded[output_columns].copy()
    
    # Sort by date and ticker
    df_final = df_final.sort_values(['year', 'date', 'ticker']).reset_index(drop=True)
    
    # Save to CSV
    print(f"\nSaving cleaned data to: {output_file}")
    df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n=== Summary ===")
    print(f"Original records: {df.shape[0]}")
    print(f"Final records: {df_final.shape[0]}")
    print(f"Records removed/transformed: {df.shape[0] - df_clean.shape[0]} (NaN/duplicates)")
    print(f"Records expanded: {df_final.shape[0] - df_clean.shape[0]} (multiple tickers)")
    print(f"Unique tickers: {df_final['ticker'].nunique()}")
    print(f"Date range: {df_final['year'].min()} - {df_final['year'].max()}")
    print(f"\nCleaned data saved successfully!")
    
    return df_final

if __name__ == "__main__":
    # Define input and output file paths
    input_files = [
        "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode/data/stock_market_news_fpt_bid_2015_2025.csv",
        "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode/data/ACB_VCB_MBB.csv"
    ]
    output_file = "/mnt/d/Ky 4/financial-news-sentiment-main/Source/recode/data/stock_market_news_cleaned_merged.csv"
    
    # Process the data
    df_result = process_stock_news_data(input_files, output_file)
    
    # Display sample of cleaned data
    print("\n=== Sample of cleaned data (first 5 rows) ===")
    print(df_result.head())
    
    print("\n=== Sample of cleaned data (last 5 rows) ===")
    print(df_result.tail())
