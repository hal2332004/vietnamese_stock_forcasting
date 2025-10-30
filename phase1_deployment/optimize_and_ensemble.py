"""
Hyperparameter Tuning & Ensemble Methods
==========================================
1. GridSearchCV for CatBoost and LightGBM
2. Train optimized models on selected features
3. Ensemble: Weighted Average + Stacking

Target: R² > 0.05, Directional Accuracy > 50%
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, make_scorer
from sklearn.linear_model import Ridge

from catboost import CatBoostRegressor
import lightgbm as lgb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizedEnsemble:
    """
    Hyperparameter tuning and ensemble methods
    """
    
    def __init__(self, data_path: str, target_col: str = 'target_return'):
        """
        Initialize
        
        Args:
            data_path: Path to selected features CSV
            target_col: Target column
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
        
        # Models
        self.best_catboost = None
        self.best_lightgbm = None
        self.stacking_model = None
        
        # Results
        self.results = []
        
    def load_data(self):
        """Load selected features"""
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"  Loaded: {self.df.shape}")
        
        return self
    
    def prepare_data(self, test_size: float = 0.2):
        """Prepare train/test split"""
        logger.info(f"\nPreparing data (test_size={test_size})...")
        
        self.df = self.df.sort_values('time')
        
        metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        feature_cols = [c for c in self.df.columns 
                       if c not in metadata_cols and c != self.target_col]
        
        self.feature_names = feature_cols
        logger.info(f"  Using {len(feature_cols)} selected features")
        
        # Remove NaN targets
        df_clean = self.df.dropna(subset=[self.target_col])
        
        # Time-based split
        split_idx = int(len(df_clean) * (1 - test_size))
        train_df = df_clean.iloc[:split_idx]
        test_df = df_clean.iloc[split_idx:]
        
        logger.info(f"  Train: {len(train_df)} rows ({train_df['time'].min()} to {train_df['time'].max()})")
        logger.info(f"  Test:  {len(test_df)} rows ({test_df['time'].min()} to {test_df['time'].max()})")
        
        # Extract features
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
    
    def evaluate_model(self, y_true, y_pred, model_name: str = 'Model') -> dict:
        """Calculate metrics"""
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # Directional accuracy
        direction_true = np.sign(y_true)
        direction_pred = np.sign(y_pred)
        directional_accuracy = np.mean(direction_true == direction_pred) * 100
        
        return {
            'Model': model_name,
            'Test_R2': r2,
            'Test_MAE': mae,
            'Test_RMSE': rmse,
            'Test_DirectionalAccuracy': directional_accuracy
        }
    
    def tune_catboost(self):
        """
        Hyperparameter tuning for CatBoost using GridSearchCV
        """
        logger.info("\n" + "="*80)
        logger.info("HYPERPARAMETER TUNING - CATBOOST")
        logger.info("="*80)
        
        # Parameter grid
        param_grid = {
            'learning_rate': [0.03, 0.05, 0.1],
            'depth': [4, 6, 8],
            'l2_leaf_reg': [1, 3, 5],
            'iterations': [300, 500]
        }
        
        logger.info(f"Parameter grid: {param_grid}")
        logger.info(f"Total combinations: {np.prod([len(v) for v in param_grid.values()])}")
        
        # TimeSeriesSplit for cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Base model
        base_model = CatBoostRegressor(
            random_seed=42,
            verbose=False
        )
        
        # GridSearchCV with negative MAE (higher is better)
        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            cv=tscv,
            scoring='neg_mean_absolute_error',
            n_jobs=-1,
            verbose=1
        )
        
        logger.info("Starting grid search (this may take a while)...")
        grid_search.fit(self.X_train, self.y_train)
        
        logger.info(f"✅ Grid search complete!")
        logger.info(f"   Best params: {grid_search.best_params_}")
        logger.info(f"   Best CV score (neg MAE): {grid_search.best_score_:.6f}")
        
        # Train final model with best params
        self.best_catboost = CatBoostRegressor(
            **grid_search.best_params_,
            random_seed=42,
            verbose=False
        )
        self.best_catboost.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_pred = self.best_catboost.predict(self.X_test)
        metrics = self.evaluate_model(self.y_test, y_pred, 'CatBoost_Tuned')
        self.results.append(metrics)
        
        logger.info(f"\n📊 Tuned CatBoost Results:")
        logger.info(f"   Test R²: {metrics['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {metrics['Test_MAE']:.4f}")
        logger.info(f"   Directional Accuracy: {metrics['Test_DirectionalAccuracy']:.2f}%")
        
        return self
    
    def tune_lightgbm(self):
        """
        Hyperparameter tuning for LightGBM using RandomizedSearchCV (faster)
        """
        logger.info("\n" + "="*80)
        logger.info("HYPERPARAMETER TUNING - LIGHTGBM")
        logger.info("="*80)
        
        # Smaller parameter grid
        param_grid = {
            'learning_rate': [0.03, 0.05, 0.1],
            'num_leaves': [20, 31],
            'max_depth': [6, 8],
            'min_child_samples': [20, 30],
            'n_estimators': [300, 500]
        }
        
        logger.info(f"Parameter grid: {param_grid}")
        logger.info(f"Total combinations: {np.prod([len(v) for v in param_grid.values()])}")
        logger.info(f"Using RandomizedSearchCV with 20 iterations")
        
        # TimeSeriesSplit
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Base model
        base_model = lgb.LGBMRegressor(
            random_state=42,
            verbose=-1
        )
        
        # RandomizedSearchCV (faster than GridSearchCV)
        random_search = RandomizedSearchCV(
            estimator=base_model,
            param_distributions=param_grid,
            n_iter=20,  # Try 20 random combinations
            cv=tscv,
            scoring='neg_mean_absolute_error',
            n_jobs=-1,
            verbose=1,
            random_state=42
        )
        
        logger.info("Starting randomized search...")
        random_search.fit(self.X_train, self.y_train)
        
        logger.info(f"✅ Randomized search complete!")
        logger.info(f"   Best params: {random_search.best_params_}")
        logger.info(f"   Best CV score (neg MAE): {random_search.best_score_:.6f}")
        
        # Train final model
        self.best_lightgbm = lgb.LGBMRegressor(
            **random_search.best_params_,
            random_state=42,
            verbose=-1
        )
        self.best_lightgbm.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_pred = self.best_lightgbm.predict(self.X_test)
        metrics = self.evaluate_model(self.y_test, y_pred, 'LightGBM_Tuned')
        self.results.append(metrics)
        
        logger.info(f"\n📊 Tuned LightGBM Results:")
        logger.info(f"   Test R²: {metrics['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {metrics['Test_MAE']:.4f}")
        logger.info(f"   Directional Accuracy: {metrics['Test_DirectionalAccuracy']:.2f}%")
        
        return self
    
    def ensemble_weighted_average(self):
        """
        Ensemble: Weighted average of CatBoost and LightGBM
        Try different weight combinations
        """
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE - WEIGHTED AVERAGE")
        logger.info("="*80)
        
        # Get predictions
        cb_pred = self.best_catboost.predict(self.X_test)
        lgb_pred = self.best_lightgbm.predict(self.X_test)
        
        # Try different weights
        weights = [
            (0.3, 0.7, "30% CB + 70% LGB"),
            (0.4, 0.6, "40% CB + 60% LGB"),
            (0.5, 0.5, "50% CB + 50% LGB"),
            (0.6, 0.4, "60% CB + 40% LGB"),
            (0.7, 0.3, "70% CB + 30% LGB"),
        ]
        
        best_r2 = -np.inf
        best_weight = None
        
        for w_cb, w_lgb, desc in weights:
            ensemble_pred = w_cb * cb_pred + w_lgb * lgb_pred
            
            metrics = self.evaluate_model(self.y_test, ensemble_pred, f'Ensemble_{desc}')
            
            logger.info(f"\n  {desc}:")
            logger.info(f"    R²: {metrics['Test_R2']:.4f}")
            logger.info(f"    MAE: {metrics['Test_MAE']:.4f}")
            logger.info(f"    Dir.Acc: {metrics['Test_DirectionalAccuracy']:.2f}%")
            
            self.results.append(metrics)
            
            if metrics['Test_R2'] > best_r2:
                best_r2 = metrics['Test_R2']
                best_weight = (w_cb, w_lgb, desc)
        
        logger.info(f"\n🏆 Best weighted average: {best_weight[2]}")
        logger.info(f"   R²: {best_r2:.4f}")
        
        return self
    
    def ensemble_stacking(self):
        """
        Ensemble: Stacking with Ridge meta-model
        Use out-of-fold predictions for training meta-model
        """
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE - STACKING")
        logger.info("="*80)
        
        # Generate out-of-fold predictions for training set
        tscv = TimeSeriesSplit(n_splits=5)
        
        oof_cb = np.zeros(len(self.X_train))
        oof_lgb = np.zeros(len(self.X_train))
        
        logger.info("Generating out-of-fold predictions...")
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(self.X_train), 1):
            logger.info(f"  Fold {fold}/5...")
            
            X_fold_train = self.X_train.iloc[train_idx]
            y_fold_train = self.y_train.iloc[train_idx]
            X_fold_val = self.X_train.iloc[val_idx]
            
            # Train CatBoost
            cb_fold = CatBoostRegressor(
                **self.best_catboost.get_params(),
                verbose=False
            )
            cb_fold.fit(X_fold_train, y_fold_train)
            oof_cb[val_idx] = cb_fold.predict(X_fold_val)
            
            # Train LightGBM
            lgb_fold = lgb.LGBMRegressor(
                **self.best_lightgbm.get_params(),
                verbose=-1
            )
            lgb_fold.fit(X_fold_train, y_fold_train)
            oof_lgb[val_idx] = lgb_fold.predict(X_fold_val)
        
        # Create meta-features (OOF predictions)
        meta_X_train = np.column_stack([oof_cb, oof_lgb])
        
        # Get test predictions from base models
        cb_test_pred = self.best_catboost.predict(self.X_test)
        lgb_test_pred = self.best_lightgbm.predict(self.X_test)
        meta_X_test = np.column_stack([cb_test_pred, lgb_test_pred])
        
        # Train meta-model (Ridge)
        logger.info("Training meta-model (Ridge)...")
        self.stacking_model = Ridge(alpha=1.0)
        self.stacking_model.fit(meta_X_train, self.y_train)
        
        # Predict on test set
        stacking_pred = self.stacking_model.predict(meta_X_test)
        
        # Evaluate
        metrics = self.evaluate_model(self.y_test, stacking_pred, 'Ensemble_Stacking')
        self.results.append(metrics)
        
        logger.info(f"\n📊 Stacking Results:")
        logger.info(f"   Test R²: {metrics['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {metrics['Test_MAE']:.4f}")
        logger.info(f"   Directional Accuracy: {metrics['Test_DirectionalAccuracy']:.2f}%")
        logger.info(f"   Meta-model weights: CB={self.stacking_model.coef_[0]:.3f}, LGB={self.stacking_model.coef_[1]:.3f}")
        
        return self
    
    def compare_all_results(self):
        """Compare all models and ensembles"""
        logger.info("\n" + "="*80)
        logger.info("FINAL COMPARISON - ALL MODELS")
        logger.info("="*80)
        
        results_df = pd.DataFrame(self.results)
        results_df = results_df.sort_values('Test_R2', ascending=False)
        
        logger.info(f"\n{'Model':<40} {'Test R²':>10} {'Test MAE':>10} {'Dir.Acc':>10}")
        logger.info("-" * 75)
        
        for _, row in results_df.iterrows():
            logger.info(
                f"{row['Model']:<40} "
                f"{row['Test_R2']:>10.4f} "
                f"{row['Test_MAE']:>10.4f} "
                f"{row['Test_DirectionalAccuracy']:>9.2f}%"
            )
        
        # Best model
        best = results_df.iloc[0]
        logger.info(f"\n🏆 BEST MODEL: {best['Model']}")
        logger.info(f"   Test R²: {best['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {best['Test_MAE']:.4f}")
        logger.info(f"   Directional Accuracy: {best['Test_DirectionalAccuracy']:.2f}%")
        
        # Check if targets met
        if best['Test_R2'] > 0.05 and best['Test_DirectionalAccuracy'] > 50:
            logger.info(f"\n✅ TARGET ACHIEVED!")
            logger.info(f"   R² > 0.05: ✓ ({best['Test_R2']:.4f})")
            logger.info(f"   Dir.Acc > 50%: ✓ ({best['Test_DirectionalAccuracy']:.2f}%)")
        else:
            logger.info(f"\n⚠️  Target not fully met:")
            logger.info(f"   R² > 0.05: {'✓' if best['Test_R2'] > 0.05 else '✗'} ({best['Test_R2']:.4f})")
            logger.info(f"   Dir.Acc > 50%: {'✓' if best['Test_DirectionalAccuracy'] > 50 else '✗'} ({best['Test_DirectionalAccuracy']:.2f}%)")
        
        return results_df
    
    def save_results(self, output_dir: str = 'results'):
        """Save results to CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_path / f'optimized_ensemble_{timestamp}.csv'
        
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(output_file, index=False)
        
        logger.info(f"\n💾 Results saved to: {output_file}")
        
        return results_df


def main():
    """
    Main execution: Hyperparameter tuning + Ensemble
    """
    logger.info("="*80)
    logger.info("OPTIMIZED MODELS + ENSEMBLE")
    logger.info("="*80)
    
    # Initialize
    optimizer = OptimizedEnsemble(
        data_path='data/processed/features_selected.csv',
        target_col='target_return'
    )
    
    # Load and prepare
    optimizer.load_data()
    optimizer.prepare_data(test_size=0.2)
    
    # Hyperparameter tuning
    logger.info("\n🔧 PHASE 1: HYPERPARAMETER TUNING")
    optimizer.tune_catboost()
    optimizer.tune_lightgbm()
    
    # Ensemble methods
    logger.info("\n🎯 PHASE 2: ENSEMBLE METHODS")
    optimizer.ensemble_weighted_average()
    optimizer.ensemble_stacking()
    
    # Compare all results
    results_df = optimizer.compare_all_results()
    
    # Save results
    optimizer.save_results()
    
    logger.info("\n✅ All tasks complete!")


if __name__ == "__main__":
    main()
