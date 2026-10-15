import os
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

def train_and_evaluate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, 'dataset', 'vehicle_service_data.csv')
    model_dir = os.path.join(base_dir, 'ml', 'saved_models')
    img_dir = os.path.join(base_dir, 'static', 'img')
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    # 1. Load data
    if not os.path.exists(dataset_path):
        from generate_dataset import generate_dataset
        generate_dataset(output_path=dataset_path)

    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

    feature_cols = [
        'vehicle_age_years', 'mileage_km', 'days_since_last_service',
        'service_frequency_per_year', 'avg_service_cost', 'major_repairs_count',
        'breakdown_history_count', 'fuel_type'
    ]
    target_col = 'breakdown_risk'

    X = df[feature_cols]
    y = df[target_col]

    # Preprocessing
    num_features = [
        'vehicle_age_years', 'mileage_km', 'days_since_last_service',
        'service_frequency_per_year', 'avg_service_cost', 'major_repairs_count',
        'breakdown_history_count'
    ]
    cat_features = ['fuel_type']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), cat_features)
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Candidate 1: Logistic Regression
    lr_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(random_state=42, max_iter=1000))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_preds = lr_pipeline.predict(X_test)
    lr_probs = lr_pipeline.predict_proba(X_test)[:, 1]

    lr_metrics = {
        'model_name': 'Logistic Regression',
        'accuracy': round(float(accuracy_score(y_test, lr_preds)), 4),
        'precision': round(float(precision_score(y_test, lr_preds)), 4),
        'recall': round(float(recall_score(y_test, lr_preds)), 4),
        'f1_score': round(float(f1_score(y_test, lr_preds)), 4),
        'roc_auc': round(float(roc_auc_score(y_test, lr_probs)), 4),
        'confusion_matrix': confusion_matrix(y_test, lr_preds).tolist()
    }

    # Candidate 2: Random Forest Classifier
    rf_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42))
    ])
    rf_pipeline.fit(X_train, y_train)
    rf_preds = rf_pipeline.predict(X_test)
    rf_probs = rf_pipeline.predict_proba(X_test)[:, 1]

    rf_metrics = {
        'model_name': 'Random Forest Classifier',
        'accuracy': round(float(accuracy_score(y_test, rf_preds)), 4),
        'precision': round(float(precision_score(y_test, rf_preds)), 4),
        'recall': round(float(recall_score(y_test, rf_preds)), 4),
        'f1_score': round(float(f1_score(y_test, rf_preds)), 4),
        'roc_auc': round(float(roc_auc_score(y_test, rf_probs)), 4),
        'confusion_matrix': confusion_matrix(y_test, rf_preds).tolist()
    }

    # Compare and choose the best model by F1 Score
    best_model_name = "Random Forest" if rf_metrics['f1_score'] >= lr_metrics['f1_score'] else "Logistic Regression"
    best_pipeline = rf_pipeline if best_model_name == "Random Forest" else lr_pipeline

    # Extract feature importances if Random Forest
    rf_model = rf_pipeline.named_steps['classifier']
    onehot_cols = rf_pipeline.named_steps['preprocessor'].named_transformers_['cat'].get_feature_names_out(cat_features).tolist()
    all_feature_names = num_features + onehot_cols
    importances = rf_model.feature_importances_.tolist()
    feature_importance_dict = dict(zip(all_feature_names, [round(val, 4) for val in importances]))

    # Save best model
    model_save_path = os.path.join(model_dir, 'breakdown_risk_model.joblib')
    joblib.dump(best_pipeline, model_save_path)

    # Save metrics JSON
    metrics_summary = {
        'best_model': best_model_name,
        'features': feature_cols,
        'comparison': {
            'logistic_regression': lr_metrics,
            'random_forest': rf_metrics
        },
        'feature_importance': feature_importance_dict,
        'test_set_size': len(y_test)
    }

    metrics_path = os.path.join(model_dir, 'model_metrics.json')
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=4)

    # Plot model comparison & confusion matrix
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Metric comparison bar chart
    metrics_names = ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']
    lr_vals = [lr_metrics['accuracy'], lr_metrics['precision'], lr_metrics['recall'], lr_metrics['f1_score'], lr_metrics['roc_auc']]
    rf_vals = [rf_metrics['accuracy'], rf_metrics['precision'], rf_metrics['recall'], rf_metrics['f1_score'], rf_metrics['roc_auc']]

    x = np.arange(len(metrics_names))
    width = 0.35

    axes[0].bar(x - width/2, lr_vals, width, label='Logistic Regression', color='#3b82f6')
    axes[0].bar(x + width/2, rf_vals, width, label='Random Forest', color='#10b981')
    axes[0].set_ylabel('Score')
    axes[0].set_title('Model Performance Comparison')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(metrics_names)
    axes[0].set_ylim(0, 1.1)
    axes[0].legend(loc='lower right')
    axes[0].grid(axis='y', linestyle='--', alpha=0.5)

    # Confusion matrix for Random Forest
    cm = np.array(rf_metrics['confusion_matrix'])
    im = axes[1].imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    axes[1].set_title(f'Random Forest Confusion Matrix (Acc: {rf_metrics["accuracy"]*100:.1f}%)')
    fig.colorbar(im, ax=axes[1])
    tick_marks = np.arange(2)
    axes[1].set_xticks(tick_marks)
    axes[1].set_yticks(tick_marks)
    axes[1].set_xticklabels(['Low Risk (0)', 'High Risk (1)'])
    axes[1].set_yticklabels(['Low Risk (0)', 'High Risk (1)'])

    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            axes[1].text(j, i, format(cm[i, j], 'd'),
                         ha="center", va="center",
                         color="white" if cm[i, j] > thresh else "black",
                         fontsize=12, fontweight='bold')

    axes[1].set_ylabel('Actual')
    axes[1].set_xlabel('Predicted')

    plt.tight_layout()
    chart_path = os.path.join(img_dir, 'model_evaluation.png')
    plt.savefig(chart_path, dpi=200)
    plt.close()

    print(f"Model saved to: {model_save_path}")
    print(f"Metrics saved to: {metrics_path}")
    print(f"Evaluation chart saved to: {chart_path}")
    print("\nSummary Results:")
    print(f"Logistic Regression F1: {lr_metrics['f1_score']}, Accuracy: {lr_metrics['accuracy']}")
    print(f"Random Forest F1: {rf_metrics['f1_score']}, Accuracy: {rf_metrics['accuracy']}")
    print(f"Selected Best Model: {best_model_name}")

if __name__ == '__main__':
    train_and_evaluate()
