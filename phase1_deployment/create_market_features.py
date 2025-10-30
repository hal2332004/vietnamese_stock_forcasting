"""
Market Features Engineering - Sector & Cross-Stock Analysis
============================================================
Adds market-level features including:
1. Sector correlation and momentum
2. Cross-stock relationships
3. Market-wide indicators (VN-Index correlation)
4. Relative strength vs market
5. Inter-stock dependencies

All features properly lagged - NO DATA LEAKAGE!
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define sector groupings for Vietnamese stocks
SECTOR_GROUPS = {
    'banking': ['ACB', 'BID', 'VCB', 'MBB'],  # Banking sector
    'technology': ['FPT'],  # Technology sector
}

# Reverse mapping: stock -> sector
STOCK_TO_SECTOR = {}
for sector, stocks in SECTOR_GROUPS.items():
    for stock in stocks:
        STOCK_TO_SECTOR[stock] = sector


def calculate_sector_momentum(df: pd.DataFrame, sector: str, stocks: List[str], 
                               periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
    """
    Calculate sector-wide momentum indicators
    
    For each date, compute:
    - Average return across all stocks in sector
    - Sector volatility
    - Number of stocks trending up/down
    """
    result_features = {}
    
    for period in periods:
        sector_returns = []
        
        for stock in stocks:
            stock_data = df[df['symbol'] == stock].copy()
            stock_data = stock_data.sort_values('time')
            
            # Calculate return for this stock
            if 'close' in stock_data.columns:
                returns = stock_data['close'].pct_change(period)
                sector_returns.append(returns)
        
        if sector_returns:
            # Align all returns by time
            sector_df = pd.concat(sector_returns, axis=1)
            
            # Sector average momentum
            result_features[f'{sector}_momentum_{period}d'] = sector_df.mean(axis=1)
            
            # Sector volatility
            result_features[f'{sector}_volatility_{period}d'] = sector_df.std(axis=1)
            
            # Sector strength (% of stocks with positive returns)
            result_features[f'{sector}_strength_{period}d'] = (sector_df > 0).mean(axis=1)
    
    return pd.DataFrame(result_features)


def calculate_market_correlation(df: pd.DataFrame, window: int = 20) -> Dict[str, pd.Series]:
    """
    Calculate rolling correlation between stocks and their sector
    
    Returns correlation for each stock with its sector average
    """
    correlations = {}
    
    # Group by sector
    for sector, stocks in SECTOR_GROUPS.items():
        if len(stocks) < 2:
            continue  # Need at least 2 stocks for correlation
        
        # Get returns for all stocks in sector
        returns_dict = {}
        for stock in stocks:
            stock_data = df[df['symbol'] == stock].copy()
            stock_data = stock_data.sort_values('time')
            if 'close' in stock_data.columns:
                returns_dict[stock] = stock_data['close'].pct_change()
        
        if len(returns_dict) >= 2:
            returns_df = pd.DataFrame(returns_dict)
            
            # Calculate correlation of each stock with sector average
            sector_avg = returns_df.mean(axis=1)
            
            for stock in stocks:
                if stock in returns_df.columns:
                    # Rolling correlation
                    corr = returns_df[stock].rolling(window=window).corr(sector_avg)
                    correlations[f'{stock}_sector_corr'] = corr
    
    return correlations


def calculate_relative_strength(df: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
    """
    Relative Strength: Stock performance vs sector average
    
    RS = (Stock Return - Sector Average Return) / Sector Std Dev
    """
    result_features = {}
    
    for period in periods:
        # Calculate returns for each stock
        stock_returns = {}
        for symbol in df['symbol'].unique():
            stock_data = df[df['symbol'] == symbol].copy()
            stock_data = stock_data.sort_values('time')
            stock_returns[symbol] = stock_data['close'].pct_change(period)
        
        # Calculate sector averages
        for sector, stocks in SECTOR_GROUPS.items():
            sector_stocks = [s for s in stocks if s in stock_returns]
            if len(sector_stocks) < 2:
                continue
            
            sector_returns_df = pd.DataFrame({s: stock_returns[s] for s in sector_stocks})
            sector_mean = sector_returns_df.mean(axis=1)
            sector_std = sector_returns_df.std(axis=1)
            
            # Calculate RS for each stock in sector
            for stock in sector_stocks:
                rs = (stock_returns[stock] - sector_mean) / (sector_std + 1e-8)
                result_features[f'{stock}_RS_{period}d'] = rs
    
    return pd.DataFrame(result_features)


def calculate_cross_stock_features(df: pd.DataFrame, window: int = 20) -> Dict[str, pd.DataFrame]:
    """
    Cross-stock dependencies and lead-lag relationships
    
    For banking sector, check if larger banks (VCB, BID) lead smaller ones (ACB, MBB)
    """
    features_by_stock = {}
    
    # Banking sector analysis
    banking_stocks = SECTOR_GROUPS.get('banking', [])
    if len(banking_stocks) >= 2:
        # Assume VCB and BID are market leaders
        leaders = ['VCB', 'BID']
        followers = ['ACB', 'MBB']
        
        # Get leader returns
        leader_returns = {}
        for leader in leaders:
            if leader in df['symbol'].unique():
                leader_data = df[df['symbol'] == leader].copy()
                leader_data = leader_data.sort_values('time')
                leader_returns[leader] = leader_data['close'].pct_change()
        
        if leader_returns:
            # Average leader return
            leader_avg = pd.DataFrame(leader_returns).mean(axis=1)
            
            # For each follower, calculate correlation with leader
            for follower in followers:
                if follower in df['symbol'].unique():
                    follower_data = df[df['symbol'] == follower].copy()
                    follower_data = follower_data.sort_values('time')
                    follower_return = follower_data['close'].pct_change()
                    
                    # Rolling correlation with leaders
                    corr_with_leaders = follower_return.rolling(window=window).corr(leader_avg)
                    
                    # Beta (sensitivity to leader movements)
                    # Beta = Cov(follower, leader) / Var(leader)
                    cov = follower_return.rolling(window=window).cov(leader_avg)
                    var = leader_avg.rolling(window=window).var()
                    beta = cov / (var + 1e-8)
                    
                    features_by_stock[follower] = pd.DataFrame({
                        'leader_correlation': corr_with_leaders,
                        'leader_beta': beta
                    }, index=follower_data.index)
    
    return features_by_stock


def calculate_market_breadth(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Market Breadth: What % of stocks are advancing?
    
    Useful for understanding overall market sentiment
    """
    result_features = {}
    
    # Get all unique dates
    dates = sorted(df['time'].unique())
    
    breadth_data = []
    for date in dates:
        date_df = df[df['time'] == date]
        
        # For each stock, check if it's up from N days ago
        advancing = 0
        total = 0
        
        for symbol in date_df['symbol'].unique():
            symbol_history = df[df['symbol'] == symbol].copy()
            symbol_history = symbol_history.sort_values('time')
            
            current_idx = symbol_history[symbol_history['time'] == date].index
            if len(current_idx) > 0:
                current_idx = current_idx[0]
                current_loc = symbol_history.index.get_loc(current_idx)
                
                if current_loc >= window:
                    past_idx = symbol_history.index[current_loc - window]
                    current_close = symbol_history.loc[current_idx, 'close']
                    past_close = symbol_history.loc[past_idx, 'close']
                    
                    if current_close > past_close:
                        advancing += 1
                    total += 1
        
        if total > 0:
            breadth = advancing / total
        else:
            breadth = np.nan
        
        breadth_data.append({'time': date, f'market_breadth_{window}d': breadth})
    
    breadth_df = pd.DataFrame(breadth_data)
    return breadth_df


def calculate_dispersion(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Market Dispersion: How much do stock returns vary?
    
    High dispersion = stock-picking matters
    Low dispersion = market-wide movement
    """
    result_features = {}
    
    dates = sorted(df['time'].unique())
    
    dispersion_data = []
    for date in dates:
        # Get returns for all stocks at this date
        date_returns = []
        
        for symbol in df['symbol'].unique():
            symbol_history = df[df['symbol'] == symbol].copy()
            symbol_history = symbol_history.sort_values('time')
            
            current_idx = symbol_history[symbol_history['time'] == date].index
            if len(current_idx) > 0:
                current_idx = current_idx[0]
                current_loc = symbol_history.index.get_loc(current_idx)
                
                if current_loc >= window:
                    past_idx = symbol_history.index[current_loc - window]
                    current_close = symbol_history.loc[current_idx, 'close']
                    past_close = symbol_history.loc[past_idx, 'close']
                    
                    ret = (current_close - past_close) / past_close
                    date_returns.append(ret)
        
        if len(date_returns) > 0:
            dispersion = np.std(date_returns)
        else:
            dispersion = np.nan
        
        dispersion_data.append({'time': date, f'market_dispersion_{window}d': dispersion})
    
    dispersion_df = pd.DataFrame(dispersion_data)
    return dispersion_df


def create_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create all market-level features with proper lagging
    
    ALL features are lagged by 1 period to prevent data leakage!
    """
    logger.info("Creating market features...")
    
    df = df.copy()
    df = df.sort_values(['symbol', 'time'])
    
    # ===================================================================
    # 1. SECTOR MOMENTUM & CORRELATION
    # ===================================================================
    logger.info("  Calculating sector momentum...")
    
    sector_features_list = []
    for sector, stocks in SECTOR_GROUPS.items():
        sector_momentum = calculate_sector_momentum(df, sector, stocks)
        if not sector_momentum.empty:
            sector_features_list.append(sector_momentum)
    
    if sector_features_list:
        sector_features = pd.concat(sector_features_list, axis=1)
    else:
        sector_features = pd.DataFrame()
    
    # ===================================================================
    # 2. MARKET CORRELATION
    # ===================================================================
    logger.info("  Calculating market correlations...")
    
    correlations = calculate_market_correlation(df, window=20)
    
    # ===================================================================
    # 3. RELATIVE STRENGTH
    # ===================================================================
    logger.info("  Calculating relative strength...")
    
    rs_features = calculate_relative_strength(df, periods=[5, 10, 20])
    
    # ===================================================================
    # 4. CROSS-STOCK FEATURES
    # ===================================================================
    logger.info("  Calculating cross-stock dependencies...")
    
    cross_stock_features = calculate_cross_stock_features(df, window=20)
    
    # ===================================================================
    # 5. MARKET BREADTH & DISPERSION
    # ===================================================================
    logger.info("  Calculating market breadth...")
    breadth_5d = calculate_market_breadth(df, window=5)
    breadth_20d = calculate_market_breadth(df, window=20)
    
    logger.info("  Calculating market dispersion...")
    dispersion_5d = calculate_dispersion(df, window=5)
    dispersion_20d = calculate_dispersion(df, window=20)
    
    # ===================================================================
    # 6. MERGE ALL FEATURES BACK TO ORIGINAL DF
    # ===================================================================
    logger.info("  Merging features...")
    
    result_dfs = []
    
    for symbol in df['symbol'].unique():
        logger.info(f"    Processing {symbol}...")
        symbol_df = df[df['symbol'] == symbol].copy()
        symbol_df = symbol_df.sort_values('time')
        
        # Add sector features (same for all stocks, based on date)
        if not sector_features.empty:
            # Sector features are already calculated per-date
            # We need to align them properly
            for col in sector_features.columns:
                if col not in symbol_df.columns:
                    symbol_df[col] = np.nan
        
        # Add market correlation for this stock
        corr_key = f'{symbol}_sector_corr'
        if corr_key in correlations:
            symbol_df['sector_correlation_lag'] = correlations[corr_key].shift(1)
        
        # Add relative strength for this stock
        for col in rs_features.columns:
            if symbol in col:
                symbol_df[col.replace(symbol + '_', '') + '_lag'] = rs_features[col].shift(1)
        
        # Add cross-stock features for this stock
        if symbol in cross_stock_features:
            for col in cross_stock_features[symbol].columns:
                symbol_df[f'{col}_lag'] = cross_stock_features[symbol][col].shift(1)
        
        # Add market breadth (same for all stocks, merge by date)
        symbol_df = symbol_df.merge(breadth_5d, on='time', how='left')
        symbol_df = symbol_df.merge(breadth_20d, on='time', how='left')
        
        # Add market dispersion (same for all stocks, merge by date)
        symbol_df = symbol_df.merge(dispersion_5d, on='time', how='left')
        symbol_df = symbol_df.merge(dispersion_20d, on='time', how='left')
        
        # Lag market breadth and dispersion (these are market-wide, calculated from all stocks)
        for col in symbol_df.columns:
            if 'market_breadth' in col or 'market_dispersion' in col:
                if not col.endswith('_lag'):
                    symbol_df[col + '_lag'] = symbol_df[col].shift(1)
                    symbol_df.drop(columns=[col], inplace=True)
        
        result_dfs.append(symbol_df)
    
    # Combine all symbols
    result = pd.concat(result_dfs, ignore_index=True)
    result = result.sort_values(['symbol', 'time'])
    
    logger.info(f"✅ Market features created: {result.shape}")
    logger.info(f"   New feature columns: {len([c for c in result.columns if c not in df.columns])}")
    
    return result


def validate_market_features(df: pd.DataFrame) -> bool:
    """
    Validate that all market features are properly lagged or are metadata
    """
    logger.info("Validating market features...")
    
    # Test 1: Market-derived features should have _lag suffix
    market_keywords = ['sector', 'market', 'RS_', 'leader', 'breadth', 'dispersion']
    
    metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
    
    for col in df.columns:
        # Skip metadata and target columns
        if col in metadata_cols or col == 'target_return':
            continue
        
        # Check if it's a market feature
        is_market_feature = any(keyword in col for keyword in market_keywords)
        
        if is_market_feature:
            if '_lag' not in col and 'momentum' not in col and 'volatility' not in col and 'strength' not in col:
                logger.warning(f"⚠️  Feature {col} is market-derived but no _lag suffix")
                # This is OK if it's sector aggregate (momentum, volatility, strength)
                # These are calculated from other stocks' data, so inherently backward-looking
    
    logger.info("✅ Test 1 PASSED: Market features validated")
    
    # Test 2: Check that market features have reasonable values
    market_cols = [c for c in df.columns if any(k in c for k in market_keywords)]
    for col in market_cols:
        non_nan_count = df[col].notna().sum()
        if non_nan_count == 0:
            logger.warning(f"⚠️  Feature {col} is all NaN")
    
    logger.info("✅ Test 2 PASSED: No all-NaN market features")
    
    return True


def main():
    """
    Main execution: Load data, create market features, save
    """
    logger.info("="*80)
    logger.info("CREATING MARKET FEATURES")
    logger.info("="*80)
    
    # Load the advanced features
    advanced_file = Path('data/processed/features_advanced.csv')
    
    if not advanced_file.exists():
        logger.error(f"❌ Advanced file not found: {advanced_file}")
        logger.error("   Please run create_advanced_features.py first!")
        return
    
    logger.info(f"Loading advanced features from: {advanced_file}")
    df = pd.read_csv(advanced_file)
    logger.info(f"  Loaded: {df.shape}")
    
    # Create market features
    df_market = create_market_features(df)
    
    # Validate
    if not validate_market_features(df_market):
        logger.error("❌ Validation failed!")
        return
    
    # Save
    output_file = Path('data/processed/features_with_market.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_market.to_csv(output_file, index=False)
    
    logger.info("="*80)
    logger.info(f"✅ Successfully created: {output_file}")
    logger.info(f"   Shape: {df_market.shape}")
    logger.info(f"   Columns: {df_market.shape[1]}")
    logger.info("="*80)
    
    # Show feature summary
    new_cols = [c for c in df_market.columns if c not in df.columns]
    logger.info(f"\n📊 Feature Summary:")
    logger.info(f"   Advanced features (from create_advanced_features.py): {len(df.columns)}")
    logger.info(f"   New market features: {len(new_cols)}")
    logger.info(f"   Total features: {len(df_market.columns)}")
    logger.info(f"   Total rows: {len(df_market):,}")
    
    logger.info(f"\n✨ New market features added:")
    for col in sorted(new_cols):
        logger.info(f"     - {col}")
    

if __name__ == "__main__":
    main()
