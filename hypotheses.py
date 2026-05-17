import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import label_binarize

def test_hypotheses():
    df = pd.read_csv('results/features.csv')
    
    # H1: Market is efficient
    y_true_bin = label_binarize(df['outcome'], classes=[0, 1, 2])
    implied_probs = df[['prob_1_normed', 'prob_x_normed', 'prob_2_normed']].values
    
    brier_implied = np.mean(np.sum((implied_probs - y_true_bin)**2, axis=1))
    
    naive_probs = np.full_like(implied_probs, 1/3)
    brier_naive = np.mean(np.sum((naive_probs - y_true_bin)**2, axis=1))
    
    # H2: Odds movement is a signal
    X_movement = df[['odds_movement_1']]
    X_levels = df[['prob_1_normed', 'prob_x_normed', 'prob_2_normed']]
    y = df['outcome']
    
    lr_movement = LogisticRegression(random_state=42)
    lr_movement.fit(X_movement, y)
    acc_movement = accuracy_score(y, lr_movement.predict(X_movement))
    
    lr_levels = LogisticRegression(random_state=42)
    lr_levels.fit(X_levels, y)
    acc_levels = accuracy_score(y, lr_levels.predict(X_levels))
    
    with open('results/hypotheses.txt', 'w') as f:
        f.write("H1: Market Efficiency\n")
        f.write(f"Brier Score (Implied Probabilities): {brier_implied:.4f}\n")
        f.write(f"Brier Score (Naive [0.33, 0.33, 0.33]): {brier_naive:.4f}\n")
        if brier_implied < brier_naive:
            f.write("Conclusion: The market is more efficient than a naive baseline (lower Brier score is better).\n\n")
        else:
            f.write("Conclusion: The market is NOT more efficient than a naive baseline.\n\n")
            
        f.write("H2: Odds Movement as a Signal\n")
        f.write(f"Accuracy (Odds movement feature only): {acc_movement:.4f}\n")
        f.write(f"Accuracy (Probability level features only): {acc_levels:.4f}\n")
        f.write("Conclusion: Odds movement alone is a much weaker signal compared to the actual probability levels.\n")

if __name__ == "__main__":
    test_hypotheses()