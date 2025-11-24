import unittest
from unittest.mock import patch, MagicMock
import sys


class MockIssue:
    def __init__(self, data=None, **kwargs):
        self.creator = kwargs.get('creator')
        self.events = kwargs.get('events', [])

class MockEvent:
    def __init__(self, data=None, **kwargs):
        self.author = kwargs.get('author')

mock_model = MagicMock()
mock_model.Issue = MockIssue
mock_model.Event = MockEvent
sys.modules['model'] = mock_model
sys.modules['config'] = MagicMock()


import example_analysis

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

if __name__ == '__main__':
    unittest.main()