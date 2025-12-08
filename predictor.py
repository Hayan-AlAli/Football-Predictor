import joblib
import pandas as pd
import os
import random
import utils
import features
import math

# Load models if they exist
MODEL_PATH_HOME = 'model_home.pkl'
MODEL_PATH_AWAY = 'model_away.pkl'
ENCODER_PATH = 'team_encoder.pkl'
ELO_PATH = 'elo_state.pkl'
TRAINING_DATA_PATH = 'training_data.pkl'

model_home = None
model_away = None
encoder = None
elo_state = None
training_df = None

try:
    if os.path.exists(MODEL_PATH_HOME):
        model_home = joblib.load(MODEL_PATH_HOME)
    if os.path.exists(MODEL_PATH_AWAY):
        model_away = joblib.load(MODEL_PATH_AWAY)
    if os.path.exists(ENCODER_PATH):
        encoder = joblib.load(ENCODER_PATH)
    if os.path.exists(ELO_PATH):
        elo_state = joblib.load(ELO_PATH)
    if os.path.exists(TRAINING_DATA_PATH):
        training_df = joblib.load(TRAINING_DATA_PATH)
        
except Exception as e:
    print(f"Error loading models: {e}")

def get_latest_stats(team_name, df, window=5):
    """Calculates the rolling stats for the team based on historical data."""
    # Filter matches where team played
    home_matches = df[df['home_team'] == team_name]
    away_matches = df[df['away_team'] == team_name]
    
    # Combine and sort by date
    all_matches = pd.concat([home_matches, away_matches]).sort_values(by='date')
    
    if all_matches.empty:
        return 0.0, 0.0 # Default if no history
        
    # Get last N matches
    recent = all_matches.tail(window)
    
    goals = []
    xg = []
    
    for _, match in recent.iterrows():
        if match['home_team'] == team_name:
            goals.append(match['home_goals'])
            xg.append(match['home_xg'] if not pd.isna(match.get('home_xg')) else 0.0)
        else:
            goals.append(match['away_goals'])
            xg.append(match['away_xg'] if not pd.isna(match.get('away_xg')) else 0.0)
            
    avg_goals = sum(goals) / len(goals) if goals else 0.0
    avg_xg = sum(xg) / len(xg) if xg else 0.0
    
    return avg_goals, avg_xg

def poisson_probability(k, lamb):
    """Calculates Poisson probability P(k; lambda)."""
    return (lamb**k * math.exp(-lamb)) / math.factorial(k)

def calculate_probabilities(home_avg, away_avg, max_goals=10):
    """
    Calculates win/draw/loss probabilities based on Poisson distribution.
    """
    prob_home_win = 0.0
    prob_draw = 0.0
    prob_away_win = 0.0
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_probability(h, home_avg) * poisson_probability(a, away_avg)
            if h > a:
                prob_home_win += p
            elif a > h:
                prob_away_win += p
            else:
                prob_draw += p
                
    # Normalize (since we truncated at max_goals)
    total_prob = prob_home_win + prob_draw + prob_away_win
    if total_prob > 0:
        prob_home_win /= total_prob
        prob_draw /= total_prob
        prob_away_win /= total_prob
        
    return prob_home_win, prob_draw, prob_away_win

def random_prediction(home_team, away_team):
    """Fallback random prediction."""
    home_score = random.randint(0, 3) 
    away_score = random.randint(0, 3)
    if home_score > away_score:
        winner = home_team
    elif away_score > home_score:
        winner = away_team
    else:
        winner = "Draw"
        
    return {
        "winner": winner,
        "score": f"{home_score}-{away_score}",
        "home_goals": home_score,
        "away_goals": away_score,
        "prob_home": 0.33,
        "prob_draw": 0.34,
        "prob_away": 0.33
    }

def predict_match(match_data):
    """
    Predicts the outcome using AI model if available, else random.
    match_data: dict with keys 'home_team' and 'away_team'
    """
    home_team = match_data['home_team']
    away_team = match_data['away_team']
    
    if model_home and model_away and encoder and elo_state and training_df is not None:
        try:
            # Normalize
            home_team_norm = utils.normalize_team_name(home_team)
            away_team_norm = utils.normalize_team_name(away_team)

            # 1. Team Codes
            home_code = encoder.transform([home_team_norm])[0]
            away_code = encoder.transform([away_team_norm])[0]
            
            # 2. ELO
            home_elo = elo_state.get_rating(home_team_norm)
            away_elo = elo_state.get_rating(away_team_norm)
            
            # 3. Rolling Stats
            h_g, h_xg = get_latest_stats(home_team_norm, training_df)
            a_g, a_xg = get_latest_stats(away_team_norm, training_df)
            
            # Construct Feature Vector
            features_dict = {
                'home_team_code': home_code,
                'away_team_code': away_code,
                'home_elo': home_elo,
                'away_elo': away_elo,
                'home_rolling_goals': h_g,
                'away_rolling_goals': a_g,
                'home_rolling_xg': h_xg,
                'away_rolling_xg': a_xg
            }
            
            X_pred = pd.DataFrame([features_dict])
            
            pred_home_goals = model_home.predict(X_pred)[0]
            pred_away_goals = model_away.predict(X_pred)[0]
            
            # Ensure non-negative
            pred_home_goals = max(0.0, pred_home_goals)
            pred_away_goals = max(0.0, pred_away_goals)
            
            # Calculate Probabilities
            prob_home, prob_draw, prob_away = calculate_probabilities(pred_home_goals, pred_away_goals)
            
            # Round to nearest integer for display, but keep float for winner logic
            score_home = round(pred_home_goals)
            score_away = round(pred_away_goals)
            
            # Winner based on highest probability
            if prob_home > prob_away and prob_home > prob_draw:
                winner = home_team
            elif prob_away > prob_home and prob_away > prob_draw:
                winner = away_team
            else:
                 # Check if probabilities are very close or draw is highest
                if prob_home > prob_away:
                     winner = home_team # Lean to home if close? No, stick to prob
                elif prob_away > prob_home:
                     winner = away_team
                else:
                    winner = "Draw"
            
            # Override winner if probabilities dictate something else or match expectation logic
            # Actually, standard is: highest prob wins.
            if prob_draw >= prob_home and prob_draw >= prob_away:
                winner = "Draw"
                
            return {
                'winner': winner,
                'score': f"{int(score_home)}-{int(score_away)}",
                'home_goals': pred_home_goals,
                'away_goals': pred_away_goals,
                'home_elo': int(home_elo),
                'away_elo': int(away_elo),
                'prob_home': prob_home,
                'prob_draw': prob_draw,
                'prob_away': prob_away
            }
            
        except Exception as e:
            # Fallback if team not found in encoder etc
            # print(f"Prediction Error: {e}")
            return random_prediction(home_team, away_team)
    else:
        return random_prediction(home_team, away_team)
