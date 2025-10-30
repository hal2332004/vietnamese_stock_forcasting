"""
Feature Selection - Remove Low-Importance Features
===================================================
Analyze feature importance from CatBoost/LightGBM and select top features

Strategy:
1. Train CatBoost and LightGBM on full feature set
2. Extract feature importance from both models
3. Combine importance scores (average rank)
4. Keep only top N most important features
5. Save reduced feature set

Target: Reduce from 98 features to ~50-60 most important features
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error

from catboost import CatBoostRegressor
import lightgbm as lgb

import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureSelector:
    """
    Select most important features using ML models
    """
    
    def __init__(self, data_path: str, target_col: str = 'target_return'):
        """
        Initialize selector
        
        Args:
            data_path: Path to features CSV
            target_col: Target column name
        """
        self.data_path = Path(data_path)
        self.target_col = target_col
        self.df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = []
        self.scaler = StandardScaler()
        self.catboost_importance = None
        self.lightgbm_importance = None
        self.combined_importance = None
        
    def load_data(self):
        """Load and prepare data"""
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"  Loaded: {self.df.shape}")
        
        return self
    
    def prepare_data(self, test_size: float = 0.2):
        """Prepare train/test split"""
        logger.info(f"\nPreparing data (test_size={test_size})...")
        
        # Sort by time
        self.df = self.df.sort_values('time')
        
        # Metadata columns
        metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        
        # Feature columns
        feature_cols = [c for c in self.df.columns 
                       if c not in metadata_cols and c != self.target_col]
        
        self.feature_names = feature_cols
        logger.info(f"  Total features: {len(feature_cols)}")
        
        # Remove NaN targets
        df_clean = self.df.dropna(subset=[self.target_col])
        
        # Time-based split
        split_idx = int(len(df_clean) * (1 - test_size))
        train_df = df_clean.iloc[:split_idx]
        test_df = df_clean.iloc[split_idx:]
        
        logger.info(f"  Train: {len(train_df)} rows")
        logger.info(f"  Test:  {len(test_df)} rows")
        
        # Extract features and target
        self.X_train = train_df[feature_cols]
        self.y_train = train_df[self.target_col]
        self.X_test = test_df[feature_cols]
        self.y_test = test_df[self.target_col]
        
        # Handle NaN
        self.X_train = self.X_train.fillna(method='ffill').fillna(method='bfill').fillna(0)
        self.X_test = self.X_test.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Scale
        self.X_train = pd.DataFrame(
            self.scaler.fit_transform(self.X_train),
            columns=feature_cols,
            index=self.X_train.index
        )
        self.X_test = pd.DataFrame(
            self.scaler.transform(self.X_test),
            columns=feature_cols,
            index=self.X_test.index
        )
        
        logger.info("✅ Data preparation complete")
        
        return self
    
    def train_catboost_for_importance(self):
        """Train CatBoost to extract feature importance"""
        logger.info("\n" + "="*80)
        logger.info("TRAINING CATBOOST FOR FEATURE IMPORTANCE")
        logger.info("="*80)
        
        model = CatBoostRegressor(
            iterations=300,
            learning_rate=0.05,
            depth=6,
            l2_leaf_reg=3,
            random_seed=42,
            verbose=False
        )
        
        model.fit(self.X_train, self.y_train)
        
        # Get feature importance
        importance = model.get_feature_importance()
        
        self.catboost_importance = pd.DataFrame({
            'feature': self.feature_names,
            'catboost_importance': importance
        }).sort_values('catboost_importance', ascending=False)
        
        # Evaluate
        y_pred = model.predict(self.X_test)
        r2 = r2_score(self.y_test, y_pred)
        mae = mean_absolute_error(self.y_test, y_pred)
        
        logger.info(f"✅ CatBoost trained: R²={r2:.4f}, MAE={mae:.4f}")
        
        return self
    
    def train_lightgbm_for_importance(self):
        """Train LightGBM to extract feature importance"""
        logger.info("\n" + "="*80)
        logger.info("TRAINING LIGHTGBM FOR FEATURE IMPORTANCE")
        logger.info("="*80)
        
        model = lgb.LGBMRegressor(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            max_depth=6,
            random_state=42,
            verbose=-1
        )
        
        model.fit(self.X_train, self.y_train)
        
        # Get feature importance
        importance = model.feature_importances_
        
        self.lightgbm_importance = pd.DataFrame({
            'feature': self.feature_names,
            'lightgbm_importance': importance
        }).sort_values('lightgbm_importance', ascending=False)
        
        # Evaluate
        y_pred = model.predict(self.X_test)
        r2 = r2_score(self.y_test, y_pred)
        mae = mean_absolute_error(self.y_test, y_pred)
        
        logger.info(f"✅ LightGBM trained: R²={r2:.4f}, MAE={mae:.4f}")
        
        return self
    
    def combine_importance(self):
        """Combine importance from both models using rank average"""
        logger.info("\n" + "="*80)
        logger.info("COMBINING FEATURE IMPORTANCE")
        logger.info("="*80)
        
        # Add rank columns
        self.catboost_importance['catboost_rank'] = range(1, len(self.catboost_importance) + 1)
        self.lightgbm_importance['lightgbm_rank'] = range(1, len(self.lightgbm_importance) + 1)
        
        # Merge
        combined = self.catboost_importance.merge(
            self.lightgbm_importance,
            on='feature',
            how='outer'
        )
        
        # Calculate average rank (lower is better)
        combined['avg_rank'] = (combined['catboost_rank'] + combined['lightgbm_rank']) / 2
        
        # Calculate combined importance score (normalized average)
        # Normalize each importance to 0-1 scale
        combined['catboost_norm'] = (
            combined['catboost_importance'] / combined['catboost_importance'].max()
        )
        combined['lightgbm_norm'] = (
            combined['lightgbm_importance'] / combined['lightgbm_importance'].max()
        )
        combined['combined_score'] = (combined['catboost_norm'] + combined['lightgbm_norm']) / 2
        
        # Sort by combined score
        combined = combined.sort_values('combined_score', ascending=False)
        
        self.combined_importance = combined
        
        logger.info(f"✅ Combined importance calculated for {len(combined)} features")
        
        return self
    
    def select_top_features(self, n_features: int = 60, min_score: float = 0.01):
        """
        Select top N features or features above minimum score
        
        Args:
            n_features: Maximum number of features to keep
            min_score: Minimum combined score (0-1 scale)
        """
        logger.info("\n" + "="*80)
        logger.info("SELECTING TOP FEATURES")
        logger.info("="*80)
        
        # Method 1: Top N features
        top_n = self.combined_importance.head(n_features)
        
        # Method 2: Features above min score
        above_threshold = self.combined_importance[
            self.combined_importance['combined_score'] >= min_score
        ]
        
        # Use the more conservative approach (fewer features)
        selected = top_n if len(top_n) <= len(above_threshold) else above_threshold
        
        logger.info(f"  Top {n_features} features: {len(top_n)}")
        logger.info(f"  Above threshold ({min_score}): {len(above_threshold)}")
        logger.info(f"  📌 Selected: {len(selected)} features")
        
        # Log top 30
        logger.info(f"\n🔍 Top 30 Selected Features:")
        for idx, row in selected.head(30).iterrows():
            logger.info(
                f"  {row['feature']:50s} | "
                f"CB:{row['catboost_importance']:8.2f} | "
                f"LGB:{row['lightgbm_importance']:8.2f} | "
                f"Score:{row['combined_score']:.4f}"
            )
        
        return selected['feature'].tolist()
    
    def save_selected_features(self, selected_features: list, output_path: str):
        """
        Save dataset with only selected features
        
        Args:
            selected_features: List of feature names to keep
            output_path: Output CSV path
        """
        logger.info("\n" + "="*80)
        logger.info("SAVING SELECTED FEATURE DATASET")
        logger.info("="*80)
        
        # Metadata + selected features + target
        metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        
        keep_cols = metadata_cols + selected_features + [self.target_col]
        
        # Filter columns that exist in df
        keep_cols = [c for c in keep_cols if c in self.df.columns]
        
        df_selected = self.df[keep_cols]
        
        # Save
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df_selected.to_csv(output_file, index=False)
        
        logger.info(f"✅ Saved selected features to: {output_file}")
        logger.info(f"   Original: {self.df.shape}")
        logger.info(f"   Selected: {df_selected.shape}")
        logger.info(f"   Features reduced: {len(self.feature_names)} → {len(selected_features)}")
        
        return df_selected
    
    def save_importance_report(self, output_dir: str = 'results'):
        """Save feature importance report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save combined importance
        importance_file = output_path / f'feature_importance_{timestamp}.csv'
        self.combined_importance.to_csv(importance_file, index=False)
        
        logger.info(f"\n💾 Feature importance report saved to: {importance_file}")


def main():
    """
    Main execution: Feature selection pipeline
    """
    logger.info("="*80)
    logger.info("FEATURE SELECTION PIPELINE")
    logger.info("="*80)
    
    # Initialize
    selector = FeatureSelector(
        data_path='data/processed/features_with_market.csv',
        target_col='target_return'
    )
    
    # Load and prepare data
    selector.load_data()
    selector.prepare_data(test_size=0.2)
    
    # Train models to get feature importance
    selector.train_catboost_for_importance()
    selector.train_lightgbm_for_importance()
    
    # Combine importance
    selector.combine_importance()
    
    # Select top features (target: 50-60 features)
    selected_features = selector.select_top_features(
        n_features=60,
        min_score=0.01
    )
    
    # Save selected feature dataset
    selector.save_selected_features(
        selected_features=selected_features,
        output_path='data/processed/features_selected.csv'
    )
    
    # Save importance report
    selector.save_importance_report()
    
    logger.info("\n✅ Feature selection complete!")


if __name__ == "__main__":
    main()
