import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# League Configuration
# 39 is Premier League
LEAGUE_ID = 39 
# Updated to current season based on system time (2025)
SEASON = 2025


# Demo Mode: Set to False to use real system time and data.
# Set to True to mock the date (useful if testing with historical data).
DEMO_MODE = False
