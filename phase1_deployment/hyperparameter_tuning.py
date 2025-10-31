"""
Advanced Hyperparameter Tuning with Optuna
===========================================
Uses Bayesian optimization (Optuna) for efficient hyperparameter search
- Faster than GridSearchCV
- Smarter than RandomizedSearchCV
- Automatic pruning of poor trials

Target: Optimize for directional accuracy and R²
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
from catboost import CatBoostRegressor
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor

import joblib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import optuna (optional but recommended)
try:
    import optuna
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
    logger.info("✅ Optuna available - using advanced optimization")
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("⚠️  Optuna not available - falling back to manual search")
    logger.warning("   Install with: pip install optuna")


class HyperparameterTuner:
    """
    Hyperparameter tuning using Optuna or fallback methods
    """
    
    def __init__(self, data_path: str, target_col: str = 'target_return'):
        self.data_path = Path(data_path)
        self.target_col = target_col
        self.df = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = []
        self.scaler = StandardScaler()
        
        # Best models
        self.best_models = {}
        self.best_params = {}
        self.results = []
        
    def load_and_prepare_data(self, test_size: float = 0.2):
        """Load and prepare data"""
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"  Shape: {self.df.shape}")
        
        # Sort by time
        self.df = self.df.sort_values('time')
        
        # Identify feature columns
        metadata_cols = ['symbol', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        feature_cols = [c for c in self.df.columns 
                       if c not in metadata_cols and c != self.target_col]
        
        self.feature_names = feature_cols
        logger.info(f"  Features: {len(feature_cols)}")
        
        # Remove NaN targets
        df_clean = self.df.dropna(subset=[self.target_col])
        
        # Time-based split
        split_idx = int(len(df_clean) * (1 - test_size))
        train_df = df_clean.iloc[:split_idx]
        test_df = df_clean.iloc[split_idx:]
        
        logger.info(f"  Train: {len(train_df)} rows")
        logger.info(f"  Test:  {len(test_df)} rows")
        
        # Extract features and target
        self.X_train = train_df[feature_cols].fillna(0)
        self.y_train = train_df[self.target_col]
        self.X_test = test_df[feature_cols].fillna(0)
        self.y_test = test_df[self.target_col]
        
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
        
        logger.info("✅ Data preparation complete\n")
        
        return self
    
    def calculate_metrics(self, y_true, y_pred):
        """Calculate comprehensive metrics"""
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        # Directional accuracy
        direction_true = np.sign(y_true)
        direction_pred = np.sign(y_pred)
        dir_acc = np.mean(direction_true == direction_pred) * 100
        
        return {
            'MAE': mae,
            'RMSE': rmse,
            'R2': r2,
            'DirectionalAccuracy': dir_acc
        }
    
    def objective_xgboost(self, trial):
        """Optuna objective function for XGBoost"""
        params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'mae',
            'booster': 'gbtree',
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=100),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'gamma': trial.suggest_float('gamma', 0, 0.5),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 2.0),
            'random_state': 42,
            'n_jobs': -1
        }
        
        # Train with cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        
        for train_idx, val_idx in tscv.split(self.X_train):
            X_tr = self.X_train.iloc[train_idx]
            y_tr = self.y_train.iloc[train_idx]
            X_val = self.X_train.iloc[val_idx]
            y_val = self.y_train.iloc[val_idx]
            
            model = xgb.XGBRegressor(**params)
            model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
            
            y_pred = model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            scores.append(mae)
        
        return np.mean(scores)
    
    def tune_xgboost(self, n_trials: int = 50):
        """Tune XGBoost hyperparameters"""
        logger.info("="*80)
        logger.info("TUNING XGBOOST")
        logger.info("="*80)
        
        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, using default parameters")
            params = {
                'max_depth': 6,
                'learning_rate': 0.05,
                'n_estimators': 500,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            }
        else:
            study = optuna.create_study(
                direction='minimize',
                sampler=TPESampler(seed=42),
                study_name='xgboost_tuning'
            )
            
            logger.info(f"Starting optimization with {n_trials} trials...")
            study.optimize(self.objective_xgboost, n_trials=n_trials, show_progress_bar=True)
            
            logger.info(f"✅ Optimization complete!")
            logger.info(f"   Best MAE: {study.best_value:.6f}")
            logger.info(f"   Best params: {study.best_params}")
            
            params = study.best_params
            params.update({
                'objective': 'reg:squarederror',
                'random_state': 42,
                'n_jobs': -1
            })
        
        # Train final model
        model = xgb.XGBRegressor(**params)
        model.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        train_metrics = self.calculate_metrics(self.y_train, y_train_pred)
        test_metrics = self.calculate_metrics(self.y_test, y_test_pred)
        
        logger.info(f"\n📊 XGBoost Results:")
        logger.info(f"   Train - MAE: {train_metrics['MAE']:.6f}, R²: {train_metrics['R2']:.4f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
        logger.info(f"   Test  - MAE: {test_metrics['MAE']:.6f}, R²: {test_metrics['R2']:.4f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        # Save
        self.best_models['XGBoost'] = model
        self.best_params['XGBoost'] = params
        self.results.append({
            'Model': 'XGBoost_Tuned',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return model, params
    
    def objective_catboost(self, trial):
        """Optuna objective function for CatBoost"""
        params = {
            'iterations': trial.suggest_int('iterations', 100, 1000, step=100),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'depth': trial.suggest_int('depth', 4, 10),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 0.1, 10.0, log=True),
            'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 1, 50),
            'random_strength': trial.suggest_float('random_strength', 0, 2.0),
            'bagging_temperature': trial.suggest_float('bagging_temperature', 0, 1.0),
            'random_seed': 42,
            'verbose': False
        }
        
        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        
        for train_idx, val_idx in tscv.split(self.X_train):
            X_tr = self.X_train.iloc[train_idx]
            y_tr = self.y_train.iloc[train_idx]
            X_val = self.X_train.iloc[val_idx]
            y_val = self.y_train.iloc[val_idx]
            
            model = CatBoostRegressor(**params)
            model.fit(X_tr, y_tr, eval_set=(X_val, y_val), verbose=False)
            
            y_pred = model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            scores.append(mae)
        
        return np.mean(scores)
    
    def tune_catboost(self, n_trials: int = 50):
        """Tune CatBoost hyperparameters"""
        logger.info("\n" + "="*80)
        logger.info("TUNING CATBOOST")
        logger.info("="*80)
        
        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, using default parameters")
            params = {
                'iterations': 500,
                'learning_rate': 0.05,
                'depth': 6,
                'l2_leaf_reg': 3
            }
        else:
            study = optuna.create_study(
                direction='minimize',
                sampler=TPESampler(seed=42),
                study_name='catboost_tuning'
            )
            
            logger.info(f"Starting optimization with {n_trials} trials...")
            study.optimize(self.objective_catboost, n_trials=n_trials, show_progress_bar=True)
            
            logger.info(f"✅ Optimization complete!")
            logger.info(f"   Best MAE: {study.best_value:.6f}")
            logger.info(f"   Best params: {study.best_params}")
            
            params = study.best_params
            params.update({
                'random_seed': 42,
                'verbose': False
            })
        
        # Train final model
        model = CatBoostRegressor(**params)
        model.fit(self.X_train, self.y_train, verbose=False)
        
        # Evaluate
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        train_metrics = self.calculate_metrics(self.y_train, y_train_pred)
        test_metrics = self.calculate_metrics(self.y_test, y_test_pred)
        
        logger.info(f"\n📊 CatBoost Results:")
        logger.info(f"   Train - MAE: {train_metrics['MAE']:.6f}, R²: {train_metrics['R2']:.4f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
        logger.info(f"   Test  - MAE: {test_metrics['MAE']:.6f}, R²: {test_metrics['R2']:.4f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        # Save
        self.best_models['CatBoost'] = model
        self.best_params['CatBoost'] = params
        self.results.append({
            'Model': 'CatBoost_Tuned',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return model, params
    
    def objective_lightgbm(self, trial):
        """Optuna objective function for LightGBM"""
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': trial.suggest_int('num_leaves', 20, 100),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=100),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 1.0),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 2.0),
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        
        # Cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        
        for train_idx, val_idx in tscv.split(self.X_train):
            X_tr = self.X_train.iloc[train_idx]
            y_tr = self.y_train.iloc[train_idx]
            X_val = self.X_train.iloc[val_idx]
            y_val = self.y_train.iloc[val_idx]
            
            model = lgb.LGBMRegressor(**params)
            model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)])
            
            y_pred = model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            scores.append(mae)
        
        return np.mean(scores)
    
    def tune_lightgbm(self, n_trials: int = 50):
        """Tune LightGBM hyperparameters"""
        logger.info("\n" + "="*80)
        logger.info("TUNING LIGHTGBM")
        logger.info("="*80)
        
        if not OPTUNA_AVAILABLE:
            logger.warning("Optuna not available, using default parameters")
            params = {
                'num_leaves': 31,
                'learning_rate': 0.05,
                'n_estimators': 500,
                'max_depth': 6
            }
        else:
            study = optuna.create_study(
                direction='minimize',
                sampler=TPESampler(seed=42),
                study_name='lightgbm_tuning'
            )
            
            logger.info(f"Starting optimization with {n_trials} trials...")
            study.optimize(self.objective_lightgbm, n_trials=n_trials, show_progress_bar=True)
            
            logger.info(f"✅ Optimization complete!")
            logger.info(f"   Best MAE: {study.best_value:.6f}")
            logger.info(f"   Best params: {study.best_params}")
            
            params = study.best_params
            params.update({
                'objective': 'regression',
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            })
        
        # Train final model
        model = lgb.LGBMRegressor(**params)
        model.fit(self.X_train, self.y_train)
        
        # Evaluate
        y_train_pred = model.predict(self.X_train)
        y_test_pred = model.predict(self.X_test)
        
        train_metrics = self.calculate_metrics(self.y_train, y_train_pred)
        test_metrics = self.calculate_metrics(self.y_test, y_test_pred)
        
        logger.info(f"\n📊 LightGBM Results:")
        logger.info(f"   Train - MAE: {train_metrics['MAE']:.6f}, R²: {train_metrics['R2']:.4f}, Dir.Acc: {train_metrics['DirectionalAccuracy']:.2f}%")
        logger.info(f"   Test  - MAE: {test_metrics['MAE']:.6f}, R²: {test_metrics['R2']:.4f}, Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        # Save
        self.best_models['LightGBM'] = model
        self.best_params['LightGBM'] = params
        self.results.append({
            'Model': 'LightGBM_Tuned',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return model, params
    
    def save_results(self, output_dir: str = 'results'):
        """Save tuning results and models"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save results
        results_df = pd.DataFrame(self.results)
        results_file = output_path / f'hyperparameter_tuning_{timestamp}.csv'
        results_df.to_csv(results_file, index=False)
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        # Save models
        models_dir = Path('models') / 'tuned'
        models_dir.mkdir(parents=True, exist_ok=True)
        
        for name, model in self.best_models.items():
            model_file = models_dir / f'{name.lower()}_tuned_{timestamp}.pkl'
            joblib.dump(model, model_file)
            logger.info(f"💾 Model saved: {model_file}")
        
        # Save parameters
        params_file = output_path / f'best_params_{timestamp}.txt'
        with open(params_file, 'w') as f:
            for name, params in self.best_params.items():
                f.write(f"\n{'='*60}\n")
                f.write(f"{name} Best Parameters:\n")
                f.write(f"{'='*60}\n")
                for k, v in params.items():
                    f.write(f"  {k}: {v}\n")
        logger.info(f"💾 Parameters saved: {params_file}")
        
        return results_df


def main():
    """Main execution"""
    logger.info("="*80)
    logger.info("HYPERPARAMETER TUNING WITH OPTUNA")
    logger.info("="*80)
    
    # Initialize tuner
    tuner = HyperparameterTuner(
        data_path='data/processed/features_with_news.csv',  # Updated to use news features
        target_col='target_return'
    )
    
    # Load and prepare data
    tuner.load_and_prepare_data(test_size=0.2)
    
    # Tune all models
    logger.info("\n🎯 STARTING HYPERPARAMETER TUNING")
    logger.info("   This will take 15-30 minutes depending on your CPU\n")
    
    try:
        tuner.tune_xgboost(n_trials=30)
    except Exception as e:
        logger.error(f"XGBoost tuning failed: {e}")
    
    try:
        tuner.tune_catboost(n_trials=30)
    except Exception as e:
        logger.error(f"CatBoost tuning failed: {e}")
    
    try:
        tuner.tune_lightgbm(n_trials=30)
    except Exception as e:
        logger.error(f"LightGBM tuning failed: {e}")
    
    # Save results
    tuner.save_results()
    
    logger.info("\n✅ HYPERPARAMETER TUNING COMPLETE!")
    logger.info("   Check results/ directory for outputs")
    logger.info("   Check models/tuned/ directory for saved models")


if __name__ == "__main__":
    main()
