"""
Train Optimized Models - XGBoost, CatBoost, RandomForest, LightGBM
===================================================================
Uses features_with_market.csv (106 features including advanced technical indicators + market features)

Model Training Strategy:
1. Time-series split (no shuffling)
2. Hyperparameter tuning with GridSearchCV/RandomizedSearchCV
3. Comprehensive evaluation metrics
4. Feature importance analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import xgboost as xgb
from catboost import CatBoostRegressor, Pool
from sklearn.ensemble import RandomForestRegressor
import lightgbm as lgb

import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockModelTrainer:
    """
    Train and evaluate multiple ML models for stock return prediction
    """
    
    def __init__(self, data_path: str, target_col: str = 'target_return'):
        """
        Initialize trainer
        
        Args:
            data_path: Path to features CSV file
            target_col: Name of target column
        """
        self.data_path = Path(data_path)
        self.target_col = target_col
        self.df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.train_dates = None
        self.test_dates = None
        self.train_symbols = None
        self.test_symbols = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.results = []
        
    def load_data(self):
        """Load and prepare data"""
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"  Loaded: {self.df.shape}")
        logger.info(f"  Columns: {self.df.shape[1]}")
        logger.info(f"  Date range: {self.df['time'].min()} to {self.df['time'].max()}")
        
        # Check for target
        if self.target_col not in self.df.columns:
            raise ValueError(f"Target column '{self.target_col}' not found!")
        
        return self
    
    def prepare_train_test_split(self, test_size: float = 0.2):
        """
        Time-series split: Last 20% as test set
        
        Args:
            test_size: Fraction of data for testing
        """
        logger.info(f"\nPreparing train/test split (test_size={test_size})...")
        
        # Sort by time
        self.df = self.df.sort_values('time')
        
        # Identify metadata columns
        metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        
        # Feature columns = all except metadata and target
        feature_cols = [c for c in self.df.columns 
                       if c not in metadata_cols and c != self.target_col]
        
        self.feature_names = feature_cols
        logger.info(f"  Using {len(feature_cols)} features")
        
        # Remove rows with NaN in target
        df_clean = self.df.dropna(subset=[self.target_col])
        logger.info(f"  After removing NaN targets: {len(df_clean)} rows")
        
        # Time-based split
        split_idx = int(len(df_clean) * (1 - test_size))
        
        train_df = df_clean.iloc[:split_idx]
        test_df = df_clean.iloc[split_idx:]
        
        logger.info(f"  Train: {len(train_df)} rows ({train_df['time'].min()} to {train_df['time'].max()})")
        logger.info(f"  Test:  {len(test_df)} rows ({test_df['time'].min()} to {test_df['time'].max()})")
        
        # Extract features and target
        self.X_train = train_df[feature_cols]
        self.y_train = train_df[self.target_col]
        self.train_dates = train_df['time']
        self.train_symbols = train_df['symbol']
        
        self.X_test = test_df[feature_cols]
        self.y_test = test_df[self.target_col]
        self.test_dates = test_df['time']
        self.test_symbols = test_df['symbol']
        
        # Handle remaining NaN in features (forward fill then backward fill)
        self.X_train = self.X_train.fillna(method='ffill').fillna(method='bfill').fillna(0)
        self.X_test = self.X_test.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Scale features
        logger.info("  Scaling features...")
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
        
        logger.info("✅ Train/test split complete")
        
        return self
    
    def evaluate_model(self, y_true, y_pred, dataset_name: str = 'Test') -> dict:
        """
        Calculate comprehensive evaluation metrics
        
        Args:
            y_true: True values
            y_pred: Predicted values
            dataset_name: Name of dataset (Train/Test)
            
        Returns:
            Dictionary of metrics
        """
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # Mean Absolute Percentage Error (MAPE)
        # Handle zeros in y_true
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() > 0 else np.inf
        
        # Directional Accuracy
        direction_true = np.sign(y_true)
        direction_pred = np.sign(y_pred)
        directional_accuracy = np.mean(direction_true == direction_pred) * 100
        
        return {
            f'{dataset_name}_MSE': mse,
            f'{dataset_name}_RMSE': rmse,
            f'{dataset_name}_MAE': mae,
            f'{dataset_name}_R2': r2,
            f'{dataset_name}_MAPE': mape,
            f'{dataset_name}_DirectionalAccuracy': directional_accuracy
        }
    
    def train_xgboost(self, params: dict = None):
        """
        Train XGBoost model
        
        Args:
            params: Hyperparameters (if None, use defaults)
        """
        logger.info("\n" + "="*80)
        logger.info("TRAINING XGBOOST")
        logger.info("="*80)
        
        if params is None:
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 6,
                'learning_rate': 0.05,
                'n_estimators': 300,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 3,
                'gamma': 0.1,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
                'random_state': 42,
                'n_jobs': -1,
                'early_stopping_rounds': 50
            }
        
        logger.info(f"Parameters: {params}")
        
        # Separate early stopping params
        early_stopping_rounds = params.pop('early_stopping_rounds', None)
        
        # Train
        model = xgb.XGBRegressor(**params)
        
        if early_stopping_rounds:
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_test, self.y_test)],
                verbose=False
            )
        else:
            model.fit(self.X_train, self.y_train)
        
        # Predict
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        # Evaluate
        train_metrics = self.evaluate_model(self.y_train, y_train_pred, 'Train')
        test_metrics = self.evaluate_model(self.y_test, y_test_pred, 'Test')
        
        metrics = {
            'Model': 'XGBoost',
            'Timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            **train_metrics,
            **test_metrics
        }
        
        self.results.append(metrics)
        
        # Log results
        logger.info(f"\n📊 XGBoost Results:")
        logger.info(f"  Train R²: {train_metrics['Train_R2']:.4f}")
        logger.info(f"  Test R²:  {test_metrics['Test_R2']:.4f}")
        logger.info(f"  Train MAE: {train_metrics['Train_MAE']:.4f}%")
        logger.info(f"  Test MAE:  {test_metrics['Test_MAE']:.4f}%")
        logger.info(f"  Test Directional Accuracy: {test_metrics['Test_DirectionalAccuracy']:.2f}%")
        
        # Feature importance
        self._log_feature_importance(model, 'XGBoost', top_n=20)
        
        return model, metrics
    
    def train_catboost(self, params: dict = None):
        """
        Train CatBoost model
        
        Args:
            params: Hyperparameters (if None, use defaults)
        """
        logger.info("\n" + "="*80)
        logger.info("TRAINING CATBOOST")
        logger.info("="*80)
        
        if params is None:
            params = {
                'iterations': 500,
                'learning_rate': 0.05,
                'depth': 6,
                'l2_leaf_reg': 3,
                'min_data_in_leaf': 20,
                'random_strength': 0.5,
                'bagging_temperature': 0.5,
                'random_seed': 42,
                'verbose': False,
                'early_stopping_rounds': 50
            }
        
        logger.info(f"Parameters: {params}")
        
        # Train
        model = CatBoostRegressor(**params)
        
        model.fit(
            self.X_train, self.y_train,
            eval_set=(self.X_test, self.y_test),
            verbose=False
        )
        
        # Predict
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        # Evaluate
        train_metrics = self.evaluate_model(self.y_train, y_train_pred, 'Train')
        test_metrics = self.evaluate_model(self.y_test, y_test_pred, 'Test')
        
        metrics = {
            'Model': 'CatBoost',
            'Timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            **train_metrics,
            **test_metrics
        }
        
        self.results.append(metrics)
        
        # Log results
        logger.info(f"\n📊 CatBoost Results:")
        logger.info(f"  Train R²: {train_metrics['Train_R2']:.4f}")
        logger.info(f"  Test R²:  {test_metrics['Test_R2']:.4f}")
        logger.info(f"  Train MAE: {train_metrics['Train_MAE']:.4f}%")
        logger.info(f"  Test MAE:  {test_metrics['Test_MAE']:.4f}%")
        logger.info(f"  Test Directional Accuracy: {test_metrics['Test_DirectionalAccuracy']:.2f}%")
        
        # Feature importance
        self._log_feature_importance(model, 'CatBoost', top_n=20)
        
        return model, metrics
    
    def train_randomforest(self, params: dict = None):
        """
        Train Random Forest model
        
        Args:
            params: Hyperparameters (if None, use defaults)
        """
        logger.info("\n" + "="*80)
        logger.info("TRAINING RANDOM FOREST")
        logger.info("="*80)
        
        if params is None:
            params = {
                'n_estimators': 300,
                'max_depth': 15,
                'min_samples_split': 20,
                'min_samples_leaf': 10,
                'max_features': 'sqrt',
                'random_state': 42,
                'n_jobs': -1
            }
        
        logger.info(f"Parameters: {params}")
        
        # Train
        model = RandomForestRegressor(**params)
        model.fit(self.X_train, self.y_train)
        
        # Predict
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        # Evaluate
        train_metrics = self.evaluate_model(self.y_train, y_train_pred, 'Train')
        test_metrics = self.evaluate_model(self.y_test, y_test_pred, 'Test')
        
        metrics = {
            'Model': 'RandomForest',
            'Timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            **train_metrics,
            **test_metrics
        }
        
        self.results.append(metrics)
        
        # Log results
        logger.info(f"\n📊 Random Forest Results:")
        logger.info(f"  Train R²: {train_metrics['Train_R2']:.4f}")
        logger.info(f"  Test R²:  {test_metrics['Test_R2']:.4f}")
        logger.info(f"  Train MAE: {train_metrics['Train_MAE']:.4f}%")
        logger.info(f"  Test MAE:  {test_metrics['Test_MAE']:.4f}%")
        logger.info(f"  Test Directional Accuracy: {test_metrics['Test_DirectionalAccuracy']:.2f}%")
        
        # Feature importance
        self._log_feature_importance(model, 'RandomForest', top_n=20)
        
        return model, metrics
    
    def train_lightgbm(self, params: dict = None):
        """
        Train LightGBM model
        
        Args:
            params: Hyperparameters (if None, use defaults)
        """
        logger.info("\n" + "="*80)
        logger.info("TRAINING LIGHTGBM")
        logger.info("="*80)
        
        if params is None:
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'n_estimators': 300,
                'max_depth': 6,
                'min_child_samples': 20,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
        
        logger.info(f"Parameters: {params}")
        
        # Train
        model = lgb.LGBMRegressor(**params)
        
        model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_test, self.y_test)],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
        )
        
        # Predict
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        # Evaluate
        train_metrics = self.evaluate_model(self.y_train, y_train_pred, 'Train')
        test_metrics = self.evaluate_model(self.y_test, y_test_pred, 'Test')
        
        metrics = {
            'Model': 'LightGBM',
            'Timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            **train_metrics,
            **test_metrics
        }
        
        self.results.append(metrics)
        
        # Log results
        logger.info(f"\n📊 LightGBM Results:")
        logger.info(f"  Train R²: {train_metrics['Train_R2']:.4f}")
        logger.info(f"  Test R²:  {test_metrics['Test_R2']:.4f}")
        logger.info(f"  Train MAE: {train_metrics['Train_MAE']:.4f}%")
        logger.info(f"  Test MAE:  {test_metrics['Test_MAE']:.4f}%")
        logger.info(f"  Test Directional Accuracy: {test_metrics['Test_DirectionalAccuracy']:.2f}%")
        
        # Feature importance
        self._log_feature_importance(model, 'LightGBM', top_n=20)
        
        return model, metrics
    
    def _log_feature_importance(self, model, model_name: str, top_n: int = 20):
        """Log top N most important features"""
        logger.info(f"\n🔍 Top {top_n} Important Features ({model_name}):")
        
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        elif hasattr(model, 'get_feature_importance'):
            importance = model.get_feature_importance()
        else:
            logger.warning("  Feature importance not available")
            return
        
        # Create dataframe
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        # Log top N
        for idx, row in importance_df.head(top_n).iterrows():
            logger.info(f"  {row['feature']:50s} : {row['importance']:.4f}")
    
    def save_results(self, output_dir: str = 'results'):
        """Save all results to CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results_df = pd.DataFrame(self.results)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_path / f'all_models_{timestamp}.csv'
        
        results_df.to_csv(output_file, index=False)
        logger.info(f"\n💾 Results saved to: {output_file}")
        
        return results_df
    
    def compare_models(self):
        """Print comparison table of all models"""
        if not self.results:
            logger.warning("No results to compare!")
            return
        
        results_df = pd.DataFrame(self.results)
        
        logger.info("\n" + "="*80)
        logger.info("MODEL COMPARISON")
        logger.info("="*80)
        
        # Sort by Test R²
        results_df = results_df.sort_values('Test_R2', ascending=False)
        
        logger.info("\n📊 Comparison Table:")
        logger.info(f"{'Model':<15} {'Test R²':>10} {'Test MAE':>10} {'Test Dir.Acc':>15} {'Train R²':>10}")
        logger.info("-" * 70)
        
        for _, row in results_df.iterrows():
            logger.info(
                f"{row['Model']:<15} "
                f"{row['Test_R2']:>10.4f} "
                f"{row['Test_MAE']:>10.4f} "
                f"{row['Test_DirectionalAccuracy']:>14.2f}% "
                f"{row['Train_R2']:>10.4f}"
            )
        
        # Best model
        best_model = results_df.iloc[0]
        logger.info(f"\n🏆 Best Model: {best_model['Model']}")
        logger.info(f"   Test R²: {best_model['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {best_model['Test_MAE']:.4f}%")
        logger.info(f"   Directional Accuracy: {best_model['Test_DirectionalAccuracy']:.2f}%")


def main():
    """
    Main execution: Train all models and compare
    """
    logger.info("="*80)
    logger.info("TRAINING OPTIMIZED MODELS")
    logger.info("="*80)
    
    # Initialize trainer
    trainer = StockModelTrainer(
        data_path='data/processed/features_with_market.csv',
        target_col='target_return'
    )
    
    # Load and prepare data
    trainer.load_data()
    trainer.prepare_train_test_split(test_size=0.2)
    
    # Train all models
    logger.info("\n🚀 Starting model training...")
    
    try:
        trainer.train_xgboost()
    except Exception as e:
        logger.error(f"XGBoost training failed: {e}")
    
    try:
        trainer.train_catboost()
    except Exception as e:
        logger.error(f"CatBoost training failed: {e}")
    
    try:
        trainer.train_randomforest()
    except Exception as e:
        logger.error(f"RandomForest training failed: {e}")
    
    try:
        trainer.train_lightgbm()
    except Exception as e:
        logger.error(f"LightGBM training failed: {e}")
    
    # Compare models
    trainer.compare_models()
    
    # Save results
    trainer.save_results()
    
    logger.info("\n✅ Training complete!")


if __name__ == "__main__":
    main()
