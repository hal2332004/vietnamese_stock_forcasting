"""
Quick Fix - Reduce Overfitting with Simplified Parameters
==========================================================
Run this BEFORE hyperparameter tuning for quick improvement
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import xgboost as xgb
from catboost import CatBoostRegressor
import lightgbm as lgb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_and_prepare_data(data_path='data/processed/features_with_market.csv', test_size=0.2):
    """Load and prepare data"""
    df = pd.read_csv(data_path)
    df = df.sort_values('time')
    
    metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
    feature_cols = [c for c in df.columns 
                   if c not in metadata_cols and c != 'target_return']
    
    df_clean = df.dropna(subset=['target_return'])
    split_idx = int(len(df_clean) * (1 - test_size))
    
    train_df = df_clean.iloc[:split_idx]
    test_df = df_clean.iloc[split_idx:]
    
    X_train = train_df[feature_cols].fillna(0)
    y_train = train_df['target_return']
    X_test = test_df[feature_cols].fillna(0)
    y_test = test_df['target_return']
    
    scaler = StandardScaler()
    X_train = pd.DataFrame(scaler.fit_transform(X_train), columns=feature_cols, index=X_train.index)
    X_test = pd.DataFrame(scaler.transform(X_test), columns=feature_cols, index=X_test.index)
    
    return X_train, X_test, y_train, y_test


def evaluate(y_true, y_pred):
    """Calculate metrics"""
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    dir_acc = np.mean(np.sign(y_true) == np.sign(y_pred)) * 100
    return {'MAE': mae, 'R2': r2, 'DirectionalAccuracy': dir_acc}


def main():
    logger.info("="*80)
    logger.info("QUICK FIX - ANTI-OVERFITTING PARAMETERS")
    logger.info("="*80)
    
    # Load data
    logger.info("\nLoading data...")
    X_train, X_test, y_train, y_test = load_and_prepare_data()
    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")
    
    results = []
    
    # XGBoost - SIMPLIFIED (anti-overfitting)
    logger.info("\n" + "-"*80)
    logger.info("Training XGBoost (simplified, anti-overfitting)...")
    logger.info("-"*80)
    
    xgb_params = {
        'max_depth': 3,              # REDUCED from 6
        'learning_rate': 0.01,       # REDUCED from 0.05
        'n_estimators': 100,         # REDUCED from 500
        'subsample': 0.6,            # REDUCED from 0.8
        'colsample_bytree': 0.6,     # REDUCED from 0.8
        'reg_alpha': 1.0,            # INCREASED (L1 regularization)
        'reg_lambda': 2.0,           # INCREASED (L2 regularization)
        'min_child_weight': 10,      # INCREASED (more samples per leaf)
        'gamma': 0.5,                # INCREASED (min loss reduction)
        'random_state': 42
    }
    
    logger.info("Parameters:")
    for k, v in xgb_params.items():
        logger.info(f"  {k}: {v}")
    
    xgb_model = xgb.XGBRegressor(**xgb_params)
    xgb_model.fit(X_train, y_train)
    
    train_metrics = evaluate(y_train, xgb_model.predict(X_train))
    test_metrics = evaluate(y_test, xgb_model.predict(X_test))
    
    logger.info(f"\nXGBoost Results:")
    logger.info(f"  Train - R²: {train_metrics['R2']:.4f}, MAE: {train_metrics['MAE']:.6f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Test  - R²: {test_metrics['R2']:.4f}, MAE: {test_metrics['MAE']:.6f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Overfitting Gap (Train R² - Test R²): {train_metrics['R2'] - test_metrics['R2']:.4f}")
    
    results.append({'Model': 'XGBoost_Simplified', **{f'Train_{k}': v for k, v in train_metrics.items()}, 
                   **{f'Test_{k}': v for k, v in test_metrics.items()}})
    
    # CatBoost - SIMPLIFIED
    logger.info("\n" + "-"*80)
    logger.info("Training CatBoost (simplified, anti-overfitting)...")
    logger.info("-"*80)
    
    cb_params = {
        'iterations': 100,           # REDUCED from 500
        'learning_rate': 0.01,       # REDUCED from 0.05
        'depth': 3,                  # REDUCED from 6
        'l2_leaf_reg': 5,            # INCREASED (regularization)
        'min_data_in_leaf': 50,      # INCREASED (more samples per leaf)
        'random_strength': 0.2,      # REDUCED (less randomness)
        'bagging_temperature': 0.2,  # REDUCED
        'random_seed': 42,
        'verbose': False
    }
    
    logger.info("Parameters:")
    for k, v in cb_params.items():
        logger.info(f"  {k}: {v}")
    
    cb_model = CatBoostRegressor(**cb_params)
    cb_model.fit(X_train, y_train, verbose=False)
    
    train_metrics = evaluate(y_train, cb_model.predict(X_train))
    test_metrics = evaluate(y_test, cb_model.predict(X_test))
    
    logger.info(f"\nCatBoost Results:")
    logger.info(f"  Train - R²: {train_metrics['R2']:.4f}, MAE: {train_metrics['MAE']:.6f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Test  - R²: {test_metrics['R2']:.4f}, MAE: {test_metrics['MAE']:.6f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Overfitting Gap: {train_metrics['R2'] - test_metrics['R2']:.4f}")
    
    results.append({'Model': 'CatBoost_Simplified', **{f'Train_{k}': v for k, v in train_metrics.items()}, 
                   **{f'Test_{k}': v for k, v in test_metrics.items()}})
    
    # LightGBM - SIMPLIFIED
    logger.info("\n" + "-"*80)
    logger.info("Training LightGBM (simplified, anti-overfitting)...")
    logger.info("-"*80)
    
    lgb_params = {
        'num_leaves': 8,             # REDUCED from 31
        'learning_rate': 0.01,       # REDUCED from 0.05
        'n_estimators': 100,         # REDUCED from 500
        'max_depth': 3,              # REDUCED from 6
        'min_child_samples': 50,     # INCREASED
        'subsample': 0.6,            # REDUCED from 0.8
        'colsample_bytree': 0.6,     # REDUCED from 0.8
        'reg_alpha': 1.0,            # INCREASED
        'reg_lambda': 2.0,           # INCREASED
        'random_state': 42,
        'verbose': -1
    }
    
    logger.info("Parameters:")
    for k, v in lgb_params.items():
        logger.info(f"  {k}: {v}")
    
    lgb_model = lgb.LGBMRegressor(**lgb_params)
    lgb_model.fit(X_train, y_train)
    
    train_metrics = evaluate(y_train, lgb_model.predict(X_train))
    test_metrics = evaluate(y_test, lgb_model.predict(X_test))
    
    logger.info(f"\nLightGBM Results:")
    logger.info(f"  Train - R²: {train_metrics['R2']:.4f}, MAE: {train_metrics['MAE']:.6f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Test  - R²: {test_metrics['R2']:.4f}, MAE: {test_metrics['MAE']:.6f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
    logger.info(f"  Overfitting Gap: {train_metrics['R2'] - test_metrics['R2']:.4f}")
    
    results.append({'Model': 'LightGBM_Simplified', **{f'Train_{k}': v for k, v in train_metrics.items()}, 
                   **{f'Test_{k}': v for k, v in test_metrics.items()}})
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY - SIMPLIFIED MODELS")
    logger.info("="*80)
    
    results_df = pd.DataFrame(results).sort_values('Test_R2', ascending=False)
    
    logger.info(f"\n{'Model':<25} {'Train R²':>10} {'Test R²':>10} {'Gap':>10} {'Test Dir.Acc':>15}")
    logger.info("-" * 80)
    
    for _, row in results_df.iterrows():
        gap = row['Train_R2'] - row['Test_R2']
        logger.info(
            f"{row['Model']:<25} "
            f"{row['Train_R2']:>10.4f} "
            f"{row['Test_R2']:>10.4f} "
            f"{gap:>10.4f} "
            f"{row['Test_DirectionalAccuracy']:>14.2f}%"
        )
    
    # Save results
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'simplified_models_{timestamp}.csv'
    results_df.to_csv(output_file, index=False)
    
    logger.info(f"\n💾 Results saved to: {output_file}")
    
    # Best model
    best = results_df.iloc[0]
    logger.info(f"\n🏆 Best Model: {best['Model']}")
    logger.info(f"   Test R²: {best['Test_R2']:.4f}")
    logger.info(f"   Test MAE: {best['Test_MAE']:.6f}")
    logger.info(f"   Directional Accuracy: {best['Test_DirectionalAccuracy']:.2f}%")
    logger.info(f"   Overfitting Gap: {best['Train_R2'] - best['Test_R2']:.4f}")
    
    logger.info("\n" + "="*80)
    logger.info("✅ QUICK FIX COMPLETE!")
    logger.info("="*80)
    logger.info("\nNext steps:")
    logger.info("1. Compare with previous results (ensemble_results_20251030_215015.csv)")
    logger.info("2. If improved, run: python hyperparameter_tuning.py")
    logger.info("3. Add news sentiment features for major improvement")


if __name__ == "__main__":
    main()
