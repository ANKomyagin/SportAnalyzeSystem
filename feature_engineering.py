import sqlite3
import pandas as pd
import numpy as np

def build_features():
    conn = sqlite3.connect('football_copy.db')
    
    query = """
    SELECT 
        start_time,
        home_score_ft, away_score_ft,
        open_1, close_1, close_x, close_2
    FROM matches
    WHERE home_score_ft IS NOT NULL 
      AND away_score_ft IS NOT NULL
      AND close_1 IS NOT NULL
      AND close_x IS NOT NULL
      AND close_2 IS NOT NULL
    ORDER BY start_time ASC
    """
    df = pd.read_sql(query, conn)
    
    conditions = [
        df['home_score_ft'] > df['away_score_ft'],
        df['home_score_ft'] == df['away_score_ft'],
        df['home_score_ft'] < df['away_score_ft']
    ]
    choices = [0, 1, 2]
    df['outcome'] = np.select(conditions, choices, default=-1)
    
    df = df[df['outcome'] != -1].copy()
    
    df['implied_prob_1'] = 1 / df['close_1']
    df['implied_prob_x'] = 1 / df['close_x']
    df['implied_prob_2'] = 1 / df['close_2']
    
    df['overround'] = df['implied_prob_1'] + df['implied_prob_x'] + df['implied_prob_2']
    
    df['prob_1_normed'] = df['implied_prob_1'] / df['overround']
    df['prob_x_normed'] = df['implied_prob_x'] / df['overround']
    df['prob_2_normed'] = df['implied_prob_2'] / df['overround']
    
    df['odds_movement_1'] = df['close_1'] - df['open_1']
    df['odds_movement_1'] = df['odds_movement_1'].fillna(0)
    
    df['favorite_home'] = (df['close_1'] < df['close_2']).astype(int)
    
    features = [
        'start_time', 'close_1', 'close_x', 'close_2',
        'prob_1_normed', 'prob_x_normed', 'prob_2_normed', 
        'odds_movement_1', 'favorite_home', 'outcome'
    ]
    
    df[features].to_csv('results/features.csv', index=False)
    print(f"Saved {len(df)} rows to results/features.csv")

if __name__ == "__main__":
    build_features()