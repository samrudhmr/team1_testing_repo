import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys


class MockIssue:
    """
    A fake Issue class that behaves like the real one.
    """
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
    """A fake Event class."""
    def __init__(self, data=None, **kwargs):
        if isinstance(data, dict):
            self.author = data.get('author')
            self.event_type = data.get('event_type')
            self.actor = data.get('actor')
            self.actor_login = data.get('actor_login')
        else:
            self.author = kwargs.get('author', data)
            self.event_type = kwargs.get('event_type')
            self.actor = kwargs.get('actor')
            self.actor_login = kwargs.get('actor_login')

# Apply mocks so the project files don't crash on import
mock_model = MagicMock()
mock_model.Issue = MockIssue
mock_model.Event = MockEvent
sys.modules['model'] = mock_model
sys.modules['config'] = MagicMock()

import data_loader
import example_analysis
import top_user_activity


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


class TestExampleAnalysis(unittest.TestCase):

    @patch('example_analysis.plt.show') 
    @patch('example_analysis.DataLoader')
    @patch('example_analysis.config.get_parameter')
    def test_run_analysis_with_user(self, mock_config, mock_loader, mock_show):
        """Test the graph generation when a specific user is filtered."""
        mock_config.return_value = 'Alice'
        
        fake_issue = MockIssue(creator='Alice', events=[MockEvent(author='Alice')])
        mock_loader.return_value.get_issues.return_value = [fake_issue]
        
        analysis = example_analysis.ExampleAnalysis()
        
        with patch('sys.stdout', new=MagicMock()):
            analysis.run()
            
        self.assertTrue(mock_show.called)

    @patch('example_analysis.plt.show')
    @patch('example_analysis.DataLoader')
    @patch('example_analysis.config.get_parameter')
    def test_run_analysis_all_users(self, mock_config, mock_loader, mock_show):
        """Test the graph generation for all users (no filter)."""
        mock_config.return_value = None 
        
        fake_issue = MockIssue(creator='Bob', events=[])
        mock_loader.return_value.get_issues.return_value = [fake_issue]
        
        analysis = example_analysis.ExampleAnalysis()
        analysis.run()
        
        self.assertTrue(mock_show.called)


class TestTopUserActivity(unittest.TestCase):

    def setUp(self):
        # Prevent the Analyser from loading real data during init
        with patch('top_user_activity.DataLoader') as MockLoader:
            MockLoader.return_value.get_issues.return_value = []
            self.analyser = top_user_activity.TopUserActivityAnalyser()

    @patch('top_user_activity.plt.show')
    def test_score_calculation(self, mock_show):
        """Test if activity scores are calculated correctly."""
        
        # Scenario: Alice opens an issue. Bob closes it and comments.
        issue_1 = MockIssue(creator_login='Alice', state='closed', events=[
            MockEvent(actor_login='Bob', event_type='closed'),
            MockEvent(actor_login='Bob', event_type='commented')
        ])
        
        self.analyser.issues = [issue_1]
        
        with patch('builtins.print'):
            self.analyser.run()

        df = self.analyser._compute_activity_dataframe(True)
        
        # Check Alice (1 point for opening)
        alice = df[df['user'] == 'Alice'].iloc[0]
        self.assertEqual(alice['score'], 1)
        
        # Check Bob (2 points: 1 close + 1 comment)
        bob = df[df['user'] == 'Bob'].iloc[0]
        self.assertEqual(bob['score'], 2)

    def test_helper_methods(self):
        """Test that the code handles messed up data structures correctly."""
        
        # Test finding creator in a nested dictionary
        hybrid_issue = MockIssue()
        hybrid_issue.user = {'login': 'Dave'} 
        creator = self.analyser._issue_creator(hybrid_issue)
        self.assertEqual(creator, 'Dave')
        
        # Test finding state in a raw dictionary
        dict_issue = {'state': 'CLOSED'}
        state = self.analyser._issue_state(dict_issue)
        self.assertEqual(state, 'closed')
        
        # Test the known bug: passing a dictionary to _event_actor returns None
        dict_event = {'actor': {'login': 'BuggyActor'}}
        result = self.analyser._event_actor(dict_event)
        self.assertIsNone(result)

    @patch('top_user_activity.plt.show')
    def test_empty_dataset(self, mock_show):
        """Ensure code handles empty lists."""
        self.analyser.issues = []
        with patch('builtins.print'):
            self.analyser.run()
        
        df = self.analyser._compute_activity_dataframe(True)
        self.assertTrue(df.empty)

if __name__ == '__main__':
    unittest.main()