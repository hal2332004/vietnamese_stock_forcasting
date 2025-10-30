"""
Enhanced Feature Engineering - Advanced Technical Indicators
=============================================================
Extends fix_data_leakage.py with advanced technical indicators for stock prediction.

New indicators added:
1. Momentum Indicators: MACD, Stochastic Oscillator, Williams %R, ROC
2. Trend Indicators: ADX, Parabolic SAR
3. Volume Indicators: OBV, MFI, Chaikin Money Flow
4. Volatility Indicators: Keltner Channels, ATR expansions
5. Market Features: Sector correlation, regime detection

All features properly lagged - NO DATA LEAKAGE!
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_macd(close: pd.Series, fast=12, slow=26, signal=9) -> Dict[str, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)
    
    Returns:
        - MACD line: Fast EMA - Slow EMA
        - Signal line: EMA of MACD
        - Histogram: MACD - Signal
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'MACD': macd_line,
        'MACD_signal': signal_line,
        'MACD_histogram': histogram
    }


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                         k_period=14, d_period=3) -> Dict[str, pd.Series]:
    """
    Stochastic Oscillator
    
    %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = SMA of %K
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return {
        'stoch_k': k_percent,
        'stoch_d': d_percent
    }


def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period=14) -> pd.Series:
    """
    Williams %R
    
    %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams_r


def calculate_roc(close: pd.Series, period=12) -> pd.Series:
    """
    Rate of Change (ROC)
    
    ROC = (Close - Close N periods ago) / Close N periods ago * 100
    """
    roc = 100 * (close - close.shift(period)) / close.shift(period)
    return roc


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> Dict[str, pd.Series]:
    """
    ADX (Average Directional Index) - Trend Strength Indicator
    
    Returns:
        - ADX: Trend strength (0-100)
        - +DI: Positive directional indicator
        - -DI: Negative directional indicator
    """
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    plus_dm_series = pd.Series(plus_dm, index=close.index).rolling(window=period).mean()
    minus_dm_series = pd.Series(minus_dm, index=close.index).rolling(window=period).mean()
    
    # Directional Indicators
    plus_di = 100 * plus_dm_series / atr
    minus_di = 100 * minus_dm_series / atr
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return {
        'ADX': adx,
        'plus_DI': plus_di,
        'minus_DI': minus_di
    }


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On-Balance Volume (OBV)
    
    Cumulative volume based on price direction
    """
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def calculate_mfi(high: pd.Series, low: pd.Series, close: pd.Series, 
                  volume: pd.Series, period=14) -> pd.Series:
    """
    Money Flow Index (MFI) - Volume-weighted RSI
    
    Values: 0-100 (>80 overbought, <20 oversold)
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    # Positive and negative money flow
    positive_flow = pd.Series(0.0, index=close.index)
    negative_flow = pd.Series(0.0, index=close.index)
    
    for i in range(1, len(close)):
        if typical_price.iloc[i] > typical_price.iloc[i-1]:
            positive_flow.iloc[i] = money_flow.iloc[i]
        elif typical_price.iloc[i] < typical_price.iloc[i-1]:
            negative_flow.iloc[i] = money_flow.iloc[i]
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi


def calculate_cmf(high: pd.Series, low: pd.Series, close: pd.Series, 
                  volume: pd.Series, period=20) -> pd.Series:
    """
    Chaikin Money Flow (CMF)
    
    Measures buying/selling pressure
    """
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_multiplier = mf_multiplier.fillna(0)
    mf_volume = mf_multiplier * volume
    
    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf


def calculate_keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, 
                                period=20, atr_period=10, multiplier=2) -> Dict[str, pd.Series]:
    """
    Keltner Channels - Volatility bands
    
    Returns:
        - Upper band
        - Middle band (EMA)
        - Lower band
        - Channel width
    """
    middle = close.ewm(span=period, adjust=False).mean()
    
    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period).mean()
    
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)
    width = (upper - lower) / middle
    
    return {
        'keltner_upper': upper,
        'keltner_middle': middle,
        'keltner_lower': lower,
        'keltner_width': width
    }


def detect_market_regime(close: pd.Series, volume: pd.Series, 
                         fast_ma=20, slow_ma=50) -> Dict[str, pd.Series]:
    """
    Market Regime Detection
    
    Returns:
        - regime: 1 (bull), -1 (bear), 0 (sideways)
        - trend_strength: How strong the trend is
        - volume_regime: 1 (high), -1 (low)
    """
    sma_fast = close.rolling(window=fast_ma).mean()
    sma_slow = close.rolling(window=slow_ma).mean()
    
    # Price regime
    regime = pd.Series(0, index=close.index)
    regime[sma_fast > sma_slow] = 1  # Bull market
    regime[sma_fast < sma_slow] = -1  # Bear market
    
    # Trend strength (distance between MAs)
    trend_strength = abs(sma_fast - sma_slow) / sma_slow
    
    # Volume regime
    vol_ma = volume.rolling(window=20).mean()
    volume_regime = pd.Series(0, index=close.index)
    volume_regime[volume > vol_ma * 1.2] = 1  # High volume
    volume_regime[volume < vol_ma * 0.8] = -1  # Low volume
    
    return {
        'price_regime': regime,
        'trend_strength_regime': trend_strength,
        'volume_regime': volume_regime
    }


def create_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create advanced technical indicators with proper lagging
    
    ALL features are lagged by 1 period to prevent data leakage!
    """
    logger.info("Creating advanced technical indicators...")
    
    df = df.copy()
    df = df.sort_values(['symbol', 'time'])
    
    result_dfs = []
    
    for symbol in df['symbol'].unique():
        logger.info(f"  Processing {symbol} - Advanced indicators...")
        symbol_df = df[df['symbol'] == symbol].copy()
        symbol_df = symbol_df.sort_values('time')
        
        close = symbol_df['close']
        high = symbol_df['high']
        low = symbol_df['low']
        volume = symbol_df['volume']
        
        # ===================================================================
        # 1. MOMENTUM INDICATORS
        # ===================================================================
        
        # MACD
        macd_dict = calculate_macd(close)
        symbol_df['MACD_lag'] = macd_dict['MACD'].shift(1)
        symbol_df['MACD_signal_lag'] = macd_dict['MACD_signal'].shift(1)
        symbol_df['MACD_histogram_lag'] = macd_dict['MACD_histogram'].shift(1)
        
        # Stochastic Oscillator
        stoch_dict = calculate_stochastic(high, low, close)
        symbol_df['stoch_k_lag'] = stoch_dict['stoch_k'].shift(1)
        symbol_df['stoch_d_lag'] = stoch_dict['stoch_d'].shift(1)
        
        # Williams %R
        symbol_df['williams_r_lag'] = calculate_williams_r(high, low, close).shift(1)
        
        # Rate of Change
        symbol_df['ROC_12_lag'] = calculate_roc(close, 12).shift(1)
        symbol_df['ROC_25_lag'] = calculate_roc(close, 25).shift(1)
        
        # ===================================================================
        # 2. TREND INDICATORS
        # ===================================================================
        
        # ADX
        adx_dict = calculate_adx(high, low, close)
        symbol_df['ADX_lag'] = adx_dict['ADX'].shift(1)
        symbol_df['plus_DI_lag'] = adx_dict['plus_DI'].shift(1)
        symbol_df['minus_DI_lag'] = adx_dict['minus_DI'].shift(1)
        
        # ===================================================================
        # 3. VOLUME INDICATORS
        # ===================================================================
        
        # On-Balance Volume
        obv = calculate_obv(close, volume)
        symbol_df['OBV_lag'] = obv.shift(1)
        symbol_df['OBV_change_lag'] = obv.pct_change().shift(1)
        
        # Money Flow Index
        symbol_df['MFI_lag'] = calculate_mfi(high, low, close, volume).shift(1)
        
        # Chaikin Money Flow
        symbol_df['CMF_lag'] = calculate_cmf(high, low, close, volume).shift(1)
        
        # ===================================================================
        # 4. VOLATILITY INDICATORS
        # ===================================================================
        
        # Keltner Channels
        keltner_dict = calculate_keltner_channels(high, low, close)
        symbol_df['keltner_upper_lag'] = keltner_dict['keltner_upper'].shift(1)
        symbol_df['keltner_middle_lag'] = keltner_dict['keltner_middle'].shift(1)
        symbol_df['keltner_lower_lag'] = keltner_dict['keltner_lower'].shift(1)
        symbol_df['keltner_width_lag'] = keltner_dict['keltner_width'].shift(1)
        
        # Price position in Keltner Channel
        keltner_position = (close - keltner_dict['keltner_lower']) / \
                          (keltner_dict['keltner_upper'] - keltner_dict['keltner_lower'])
        symbol_df['keltner_position_lag'] = keltner_position.shift(1)
        
        # ===================================================================
        # 5. MARKET REGIME FEATURES
        # ===================================================================
        
        regime_dict = detect_market_regime(close, volume)
        symbol_df['price_regime_lag'] = regime_dict['price_regime'].shift(1)
        symbol_df['trend_strength_regime_lag'] = regime_dict['trend_strength_regime'].shift(1)
        symbol_df['volume_regime_lag'] = regime_dict['volume_regime'].shift(1)
        
        # ===================================================================
        # 6. COMBINED SIGNALS (Lagged)
        # ===================================================================
        
        # MACD crossover signal
        macd_cross = pd.Series(0, index=close.index)
        macd_cross[macd_dict['MACD'] > macd_dict['MACD_signal']] = 1
        macd_cross[macd_dict['MACD'] < macd_dict['MACD_signal']] = -1
        symbol_df['MACD_cross_lag'] = macd_cross.shift(1)
        
        # Stochastic crossover
        stoch_cross = pd.Series(0, index=close.index)
        stoch_cross[stoch_dict['stoch_k'] > stoch_dict['stoch_d']] = 1
        stoch_cross[stoch_dict['stoch_k'] < stoch_dict['stoch_d']] = -1
        symbol_df['stoch_cross_lag'] = stoch_cross.shift(1)
        
        # ADX trend quality (strong trend > 25)
        adx_strong = (adx_dict['ADX'] > 25).astype(int)
        symbol_df['ADX_strong_trend_lag'] = adx_strong.shift(1)
        
        result_dfs.append(symbol_df)
    
    # Combine all symbols
    result = pd.concat(result_dfs, ignore_index=True)
    result = result.sort_values(['symbol', 'time'])
    
    logger.info(f"✅ Advanced features created: {result.shape}")
    logger.info(f"   New feature columns: {len([c for c in result.columns if '_lag' in c])}")
    
    return result


def validate_advanced_features(df: pd.DataFrame) -> bool:
    """
    Validate that all advanced features are properly lagged
    """
    logger.info("Validating advanced features...")
    
    # Test 1: All technical indicator columns should have _lag suffix
    indicator_keywords = ['MACD', 'stoch', 'williams', 'ROC', 'ADX', 'DI', 
                         'OBV', 'MFI', 'CMF', 'keltner', 'regime']
    
    for col in df.columns:
        for keyword in indicator_keywords:
            if keyword in col and '_lag' not in col:
                logger.error(f"❌ Feature {col} contains {keyword} but no _lag suffix!")
                return False
    
    logger.info("✅ Test 1 PASSED: All indicator features have _lag suffix")
    
    # Test 2: No NaN in early rows for lagged features should be acceptable
    lag_cols = [c for c in df.columns if '_lag' in c]
    logger.info(f"✅ Test 2: Found {len(lag_cols)} lagged features")
    
    # Test 3: Check that values make sense (no all-NaN columns)
    for col in lag_cols:
        non_nan_count = df[col].notna().sum()
        if non_nan_count == 0:
            logger.error(f"❌ Feature {col} is all NaN!")
            return False
    
    logger.info("✅ Test 3 PASSED: No all-NaN lagged features")
    
    return True


def main():
    """
    Main execution: Load data, create advanced features, save
    """
    logger.info("="*80)
    logger.info("CREATING ADVANCED TECHNICAL INDICATORS")
    logger.info("="*80)
    
    # Load the leak-free base features
    base_file = Path('data/processed/features_no_leakage.csv')
    
    if not base_file.exists():
        logger.error(f"❌ Base file not found: {base_file}")
        logger.error("   Please run fix_data_leakage.py first!")
        return
    
    logger.info(f"Loading base features from: {base_file}")
    df = pd.read_csv(base_file)
    logger.info(f"  Loaded: {df.shape}")
    
    # Create advanced features
    df_advanced = create_advanced_features(df)
    
    # Validate
    if not validate_advanced_features(df_advanced):
        logger.error("❌ Validation failed!")
        return
    
    # Save
    output_file = Path('data/processed/features_advanced.csv')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_advanced.to_csv(output_file, index=False)
    
    logger.info("="*80)
    logger.info(f"✅ Successfully created: {output_file}")
    logger.info(f"   Shape: {df_advanced.shape}")
    logger.info(f"   Columns: {df_advanced.shape[1]}")
    logger.info("="*80)
    
    # Show feature summary
    lag_features = [c for c in df_advanced.columns if '_lag' in c]
    logger.info(f"\n📊 Feature Summary:")
    logger.info(f"   Base features (from fix_data_leakage.py): {len(df.columns)}")
    logger.info(f"   New advanced features: {len(df_advanced.columns) - len(df.columns)}")
    logger.info(f"   Total lagged features: {len(lag_features)}")
    logger.info(f"   Total rows: {len(df_advanced):,}")
    

if __name__ == "__main__":
    main()
