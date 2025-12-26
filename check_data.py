
import pandas as pd
import joblib

try:
    df = joblib.load('training_data.pkl')
    print(f"Min Date: {df['date'].min()}")
    print(f"Max Date: {df['date'].max()}")
    print(f"Total rows: {len(df)}")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
