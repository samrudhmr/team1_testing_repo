import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys


class MockIssue:
    def __init__(self, data=None, **kwargs):
        if isinstance(data, dict):
            self.creator = data.get('creator')
            self.creator_login = data.get('creator_login')
            self.events = data.get('events', [])
            self.user = data.get('user')
            self.state = data.get('state')
        else:
            self.creator = kwargs.get('creator', data)
            self.creator_login = kwargs.get('creator_login')
            self.events = kwargs.get('events', [])
            self.user = kwargs.get('user')
            self.state = kwargs.get('state')

class MockEvent:
    def __init__(self, data=None, **kwargs):
        pass 

mock_model = MagicMock()
mock_model.Issue = MockIssue
mock_model.Event = MockEvent
sys.modules['model'] = mock_model
sys.modules['config'] = MagicMock()


import data_loader

class TestDataLoader(unittest.TestCase):
    
    def setUp(self):
        # Reset the global variable before every test
        data_loader._ISSUES = None

    @patch('builtins.open', new_callable=mock_open)
    @patch('data_loader.json.load')
    def test_load_data_successfully(self, mock_json, mock_file):
        """Test that the loader actually reads the file and creates objects."""
        mock_json.return_value = [{'creator': 'Alice'}]
        
        loader = data_loader.DataLoader()
        issues = loader.get_issues()
        
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].creator, 'Alice')
        self.assertTrue(mock_file.called)

    @patch('builtins.open', new_callable=mock_open)
    @patch('data_loader.json.load')
    def test_singleton_pattern(self, mock_json, mock_file):
        """Test that we don't reload the file if we already have the data."""
        mock_json.return_value = []
        
        loader = data_loader.DataLoader()
        loader.get_issues() # First load
        loader.get_issues() # Second load (should use cache)
        
        self.assertEqual(mock_json.call_count, 1)

if __name__ == '__main__':
    unittest.main()