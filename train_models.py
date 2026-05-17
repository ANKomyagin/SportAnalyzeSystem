import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, ConfusionMatrixDisplay

def train_and_compare():
    # 1. Load results/features.csv
    df = pd.read_csv('results/features.csv')
    
    # 2. Split data: train on first 70%, test on last 30% (time-ordered)
    # Ensure it's sorted by time
    df = df.sort_values('start_time').reset_index(drop=True)
    split_idx = int(len(df) * 0.7)
    
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    features = ['prob_1_normed', 'prob_x_normed', 'prob_2_normed', 'odds_movement_1', 'favorite_home']
    X_train = train_df[features]
    y_train = train_df['outcome']
    X_test = test_df[features]
    y_test = test_df['outcome']
    
    # 3. Train models
    # Baseline: always predict the implied favorite (argmin of close odds)
    def predict_baseline(data):
        # 0 for close_1, 1 for close_x, 2 for close_2
        odds = data[['close_1', 'close_x', 'close_2']].values
        return np.argmin(odds, axis=1)

    def predict_proba_baseline(data):
        # Baseline probabilities are the normed probabilities
        return data[['prob_1_normed', 'prob_x_normed', 'prob_2_normed']].values
        
    y_pred_base = predict_baseline(test_df)
    y_prob_base = predict_proba_baseline(test_df)
    
    # Logistic Regression
    lr = LogisticRegression(random_state=42)
    lr.fit(X_train, y_train)
    y_pred_lr = lr.predict(X_test)
    y_prob_lr = lr.predict_proba(X_test)
    
    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    y_prob_rf = rf.predict_proba(X_test)
    
    # 4. Compute metrics
    models = {
        'Baseline': (y_pred_base, y_prob_base),
        'Logistic Regression': (y_pred_lr, y_prob_lr),
        'Random Forest': (y_pred_rf, y_prob_rf)
    }
    
    results = []
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    for idx, (name, (preds, probs)) in enumerate(models.items()):
        acc = accuracy_score(y_test, preds)
        loss = log_loss(y_test, probs, labels=[0,1,2])
        cm = confusion_matrix(y_test, preds, labels=[0,1,2])
        
        results.append({
            'Model': name,
            'Accuracy': acc,
            'Log Loss': loss
        })
        
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Home', 'Draw', 'Away'])
        disp.plot(ax=axes[idx], cmap='Blues', values_format='d')
        axes[idx].set_title(f'{name} Confusion Matrix')
        
    # 5. Save comparison table
    results_df = pd.DataFrame(results)
    results_df.to_csv('results/model_comparison.csv', index=False)
    print("Saved model_comparison.csv")
    print(results_df.to_string(index=False))
    
    # 6. Save confusion matrices plot
    plt.tight_layout()
    plt.savefig('results/confusion_matrices.png', dpi=300)
    print("Saved confusion_matrices.png")

if __name__ == "__main__":
    train_and_compare()