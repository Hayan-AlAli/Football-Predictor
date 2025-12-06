import unittest
from datetime import datetime
import utils
import match_manager
from predictor import predict_match

class TestFootballApp(unittest.TestCase):

    def test_predictor_structure(self):
        """Test that predictor returns correct structure."""
        match_data = {
            'home_team': 'Team A',
            'away_team': 'Team B'
        }
        # Predictor handles unseen teams gracefully (random fallback)
        prediction = predict_match(match_data)
        self.assertIn('winner', prediction)
        self.assertIn('score', prediction)

    def test_normalization(self):
        """Test team name normalization."""
        self.assertEqual(utils.normalize_team_name("Newcastle Utd"), "Newcastle")
        self.assertEqual(utils.normalize_team_name("Arsenal"), "Arsenal")

    def test_date_formatting(self):
        """Test date formatting."""
        dt = datetime(2025, 12, 25, 15, 30)
        formatted = utils.format_match_time(dt)
        self.assertEqual(formatted, "2025-12-25 15:30")

if __name__ == '__main__':
    unittest.main()
