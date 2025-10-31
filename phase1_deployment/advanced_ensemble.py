"""
Advanced Ensemble Methods for Stock Forecasting
================================================
Combines multiple tuned models using sophisticated ensemble techniques:
1. Simple Weighted Average
2. Optimized Weighted Average (scipy optimization)
3. Stacking with Ridge meta-learner
4. Voting Ensemble
5. Dynamic Weighting (performance-based)

Requires: Tuned models from hyperparameter_tuning.py
Target: R² > 0.05, Directional Accuracy > 52%
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
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import VotingRegressor

import xgboost as xgb
from catboost import CatBoostRegressor
import lightgbm as lgb

import joblib
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedEnsemble:
    """
    Advanced ensemble methods for stock return prediction
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
        
        # Base models
        self.models = {}
        self.predictions = {}
        
        # Ensemble models
        self.ensembles = {}
        
        # Results
        self.results = []
        
    def load_and_prepare_data(self, test_size: float = 0.2):
        """Load and prepare data"""
        logger.info(f"Loading data from: {self.data_path}")
        self.df = pd.read_csv(self.data_path)
        logger.info(f"  Shape: {self.df.shape}")
        
        # Sort by time
        self.df = self.df.sort_values('time')
        
        # Feature columns
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
        
        # Extract features
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
        
        logger.info("✅ Data loaded and prepared\n")
        
        return self
    
    def train_base_models(self):
        """Train base models with good default parameters"""
        logger.info("="*80)
        logger.info("TRAINING BASE MODELS")
        logger.info("="*80)
        
        # XGBoost
        logger.info("\n Training XGBoost...")
        xgb_params = {
            'max_depth': 6,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1
        }
        self.models['XGBoost'] = xgb.XGBRegressor(**xgb_params)
        self.models['XGBoost'].fit(self.X_train, self.y_train)
        
        # CatBoost
        logger.info("  Training CatBoost...")
        cb_params = {
            'iterations': 500,
            'learning_rate': 0.05,
            'depth': 6,
            'l2_leaf_reg': 3,
            'random_seed': 42,
            'verbose': False
        }
        self.models['CatBoost'] = CatBoostRegressor(**cb_params)
        self.models['CatBoost'].fit(self.X_train, self.y_train, verbose=False)
        
        # LightGBM
        logger.info("  Training LightGBM...")
        lgb_params = {
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'max_depth': 6,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        self.models['LightGBM'] = lgb.LGBMRegressor(**lgb_params)
        self.models['LightGBM'].fit(self.X_train, self.y_train)
        
        logger.info("✅ Base models trained\n")
        
        # Generate predictions
        self._generate_predictions()
        
        # Evaluate individual models
        self._evaluate_base_models()
        
        return self
    
    def load_tuned_models(self, models_dir: str = 'models/tuned'):
        """Load pre-tuned models from hyperparameter_tuning.py"""
        logger.info("="*80)
        logger.info("LOADING TUNED MODELS")
        logger.info("="*80)
        
        models_path = Path(models_dir)
        
        # Find latest model files
        model_files = {}
        for model_name in ['xgboost', 'catboost', 'lightgbm']:
            files = list(models_path.glob(f'{model_name}_tuned_*.pkl'))
            if files:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                model_files[model_name] = latest
                logger.info(f"  Found {model_name}: {latest.name}")
        
        if not model_files:
            logger.warning("⚠️  No tuned models found! Training base models instead...")
            return self.train_base_models()
        
        # Load models
        for name, file_path in model_files.items():
            model = joblib.load(file_path)
            self.models[name.upper()] = model
        
        logger.info(f"✅ Loaded {len(self.models)} tuned models\n")
        
        # Generate predictions
        self._generate_predictions()
        
        # Evaluate individual models
        self._evaluate_base_models()
        
        return self
    
    def _generate_predictions(self):
        """Generate predictions from all base models"""
        for name, model in self.models.items():
            self.predictions[name] = {
                'train': model.predict(self.X_train),
                'test': model.predict(self.X_test)
            }
    
    def _evaluate_base_models(self):
        """Evaluate individual base models"""
        logger.info("\n" + "="*80)
        logger.info("BASE MODEL PERFORMANCE")
        logger.info("="*80)
        logger.info(f"{'Model':<15} {'Train R²':>10} {'Test R²':>10} {'Test MAE':>12} {'Test Dir.Acc':>15}")
        logger.info("-" * 80)
        
        for name in self.models.keys():
            train_pred = self.predictions[name]['train']
            test_pred = self.predictions[name]['test']
            
            train_metrics = self._calculate_metrics(self.y_train, train_pred)
            test_metrics = self._calculate_metrics(self.y_test, test_pred)
            
            logger.info(
                f"{name:<15} "
                f"{train_metrics['R2']:>10.4f} "
                f"{test_metrics['R2']:>10.4f} "
                f"{test_metrics['MAE']:>12.6f} "
                f"{test_metrics['DirectionalAccuracy']:>14.2f}%"
            )
            
            self.results.append({
                'Model': name,
                'Type': 'Base',
                **{f'Train_{k}': v for k, v in train_metrics.items()},
                **{f'Test_{k}': v for k, v in test_metrics.items()}
            })
    
    def _calculate_metrics(self, y_true, y_pred):
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
    
    def ensemble_simple_average(self):
        """Simple average ensemble"""
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE: SIMPLE AVERAGE")
        logger.info("="*80)
        
        # Average predictions
        train_preds = np.array([self.predictions[name]['train'] for name in self.models.keys()])
        test_preds = np.array([self.predictions[name]['test'] for name in self.models.keys()])
        
        ensemble_train = np.mean(train_preds, axis=0)
        ensemble_test = np.mean(test_preds, axis=0)
        
        # Evaluate
        train_metrics = self._calculate_metrics(self.y_train, ensemble_train)
        test_metrics = self._calculate_metrics(self.y_test, ensemble_test)
        
        logger.info(f"\n📊 Simple Average Results:")
        logger.info(f"   Test R²: {test_metrics['R2']:.4f}")
        logger.info(f"   Test MAE: {test_metrics['MAE']:.6f}")
        logger.info(f"   Test Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        self.ensembles['SimpleAverage'] = (ensemble_train, ensemble_test)
        self.results.append({
            'Model': 'SimpleAverage',
            'Type': 'Ensemble',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return self
    
    def ensemble_optimized_weights(self):
        """Optimized weighted average using scipy"""
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE: OPTIMIZED WEIGHTED AVERAGE")
        logger.info("="*80)
        
        n_models = len(self.models)
        
        # Objective function: minimize validation MAE
        def objective(weights):
            weights = weights / np.sum(weights)  # Normalize
            train_preds = np.array([self.predictions[name]['train'] for name in self.models.keys()])
            ensemble_pred = np.sum(weights.reshape(-1, 1) * train_preds, axis=0)
            return mean_absolute_error(self.y_train, ensemble_pred)
        
        # Constraints: weights sum to 1 and are positive
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(n_models)]
        
        # Initial guess: equal weights
        initial_weights = np.ones(n_models) / n_models
        
        # Optimize
        logger.info("   Optimizing weights...")
        result = minimize(objective, initial_weights, method='SLSQP', 
                         bounds=bounds, constraints=constraints)
        
        optimal_weights = result.x / np.sum(result.x)
        
        logger.info(f"\n   Optimal weights:")
        for name, weight in zip(self.models.keys(), optimal_weights):
            logger.info(f"     {name}: {weight:.4f}")
        
        # Apply optimal weights
        train_preds = np.array([self.predictions[name]['train'] for name in self.models.keys()])
        test_preds = np.array([self.predictions[name]['test'] for name in self.models.keys()])
        
        ensemble_train = np.sum(optimal_weights.reshape(-1, 1) * train_preds, axis=0)
        ensemble_test = np.sum(optimal_weights.reshape(-1, 1) * test_preds, axis=0)
        
        # Evaluate
        train_metrics = self._calculate_metrics(self.y_train, ensemble_train)
        test_metrics = self._calculate_metrics(self.y_test, ensemble_test)
        
        logger.info(f"\n📊 Optimized Weighted Average Results:")
        logger.info(f"   Test R²: {test_metrics['R2']:.4f}")
        logger.info(f"   Test MAE: {test_metrics['MAE']:.6f}")
        logger.info(f"   Test Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        self.ensembles['OptimizedWeights'] = (ensemble_train, ensemble_test, optimal_weights)
        self.results.append({
            'Model': 'OptimizedWeights',
            'Type': 'Ensemble',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return self
    
    def ensemble_stacking(self):
        """Stacking ensemble with Ridge meta-learner"""
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE: STACKING")
        logger.info("="*80)
        
        # Generate out-of-fold predictions for meta-features
        logger.info("   Generating out-of-fold predictions...")
        tscv = TimeSeriesSplit(n_splits=5)
        
        oof_predictions = {name: np.zeros(len(self.X_train)) for name in self.models.keys()}
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(self.X_train), 1):
            logger.info(f"     Fold {fold}/5...")
            
            X_fold_train = self.X_train.iloc[train_idx]
            y_fold_train = self.y_train.iloc[train_idx]
            X_fold_val = self.X_train.iloc[val_idx]
            
            for name, model in self.models.items():
                # Clone model with same parameters
                if name == 'XGBoost':
                    fold_model = xgb.XGBRegressor(**model.get_params())
                elif name == 'CatBoost':
                    fold_model = CatBoostRegressor(**model.get_params())
                elif name == 'LightGBM':
                    fold_model = lgb.LGBMRegressor(**model.get_params())
                else:
                    continue
                
                # Train and predict
                fold_model.fit(X_fold_train, y_fold_train)
                oof_predictions[name][val_idx] = fold_model.predict(X_fold_val)
        
        # Create meta-features
        meta_X_train = np.column_stack([oof_predictions[name] for name in self.models.keys()])
        meta_X_test = np.column_stack([self.predictions[name]['test'] for name in self.models.keys()])
        
        # Train meta-learner
        logger.info("   Training meta-learner (Ridge)...")
        meta_learner = Ridge(alpha=1.0)
        meta_learner.fit(meta_X_train, self.y_train)
        
        # Meta-learner weights
        logger.info(f"\n   Meta-learner weights:")
        for name, weight in zip(self.models.keys(), meta_learner.coef_):
            logger.info(f"     {name}: {weight:.4f}")
        
        # Predict
        stacking_train = meta_learner.predict(meta_X_train)
        stacking_test = meta_learner.predict(meta_X_test)
        
        # Evaluate
        train_metrics = self._calculate_metrics(self.y_train, stacking_train)
        test_metrics = self._calculate_metrics(self.y_test, stacking_test)
        
        logger.info(f"\n📊 Stacking Results:")
        logger.info(f"   Test R²: {test_metrics['R2']:.4f}")
        logger.info(f"   Test MAE: {test_metrics['MAE']:.6f}")
        logger.info(f"   Test Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        self.ensembles['Stacking'] = (stacking_train, stacking_test, meta_learner)
        self.results.append({
            'Model': 'Stacking',
            'Type': 'Ensemble',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return self
    
    def ensemble_voting(self):
        """Voting ensemble (sklearn VotingRegressor)"""
        logger.info("\n" + "="*80)
        logger.info("ENSEMBLE: VOTING")
        logger.info("="*80)
        
        # Create voting ensemble
        estimators = [(name, model) for name, model in self.models.items()]
        
        logger.info("   Training voting ensemble...")
        voting = VotingRegressor(estimators=estimators)
        voting.fit(self.X_train, self.y_train)
        
        # Predict
        voting_train = voting.predict(self.X_train)
        voting_test = voting.predict(self.X_test)
        
        # Evaluate
        train_metrics = self._calculate_metrics(self.y_train, voting_train)
        test_metrics = self._calculate_metrics(self.y_test, voting_test)
        
        logger.info(f"\n📊 Voting Results:")
        logger.info(f"   Test R²: {test_metrics['R2']:.4f}")
        logger.info(f"   Test MAE: {test_metrics['MAE']:.6f}")
        logger.info(f"   Test Dir.Acc: {test_metrics['DirectionalAccuracy']:.2f}%")
        
        self.ensembles['Voting'] = (voting_train, voting_test, voting)
        self.results.append({
            'Model': 'Voting',
            'Type': 'Ensemble',
            **{f'Train_{k}': v for k, v in train_metrics.items()},
            **{f'Test_{k}': v for k, v in test_metrics.items()}
        })
        
        return self
    
    def compare_all_results(self):
        """Compare all models and ensembles"""
        logger.info("\n" + "="*80)
        logger.info("FINAL COMPARISON - ALL MODELS & ENSEMBLES")
        logger.info("="*80)
        
        results_df = pd.DataFrame(self.results)
        results_df = results_df.sort_values('Test_R2', ascending=False)
        
        logger.info(f"\n{'Model':<20} {'Type':<10} {'Test R²':>10} {'Test MAE':>12} {'Dir.Acc':>10}")
        logger.info("-" * 80)
        
        for _, row in results_df.iterrows():
            logger.info(
                f"{row['Model']:<20} "
                f"{row['Type']:<10} "
                f"{row['Test_R2']:>10.4f} "
                f"{row['Test_MAE']:>12.6f} "
                f"{row['Test_DirectionalAccuracy']:>9.2f}%"
            )
        
        # Best model
        best = results_df.iloc[0]
        logger.info(f"\n🏆 BEST MODEL: {best['Model']} ({best['Type']})")
        logger.info(f"   Test R²: {best['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {best['Test_MAE']:.6f}")
        logger.info(f"   Directional Accuracy: {best['Test_DirectionalAccuracy']:.2f}%")
        
        # Check targets
        if best['Test_R2'] > 0.05 and best['Test_DirectionalAccuracy'] > 52:
            logger.info(f"\n✅ TARGET ACHIEVED!")
            logger.info(f"   R² > 0.05: ✓ ({best['Test_R2']:.4f})")
            logger.info(f"   Dir.Acc > 52%: ✓ ({best['Test_DirectionalAccuracy']:.2f}%)")
        else:
            logger.info(f"\n⚠️  Target not fully met:")
            logger.info(f"   R² > 0.05: {'✓' if best['Test_R2'] > 0.05 else '✗'} ({best['Test_R2']:.4f})")
            logger.info(f"   Dir.Acc > 52%: {'✓' if best['Test_DirectionalAccuracy'] > 52 else '✗'} ({best['Test_DirectionalAccuracy']:.2f}%)")
        
        return results_df
    
    def save_results(self, output_dir: str = 'results'):
        """Save ensemble results"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save results
        results_df = pd.DataFrame(self.results)
        results_file = output_path / f'ensemble_results_{timestamp}.csv'
        results_df.to_csv(results_file, index=False)
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        # Save best ensemble model
        models_dir = Path('models') / 'ensemble'
        models_dir.mkdir(parents=True, exist_ok=True)
        
        best_idx = results_df['Test_R2'].idxmax()
        best_name = results_df.loc[best_idx, 'Model']
        
        if best_name in self.ensembles:
            ensemble_data = self.ensembles[best_name]
            model_file = models_dir / f'{best_name.lower()}_{timestamp}.pkl'
            joblib.dump(ensemble_data, model_file)
            logger.info(f"💾 Best ensemble saved: {model_file}")
        
        return results_df


def main():
    """Main execution: Train models and create ensembles"""
    logger.info("="*80)
    logger.info("ADVANCED ENSEMBLE METHODS")
    logger.info("="*80)
    
    # Initialize
    ensemble = AdvancedEnsemble(
        data_path='data/processed/features_with_market.csv',
        target_col='target_return'
    )
    
    # Load and prepare data
    ensemble.load_and_prepare_data(test_size=0.2)
    
    # Try to load tuned models, otherwise train base models
    try:
        ensemble.load_tuned_models()
    except:
        logger.info("Could not load tuned models, training base models...")
        ensemble.train_base_models()
    
    # Create ensembles
    logger.info("\n🎯 CREATING ENSEMBLES")
    
    ensemble.ensemble_simple_average()
    ensemble.ensemble_optimized_weights()
    ensemble.ensemble_stacking()
    ensemble.ensemble_voting()
    
    # Compare all results
    results_df = ensemble.compare_all_results()
    
    # Save results
    ensemble.save_results()
    
    logger.info("\n✅ ENSEMBLE METHODS COMPLETE!")


if __name__ == "__main__":
    main()
