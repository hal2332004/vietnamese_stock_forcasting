"""
Master Script - Run Complete Hyperparameter Tuning & Ensemble Pipeline
=======================================================================
Executes the full pipeline:
1. Hyperparameter tuning (optional - can skip if Optuna not installed)
2. Advanced ensemble methods
3. Model comparison and selection

Usage:
    python run_full_pipeline.py              # Run everything
    python run_full_pipeline.py --skip-tuning  # Skip tuning, use default params
    python run_full_pipeline.py --quick        # Quick run with fewer trials
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_data_files():
    """Check if required data files exist"""
    data_files = [
        'data/processed/features_with_market.csv',
        'data/processed/features_no_leakage.csv',
        'data/processed/features_selected.csv'
    ]
    
    logger.info("\n" + "="*80)
    logger.info("CHECKING DATA FILES")
    logger.info("="*80)
    
    available_files = []
    for file_path in data_files:
        path = Path(file_path)
        if path.exists():
            logger.info(f"  ✅ {file_path}")
            available_files.append(file_path)
        else:
            logger.info(f"  ❌ {file_path} - NOT FOUND")
    
    if not available_files:
        logger.error("\n❌ No data files found! Please create features first.")
        logger.error("   Run: python create_advanced_features.py")
        sys.exit(1)
    
    # Use best available file
    if 'data/processed/features_with_market.csv' in available_files:
        best_file = 'data/processed/features_with_market.csv'
    elif 'data/processed/features_selected.csv' in available_files:
        best_file = 'data/processed/features_selected.csv'
    else:
        best_file = available_files[0]
    
    logger.info(f"\n📊 Using: {best_file}")
    return best_file


def run_hyperparameter_tuning(n_trials=30):
    """Run hyperparameter tuning"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: HYPERPARAMETER TUNING")
    logger.info("="*80)
    
    try:
        import optuna
        logger.info("✅ Optuna available - using advanced optimization")
    except ImportError:
        logger.warning("⚠️  Optuna not installed - will use default parameters")
        logger.warning("   Install with: pip install optuna")
        return False
    
    try:
        from hyperparameter_tuning import main as tuning_main
        tuning_main()
        return True
    except Exception as e:
        logger.error(f"❌ Hyperparameter tuning failed: {e}")
        return False


def run_ensemble_methods():
    """Run ensemble methods"""
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: ENSEMBLE METHODS")
    logger.info("="*80)
    
    try:
        from advanced_ensemble import main as ensemble_main
        ensemble_main()
        return True
    except Exception as e:
        logger.error(f"❌ Ensemble methods failed: {e}")
        return False


def generate_summary_report():
    """Generate summary report"""
    logger.info("\n" + "="*80)
    logger.info("GENERATING SUMMARY REPORT")
    logger.info("="*80)
    
    results_dir = Path('results')
    if not results_dir.exists():
        logger.warning("No results directory found")
        return
    
    # Find latest results
    ensemble_files = list(results_dir.glob('ensemble_results_*.csv'))
    tuning_files = list(results_dir.glob('hyperparameter_tuning_*.csv'))
    
    if ensemble_files:
        latest_ensemble = max(ensemble_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"\n📊 Latest ensemble results: {latest_ensemble.name}")
        
        import pandas as pd
        df = pd.read_csv(latest_ensemble)
        
        # Best model
        best_idx = df['Test_R2'].idxmax()
        best = df.loc[best_idx]
        
        logger.info(f"\n🏆 BEST MODEL: {best['Model']}")
        logger.info(f"   Type: {best['Type']}")
        logger.info(f"   Test R²: {best['Test_R2']:.4f}")
        logger.info(f"   Test MAE: {best['Test_MAE']:.6f}")
        logger.info(f"   Directional Accuracy: {best['Test_DirectionalAccuracy']:.2f}%")
        
        # Check targets
        logger.info(f"\n🎯 TARGET CHECK:")
        logger.info(f"   R² > 0.05: {'✅' if best['Test_R2'] > 0.05 else '❌'} (Actual: {best['Test_R2']:.4f})")
        logger.info(f"   Dir.Acc > 52%: {'✅' if best['Test_DirectionalAccuracy'] > 52 else '❌'} (Actual: {best['Test_DirectionalAccuracy']:.2f}%)")
    
    if tuning_files:
        latest_tuning = max(tuning_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"\n📊 Latest tuning results: {latest_tuning.name}")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Run hyperparameter tuning and ensemble pipeline')
    parser.add_argument('--skip-tuning', action='store_true', 
                       help='Skip hyperparameter tuning (use default parameters)')
    parser.add_argument('--quick', action='store_true', 
                       help='Quick run with fewer optimization trials')
    parser.add_argument('--n-trials', type=int, default=30, 
                       help='Number of optimization trials (default: 30)')
    
    args = parser.parse_args()
    
    # Banner
    logger.info("\n" + "="*80)
    logger.info("VIETNAMESE STOCK FORECASTING")
    logger.info("Hyperparameter Tuning & Ensemble Pipeline")
    logger.info("="*80)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check data files
    data_file = check_data_files()
    
    # Phase 1: Hyperparameter tuning
    tuning_success = False
    if not args.skip_tuning:
        n_trials = 10 if args.quick else args.n_trials
        logger.info(f"\nRunning hyperparameter tuning with {n_trials} trials per model...")
        logger.info("This may take 15-30 minutes depending on your CPU")
        logger.info("Press Ctrl+C to skip to ensemble methods\n")
        
        try:
            tuning_success = run_hyperparameter_tuning(n_trials)
        except KeyboardInterrupt:
            logger.warning("\n⚠️  Hyperparameter tuning interrupted by user")
            tuning_success = False
    else:
        logger.info("\n⏭️  Skipping hyperparameter tuning (--skip-tuning flag)")
    
    # Phase 2: Ensemble methods
    logger.info("\nRunning ensemble methods...")
    ensemble_success = run_ensemble_methods()
    
    # Generate summary
    generate_summary_report()
    
    # Final status
    logger.info("\n" + "="*80)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*80)
    logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if tuning_success:
        logger.info("✅ Hyperparameter tuning: SUCCESS")
    elif not args.skip_tuning:
        logger.info("⚠️  Hyperparameter tuning: SKIPPED/FAILED (using default params)")
    
    if ensemble_success:
        logger.info("✅ Ensemble methods: SUCCESS")
    else:
        logger.info("❌ Ensemble methods: FAILED")
    
    logger.info("\n📁 Check the following directories:")
    logger.info("   - results/ : CSV files with metrics")
    logger.info("   - models/tuned/ : Tuned model files")
    logger.info("   - models/ensemble/ : Ensemble model files")
    
    return ensemble_success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
