import unittest
from unittest.mock import patch, MagicMock
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
        if isinstance(data, dict):
            self.actor = data.get('actor')
            self.actor_login = data.get('actor_login')
            self.event_type = data.get('event_type')
        else:
            self.actor = kwargs.get('actor')
            self.actor_login = kwargs.get('actor_login')
            self.event_type = kwargs.get('event_type')

mock_model = MagicMock()
mock_model.Issue = MockIssue
mock_model.Event = MockEvent
sys.modules['model'] = mock_model
sys.modules['config'] = MagicMock()


import top_user_activity

class TestTopUserActivity(unittest.TestCase):

    def setUp(self):
        # Prevent loading real data during init
        with patch('top_user_activity.DataLoader') as MockLoader:
            MockLoader.return_value.get_issues.return_value = []
            self.analyser = top_user_activity.TopUserActivityAnalyser()

    @patch('top_user_activity.plt.show')
    def test_score_calculation(self, mock_show):
        """Test if activity scores are calculated correctly."""
        
        issue_1 = MockIssue(creator_login='Alice', state='closed', events=[
            MockEvent(actor_login='Bob', event_type='closed'),
            MockEvent(actor_login='Bob', event_type='commented')
        ])
        
        self.analyser.issues = [issue_1]
        
        with patch('builtins.print'):
            self.analyser.run()

        df = self.analyser._compute_activity_dataframe(True)
        
        alice = df[df['user'] == 'Alice'].iloc[0]
        self.assertEqual(alice['score'], 1)
        
        bob = df[df['user'] == 'Bob'].iloc[0]
        self.assertEqual(bob['score'], 2)

    def test_helper_methods(self):
        """Test that the code handles messed up data structures correctly."""
        
        # 1. Test finding creator in a nested dictionary
        hybrid_issue = MockIssue()
        hybrid_issue.user = {'login': 'Dave'} 
        creator = self.analyser._issue_creator(hybrid_issue)
        self.assertEqual(creator, 'Dave')
        
        # 2. Test finding state in a raw dictionary
        dict_issue = {'state': 'CLOSED'}
        state = self.analyser._issue_state(dict_issue)
        self.assertEqual(state, 'closed')
        
        # 3. Test the known bug: passing a dictionary to _event_actor returns None
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


    def test_ghost_user_crash(self):
        """
        Bug: If a user is None (deleted account), the print formatting 
        crashes with TypeError.
        """
        ghost_issue = MockIssue(creator=None, user=None, creator_login=None)
        self.analyser.issues = [ghost_issue]
        
        with self.assertRaises(TypeError):
            with patch('builtins.print'): 
                self.analyser.run()

    def test_logic_closed_issues(self):
        """
        Checks if closed issues get credited properly.
        """
        # Issue is closed, but the only event is 'labeled'.
        trap_issue = MockIssue(creator='Alice', state='closed', events=[
            MockEvent(event_type='labeled', actor_login='Bot')
        ])
        
        self.analyser.issues = [trap_issue]
        
        df = self.analyser._compute_activity_dataframe(True)
        
        row = df[df['user'] == 'Alice'].iloc[0]
        
        # We Expect Alice to have 1 closed credit because the issue is closed.
        # The code calculates 0. This assertion will fail.
        self.assertEqual(row['closed'], 1, "Alice should be credited for the closed issue")

if __name__ == '__main__':
    unittest.main()