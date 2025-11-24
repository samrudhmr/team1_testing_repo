import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model import State, Event, Issue


class TestStateEnum(unittest.TestCase):
    """Test cases for State enum"""
    
    def test_state_values(self):
        """Test that State enum has correct values"""
        self.assertEqual(State.open, 'open')
        self.assertEqual(State.closed, 'closed')
    
    def test_state_instantiation(self):
        """Test creating State from string"""
        open_state = State['open']
        closed_state = State['closed']
        
        self.assertEqual(open_state, State.open)
        self.assertEqual(closed_state, State.closed)


class TestEvent(unittest.TestCase):
    """Test cases for Event class"""
    
    def test_event_initialization_empty(self):
        """Test Event initialization with no data"""
        event = Event(None)
        
        self.assertIsNone(event.event_type)
        self.assertIsNone(event.author)
        self.assertIsNone(event.event_date)
        self.assertIsNone(event.label)
        self.assertIsNone(event.comment)
    
    def test_event_initialization_with_data(self):
        """Test Event initialization with JSON data"""
        test_data = {
            'event_type': 'labeled',
            'author': 'testuser',
            'event_date': '2023-01-15T10:30:00Z',
            'label': 'bug',
            'comment': 'This is a test comment'
        }
        
        event = Event(test_data)
        
        self.assertEqual(event.event_type, 'labeled')
        self.assertEqual(event.author, 'testuser')
        self.assertIsInstance(event.event_date, datetime)
        self.assertEqual(event.label, 'bug')
        self.assertEqual(event.comment, 'This is a test comment')
    
    def test_event_initialization_partial_data(self):
        """Test Event initialization with partial data"""
        test_data = {
            'event_type': 'commented',
            'author': 'user2'
            # Missing other fields
        }
        
        event = Event(test_data)
        
        self.assertEqual(event.event_type, 'commented')
        self.assertEqual(event.author, 'user2')
        self.assertIsNone(event.event_date)
        self.assertIsNone(event.label)
        self.assertIsNone(event.comment)
    
    def test_event_invalid_date(self):
        """Test Event with invalid date string"""
        test_data = {
            'event_type': 'labeled',
            'event_date': 'invalid-date-string'
        }
        
        # Should not raise exception, just set event_date to None
        event = Event(test_data)
        
        self.assertEqual(event.event_type, 'labeled')
        self.assertIsNone(event.event_date)
    
    def test_event_from_json_method(self):
        """Test the from_json method directly"""
        event = Event(None)
        
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
        self.assertIsNone(event.label)
        self.assertEqual(event.comment, 'Assigned to user')


class TestIssue(unittest.TestCase):
    """Test cases for Issue class"""
    
    def test_issue_initialization_empty(self):
        """Test Issue initialization with no data"""
        issue = Issue(None)
        
        self.assertIsNone(issue.url)
        self.assertIsNone(issue.creator)
        self.assertEqual(issue.labels, [])
        self.assertIsNone(issue.state)
        self.assertEqual(issue.assignees, [])
        self.assertIsNone(issue.title)
        self.assertIsNone(issue.text)
        self.assertEqual(issue.number, -1)
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)
        self.assertIsNone(issue.timeline_url)
        self.assertEqual(issue.events, [])
    
    def test_issue_initialization_with_data(self):
        """Test Issue initialization with complete JSON data"""
        test_data = {
            'url': 'https://github.com/test/repo/issues/1',
            'creator': 'creatoruser',
            'labels': ['bug', 'priority:high'],
            'state': 'open',
            'assignees': ['user1', 'user2'],
            'title': 'Test Issue Title',
            'text': 'This is the issue description',
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
        
        issue = Issue(test_data)
        
        # Test basic properties
        self.assertEqual(issue.url, 'https://github.com/test/repo/issues/1')
        self.assertEqual(issue.creator, 'creatoruser')
        self.assertEqual(issue.labels, ['bug', 'priority:high'])
        self.assertEqual(issue.state, State.open)
        self.assertEqual(issue.assignees, ['user1', 'user2'])
        self.assertEqual(issue.title, 'Test Issue Title')
        self.assertEqual(issue.text, 'This is the issue description')
        self.assertEqual(issue.number, 123)
        self.assertIsInstance(issue.created_date, datetime)
        self.assertIsInstance(issue.updated_date, datetime)
        self.assertEqual(issue.timeline_url, 'https://github.com/test/repo/issues/1/timeline')
        
        # Test events
        self.assertEqual(len(issue.events), 2)
        self.assertIsInstance(issue.events[0], Event)
        self.assertEqual(issue.events[0].event_type, 'labeled')
        self.assertEqual(issue.events[1].event_type, 'assigned')
    
    def test_issue_state_closed(self):
        """Test Issue with closed state"""
        test_data = {
            'state': 'closed',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = Issue(test_data)
        self.assertEqual(issue.state, State.closed)
    
    def test_issue_invalid_number(self):
        """Test Issue with invalid number string"""
        test_data = {
            'number': 'not-a-number',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = Issue(test_data)
        self.assertEqual(issue.number, -1)  # Should keep default value
    
    def test_issue_invalid_dates(self):
        """Test Issue with invalid date strings"""
        test_data = {
            'created_date': 'invalid-date',
            'updated_date': 'another-invalid-date',
            'labels': [],
            'assignees': [],
            'events': []
        }
        
        issue = Issue(test_data)
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)
    
    def test_issue_empty_events(self):
        """Test Issue with empty events list"""
        test_data = {
            'events': [],
            'labels': [],
            'assignees': []
        }
        
        issue = Issue(test_data)
        self.assertEqual(issue.events, [])
    
    def test_issue_missing_optional_fields(self):
        """Test Issue with missing optional fields"""
        test_data = {
            'state': 'open',
            'labels': [],
            'assignees': []
            # Missing url, creator, title, etc.
        }
        
        issue = Issue(test_data)
        self.assertEqual(issue.state, State.open)
        self.assertIsNone(issue.url)
        self.assertIsNone(issue.creator)
        self.assertIsNone(issue.title)
        self.assertIsNone(issue.text)
        self.assertEqual(issue.number, -1)
        self.assertIsNone(issue.created_date)
        self.assertIsNone(issue.updated_date)
        self.assertIsNone(issue.timeline_url)
    
    def test_issue_from_json_method(self):
        """Test the from_json method directly"""
        issue = Issue(None)
        
        test_data = {
            'url': 'https://example.com/issue/1',
            'creator': 'testuser',
            'labels': ['feature'],
            'state': 'closed',
            'assignees': ['dev1'],
            'title': 'Test Issue',
            'text': 'Description',
            'number': '456',
            'created_date': '2023-03-01T12:00:00Z',
            'updated_date': '2023-03-05T18:00:00Z',
            'timeline_url': 'https://example.com/issue/1/timeline',
            'events': [
                {
                    'event_type': 'commented',
                    'author': 'user1',
                    'event_date': '2023-03-02T10:00:00Z',
                    'label': None,
                    'comment': 'This is a comment'
                }
            ]
        }
        
        issue.from_json(test_data)
        
        self.assertEqual(issue.url, 'https://example.com/issue/1')
        self.assertEqual(issue.creator, 'testuser')
        self.assertEqual(issue.labels, ['feature'])
        self.assertEqual(issue.state, State.closed)
        self.assertEqual(issue.assignees, ['dev1'])
        self.assertEqual(issue.title, 'Test Issue')
        self.assertEqual(issue.text, 'Description')
        self.assertEqual(issue.number, 456)
        self.assertIsInstance(issue.created_date, datetime)
        self.assertIsInstance(issue.updated_date, datetime)
        self.assertEqual(issue.timeline_url, 'https://example.com/issue/1/timeline')
        self.assertEqual(len(issue.events), 1)
        self.assertEqual(issue.events[0].event_type, 'commented')
    
    def test_issue_default_values_with_empty_json(self):
        """Test Issue with empty JSON object"""
        test_data = {}
        
        issue = Issue(test_data)
        
        # Should have default values
        self.assertEqual(issue.labels, [])
        self.assertEqual(issue.assignees, [])
        self.assertEqual(issue.number, -1)
        self.assertEqual(issue.events, [])
    
    def test_issue_with_none_events(self):
        """Test Issue when events field is None"""
        test_data = {
            'events': None,
            'labels': [],
            'assignees': []
        }
        
        issue = Issue(test_data)
        self.assertEqual(issue.events, [])


if __name__ == '__main__':
    unittest.main()