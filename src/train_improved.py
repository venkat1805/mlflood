"""
Enhanced model training script with XGBoost and feature engineering
"""
import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from datetime import datetime

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)
from xgboost import XGBClassifier

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.feature_engineering import engineer_features, get_feature_importance

DATA_PATH = Path("data/sample_chennai_like_rainfall.csv")
MODEL_PATH = Path("models/baseline_random_forest.pkl")
IMPROVED_MODEL_PATH = Path("models/improved_xgboost.pkl")
FEATURES_PATH = Path("models/feature_list.txt")


def load_and_prepare_data():
    """Load data and apply feature engineering"""
    print("📊 Loading data...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Separate target
    y = df["flooded"].astype(int)
    X = df.drop(columns=["flooded"])
    
    # Apply feature engineering
    print("🔧 Engineering features...")
    X_engineered = engineer_features(X, include_lags=False)
    
    print(f"   Original features: {len(X.columns)}")
    print(f"   Engineered features: {len(X_engineered.columns)}")
    print(f"   New features: {set(X_engineered.columns) - set(X.columns)}")
    
    return X_engineered, y


def evaluate_model(model, X_test, y_test, model_name="Model"):
    """Evaluate model performance"""
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_test, y_pred_proba)
    except:
        roc_auc = 0.0
    
    print(f"\n📈 {model_name} Performance:")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   ROC-AUC:   {roc_auc:.4f}")
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc
    }


def train_baseline_rf(X, y):
    """Train baseline Random Forest model"""
    print("\n🌲 Training Baseline Random Forest...")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        random_state=42,
        class_weight="balanced"
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, "Baseline Random Forest")
    
    # Save baseline model
    joblib.dump({"model": model, "features": list(X.columns)}, MODEL_PATH)
    print(f"✅ Baseline model saved to {MODEL_PATH}")
    
    return model, metrics


def train_improved_xgboost(X, y):
    """Train improved XGBoost model"""
    print("\n🚀 Training Improved XGBoost Model...")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # XGBoost with better hyperparameters
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        eval_metric='logloss',
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum() if (y_train == 1).sum() > 0 else 1
    )
    
    # Train with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, "Improved XGBoost")
    
    # Cross-validation
    print("\n🔄 Running Cross-Validation...")
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
    print(f"   CV ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # Feature importance
    importance_df = get_feature_importance(model, X.columns)
    if importance_df is not None:
        print("\n🔝 Top 10 Most Important Features:")
        for idx, row in importance_df.head(10).iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
        
        # Save feature importance
        importance_df.to_csv("models/feature_importance.csv", index=False)
        print("\n✅ Feature importance saved to models/feature_importance.csv")
    
    # Save improved model
    joblib.dump({"model": model, "features": list(X.columns)}, IMPROVED_MODEL_PATH)
    
    # Save feature list
    with open(FEATURES_PATH, 'w') as f:
        f.write('\n'.join(X.columns))
    
    print(f"\n✅ Improved model saved to {IMPROVED_MODEL_PATH}")
    
    return model, metrics


def compare_models(baseline_metrics, improved_metrics):
    """Compare baseline and improved models"""
    print("\n" + "="*60)
    print("📊 MODEL COMPARISON")
    print("="*60)
    
    comparison = pd.DataFrame({
        "Baseline RF": baseline_metrics,
        "Improved XGBoost": improved_metrics
    })
    
    print(comparison.to_string())
    
    improvement = {
        key: improved_metrics[key] - baseline_metrics[key]
        for key in baseline_metrics.keys()
    }
    
    print("\n📈 Improvement:")
    for metric, value in improvement.items():
        sign = "+" if value >= 0 else ""
        print(f"   {metric.capitalize()}: {sign}{value:.4f} ({sign}{value*100:.2f}%)")
    
    return comparison


def main():
    """Main training function"""
    print("="*60)
    print("🎯 PHASE 2: Enhanced Model Training")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Ensure models directory exists
    Path("models").mkdir(exist_ok=True)
    
    # Load and prepare data
    X, y = load_and_prepare_data()
    
    print(f"\n📊 Dataset Info:")
    print(f"   Total samples: {len(X)}")
    print(f"   Features: {len(X.columns)}")
    print(f"   Flooded (1): {y.sum()} ({y.sum()/len(y)*100:.2f}%)")
    print(f"   Not flooded (0): {(y==0).sum()} ({(y==0).sum()/len(y)*100:.2f}%)")
    
    # Train baseline model
    baseline_model, baseline_metrics = train_baseline_rf(X, y)
    
    # Train improved model
    improved_model, improved_metrics = train_improved_xgboost(X, y)
    
    # Compare models
    comparison = compare_models(baseline_metrics, improved_metrics)
    
    print("\n" + "="*60)
    print("✅ Training Complete!")
    print("="*60)
    print(f"\nModels saved:")
    print(f"  - Baseline: {MODEL_PATH}")
    print(f"  - Improved: {IMPROVED_MODEL_PATH}")
    print(f"\nNext steps:")
    print(f"  1. Update app/main.py to use improved model")
    print(f"  2. Test predictions with new model")
    print(f"  3. Proceed with anomaly detection")


if __name__ == "__main__":
    main()

