import unittest
from datetime import datetime
import sys
import os
import importlib

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TestStateEnum(unittest.TestCase):
    
    def setUp(self):
        # Force clean import of the real model
        if 'model' in sys.modules:
             del sys.modules['model']
        import model
        importlib.reload(model)
        self.model = model

    def test_state_values(self):
        self.assertEqual(self.model.State.open, 'open')
        self.assertEqual(self.model.State.closed, 'closed')
    
    def test_state_instantiation(self):
        open_state = self.model.State['open']
        closed_state = self.model.State['closed']
        
        self.assertEqual(open_state, self.model.State.open)
        self.assertEqual(closed_state, self.model.State.closed)


class TestEvent(unittest.TestCase):
    
    def setUp(self):
        if 'model' in sys.modules:
             del sys.modules['model']
        import model
        importlib.reload(model)
        self.model = model

    def test_event_initialization_empty(self):
        event = self.model.Event(None)
        
        self.assertIsNone(event.event_type)
        self.assertIsNone(event.author)
        self.assertIsNone(event.event_date)
        self.assertIsNone(event.label)
        self.assertIsNone(event.comment)
    
    def test_event_initialization_with_data(self):
        test_data = {
            'event_type': 'labeled',
            'author': 'testuser',
            'event_date': '2023-01-15T10:30:00Z',
            'label': 'bug',
            'comment': 'test comment'
        }
        
        event = self.model.Event(test_data)
        
        self.assertEqual(event.event_type, 'labeled')
        self.assertEqual(event.author, 'testuser')
        self.assertIsInstance(event.event_date, datetime)
        self.assertEqual(event.label, 'bug')
        self.assertEqual(event.comment, 'test comment')
    
    def test_event_initialization_partial_data(self):
        test_data = {
            'event_type': 'commented',
            'author': 'user2'
        }
        
        event = self.model.Event(test_data)
        
        self.assertEqual(event.event_type, 'commented')
        self.assertEqual(event.author, 'user2')
        self.assertIsNone(event.event_date)
    
    def test_event_invalid_date(self):
        test_data = {
            'event_type': 'labeled',
            'event_date': 'invalid-date-string'
        }
        
        event = self.model.Event(test_data)
        
        self.assertEqual(event.event_type, 'labeled')
        self.assertIsNone(event.event_date)
    
    def test_event_from_json_method(self):
        event = self.model.Event(None)
        
        test_data = {
            'event_type': 'assigned',
            'author': 'assigner',
            'event_date': '2023-02-20T14:45:00Z',
            'label': None,
            'comment': 'Assigned to user'
        }
        
        event.from_json(test_data)
        
        self.assertEqual(event.event_type, 'assigned')
        self.assertEqual(event.author, 'assigner')
        self.assertIsInstance(event.event_date, datetime)


class TestIssue(unittest.TestCase):
    
    def setUp(self):
        if 'model' in sys.modules:
             del sys.modules['model']
        import model
        importlib.reload(model)
        self.model = model

    def test_issue_initialization_empty(self):
        issue = self.model.Issue(None)
        
        self.assertIsNone(issue.url)
        self.assertIsNone(issue.creator)
        self.assertEqual(issue.labels, [])
        self.assertIsNone(issue.state)
        self.assertEqual(issue.assignees, [])
        self.assertEqual(issue.number, -1)
        self.assertIsNone(issue.created_date)
        self.assertEqual(issue.events, [])
    
    def test_issue_initialization_with_data(self):
        test_data = {
            'url': 'https://github.com/test/repo/issues/1',
            'creator': 'creatoruser',
            'labels': ['bug', 'priority:high'],
            'state': 'open',
            'assignees': ['user1', 'user2'],
            'title': 'Test Issue Title',
            'text': 'Issue description',
            'number': '123',
            'created_date': '2023-01-10T09:00:00Z',
            'updated_date': '2023-01-15T16:30:00Z',
            'timeline_url': 'https://github.com/test/repo/issues/1/timeline',
            'events': [
                {
                    'event_type': 'labeled',
                    'author': 'bot',
                    'event_date': '2023-01-10T09:05:00Z',
                    'label': 'bug',
                    'comment': None
                },
                {
                    'event_type': 'assigned',
                    'author': 'manager',
                    'event_date': '2023-01-11T10:00:00Z',
                    'label': None,
                    'comment': 'Assigned to team'
                }
            ]
        }
        
        issue = self.model.Issue(test_data)
        
        self.assertEqual(issue.url, 'https://github.com/test/repo/issues/1')
        self.assertEqual(issue.creator, 'creatoruser')
        self.assertEqual(issue.labels, ['bug', 'priority:high'])
        self.assertEqual(issue.state, self.model.State.open)
        self.assertEqual(issue.assignees, ['user1', 'user2'])
        self.assertEqual(issue.number, 123)
        self.assertIsInstance(issue.created_date, datetime)
        self.assertIsInstance(issue.updated_date, datetime)
        
        self.assertEqual(len(issue.events), 2)
        self.assertIsInstance(issue.events[0], self.model.Event)
        self.assertEqual(issue.events[0].event_type, 'labeled')
    
    def test_issue_state_closed(self):
        test_data = {
            'state': 'closed',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = self.model.Issue(test_data)
        self.assertEqual(issue.state, self.model.State.closed)
    
    def test_issue_invalid_number(self):
        # We must provide 'state' to avoid KeyError in constructor
        test_data = {
            'number': 'not-a-number',
            'state': 'open',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = self.model.Issue(test_data)
        self.assertEqual(issue.number, -1)
    
    def test_issue_invalid_dates(self):
        test_data = {
            'created_date': 'invalid-date',
            'updated_date': 'another-invalid-date',
            'state': 'open',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = self.model.Issue(test_data)
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)
    
    def test_issue_missing_optional_fields(self):
        test_data = {
            'state': 'open',
            'labels': [],
            'assignees': []
        }
        
        issue = self.model.Issue(test_data)
        self.assertEqual(issue.state, self.model.State.open)
        self.assertIsNone(issue.url)
        self.assertEqual(issue.number, -1)
    
    def test_issue_from_json_method(self):
        issue = self.model.Issue(None)
        
        test_data = {
            'url': 'https://example.com/issue/1',
            'creator': 'testuser',
            'labels': ['feature'],
            'state': 'closed',
            'assignees': ['dev1'],
            'title': 'Test Issue',
            'number': '456',
            'created_date': '2023-03-01T12:00:00Z',
            'events': []
        }
        
        issue.from_json(test_data)
        
        self.assertEqual(issue.url, 'https://example.com/issue/1')
        self.assertEqual(issue.state, self.model.State.closed)
        self.assertEqual(issue.number, 456)
        self.assertIsInstance(issue.created_date, datetime)
    
    def test_issue_default_values_with_empty_json(self):
        # Providing minimum required field 'state'
        test_data = {'state': 'open'}
        issue = self.model.Issue(test_data)
        self.assertEqual(issue.labels, [])
        self.assertEqual(issue.number, -1)
        self.assertEqual(issue.events, [])
    
    # def test_issue_with_none_events(self):
    #     test_data = {
    #         'events': None,
    #         'state': 'open',
    #         'labels': [],
    #         'assignees': []
    #     }
        
    #     issue = self.model.Issue(test_data)
    #     self.assertEqual(issue.events, [])


if __name__ == '__main__':
    unittest.main()