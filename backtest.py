import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression

def backtest():
    df = pd.read_csv('results/features.csv')
    df['start_time'] = pd.to_datetime(df['start_time'], unit='ms')
    df = df.sort_values('start_time').reset_index(drop=True)
    
    split_idx = int(len(df) * 0.7)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:].copy()
    
    features = ['prob_1_normed', 'prob_x_normed', 'prob_2_normed', 'odds_movement_1', 'favorite_home']
    X_train = train_df[features]
    y_train = train_df['outcome']
    X_test = test_df[features]
    
    # Train ML model to get probs
    lr = LogisticRegression(random_state=42)
    lr.fit(X_train, y_train)
    ml_probs = lr.predict_proba(X_test)
    
    # Implied probs
    implied_probs = test_df[['prob_1_normed', 'prob_x_normed', 'prob_2_normed']].values
    close_odds = test_df[['close_1', 'close_x', 'close_2']].values
    outcomes = test_df['outcome'].values
    
    # Strategy A: Implied Favorite
    fav_idx = np.argmin(close_odds, axis=1) # index of min odds is the favorite
    
    strat_a_profit = []
    strat_a_correct = 0
    
    for i in range(len(test_df)):
        bet_idx = fav_idx[i]
        if bet_idx == outcomes[i]:
            payout = close_odds[i, bet_idx]
            strat_a_correct += 1
        else:
            payout = 0
        strat_a_profit.append(payout - 1)
        
    # Strategy B: Value Betting
    strat_b_profit = []
    strat_b_correct = 0
    strat_b_bets = 0
    
    for i in range(len(test_df)):
        edges = ml_probs[i] - implied_probs[i]
        valid_bets = np.where(edges > 0.05)[0]
        
        if len(valid_bets) > 0:
            bet_idx = valid_bets[np.argmax(edges[valid_bets])]
            strat_b_bets += 1
            if bet_idx == outcomes[i]:
                payout = close_odds[i, bet_idx]
                strat_b_correct += 1
            else:
                payout = 0
            strat_b_profit.append(payout - 1)
        else:
            strat_b_profit.append(0)

    test_df['strat_a_profit'] = strat_a_profit
    test_df['strat_b_profit'] = strat_b_profit
    
    # Metrics
    def calc_metrics(profits, total_bets):
        if total_bets == 0:
            return 0, 0, 0
        profits = np.array(profits)
        roi = np.sum(profits) / total_bets * 100
        sharpe = (np.mean(profits) / np.std(profits)) * np.sqrt(252) if np.std(profits) > 0 else 0
        cum_profit = np.cumsum(profits)
        max_drawdown = np.max(np.maximum.accumulate(cum_profit) - cum_profit)
        return roi, sharpe, max_drawdown
        
    roi_a, sharpe_a, md_a = calc_metrics(test_df['strat_a_profit'], len(test_df))
    acc_a = strat_a_correct / len(test_df)
    
    b_profits_only = test_df['strat_b_profit'][test_df['strat_b_profit'] != 0].values
    roi_b, sharpe_b, md_b = calc_metrics(b_profits_only, strat_b_bets)
    acc_b = strat_b_correct / strat_b_bets if strat_b_bets > 0 else 0
    
    summary = pd.DataFrame({
        'Strategy': ['A (Baseline)', 'B (ML Value)'],
        'Total Bets': [len(test_df), strat_b_bets],
        'Accuracy': [acc_a, acc_b],
        'Total ROI (%)': [roi_a, roi_b],
        'Sharpe Ratio': [sharpe_a, sharpe_b],
        'Max Drawdown': [md_a, md_b]
    })
    summary.to_csv('results/backtest_summary.csv', index=False)
    print("Saved backtest_summary.csv")
    print(summary.to_string(index=False))
    
    # Plot cumulative profit
    plt.figure(figsize=(10, 6))
    plt.plot(test_df['start_time'], np.cumsum(test_df['strat_a_profit']), label='Strategy A (Baseline)')
    plt.plot(test_df['start_time'], np.cumsum(test_df['strat_b_profit']), label='Strategy B (ML Value)')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Profit (Units)')
    plt.title('Cumulative Profit by Strategy')
    plt.legend()
    plt.tight_layout()
    plt.savefig('results/cumulative_profit.png')
    print("Saved cumulative_profit.png")
    
    # ROI by month for Strategy B
    test_df['month'] = test_df['start_time'].dt.to_period('M')
    b_bets_df = test_df[test_df['strat_b_profit'] != 0]
    if len(b_bets_df) > 0:
        monthly_b = b_bets_df.groupby('month').agg(
            profit=('strat_b_profit', 'sum'),
            bets=('strat_b_profit', 'count')
        )
        monthly_b['roi'] = monthly_b['profit'] / monthly_b['bets'] * 100
        
        plt.figure(figsize=(10, 6))
        monthly_b['roi'].plot(kind='bar', color='skyblue')
        plt.xlabel('Month')
        plt.ylabel('ROI (%)')
        plt.title('Strategy B ROI by Month')
        plt.tight_layout()
        plt.savefig('results/roi_by_month.png')
        print("Saved roi_by_month.png")
    
if __name__ == "__main__":
    backtest()