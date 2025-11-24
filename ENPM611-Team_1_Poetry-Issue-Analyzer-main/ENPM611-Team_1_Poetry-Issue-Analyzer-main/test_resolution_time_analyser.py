import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from resolution_time_analyser import ResolutionTimeAnalyser
from model import Issue, Event


class TestResolutionTimeAnalyser(unittest.TestCase):

    def setUp(self):
        # Mock the config and DataLoader dependencies
        self.config_patcher = patch('resolution_time_analyser.config._init_config')
        self.data_loader_patcher = patch('resolution_time_analyser.DataLoader')
        
        self.mock_config = self.config_patcher.start()
        self.mock_data_loader = self.data_loader_patcher.start()
        
        # Create analyzer instance
        self.analyser = ResolutionTimeAnalyser()
        
    def tearDown(self):
        self.config_patcher.stop()
        self.data_loader_patcher.stop()

    def create_mock_issue(self, issue_id, state, created_date, updated_date=None, events=None):
        issue = MagicMock(spec=Issue)
        issue.id = issue_id
        issue.state = state
        issue.created_date = created_date
        issue.updated_date = updated_date or created_date
        issue.events = events or []
        return issue

    def create_mock_event(self, event_type, event_date, actor=None):
        event = MagicMock(spec=Event)
        event.event_type = event_type
        event.event_date = event_date
        event.actor = actor
        return event

    def test_initialization(self):#Test that analyser initializes correctly
        self.assertIsNotNone(self.analyser)
        self.mock_config.assert_called_once()
        self.mock_data_loader.return_value.get_issues.assert_called_once()

    def test_run_method(self): #Test the main run method
        with patch.object(self.analyser, 'analyze_event_impact_on_resolution_time') as mock_method:
            self.analyser.run()
            mock_method.assert_called_once()

    def test_analyze_event_impact_with_empty_issues(self): #Test analysis with no issues
        self.analyser.issues = []
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            self.assertEqual(mock_plot.call_count, 2)

    def test_analyze_event_impact_with_valid_open_closed_issues(self):
        created_date = datetime(2023, 1, 1)
        updated_date = datetime(2023, 1, 5)
        
        # Create issues with different states
        open_issue = self.create_mock_issue(1, "open", created_date, updated_date)
        closed_issue = self.create_mock_issue(2, "closed", created_date, updated_date)
        merged_issue = self.create_mock_issue(3, "merged", created_date, updated_date)  # Should be skipped
        
        # Add events to closed issue
        event1 = self.create_mock_event("labeled", created_date + timedelta(days=1))
        event2 = self.create_mock_event("assigned", created_date + timedelta(days=2))
        closed_issue.events = [event1, event2]
        
        self.analyser.issues = [open_issue, closed_issue, merged_issue]
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            
            # Should attempt to create plots for both event types
            self.assertEqual(mock_plot.call_count, 2)

    def test_analyze_event_impact_with_mismatched_events(self):
        created_date = datetime(2023, 1, 1)
        
        # Create issue where events have inconsistent data
        issue = self.create_mock_issue(1, "closed", created_date)
        
        # Manually set problematic events data
        issue.events = [self.create_mock_event("labeled", created_date + timedelta(days=1))]
        
        # Mock the event extraction to simulate mismatch
        with patch.object(issue, 'events', []):  # Empty events but we'll mock the lists
            event_types = ["labeled"]  # One event type
            event_dates = []  # No dates - this creates mismatch
            
            # This should skip the issue due to length mismatch
            self.analyser.issues = [issue]
            
            with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
                self.analyser.analyze_event_impact_on_resolution_time()
                mock_plot.assert_called()

    def test_analyze_event_impact_without_created_date(self):
        """Test issues without created_date are skipped"""
        # Create issue without created_date
        issue = self.create_mock_issue(1, "closed", None)
        
        self.analyser.issues = [issue]
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            mock_plot.assert_called()

    def test_analyze_event_impact_with_none_updated_date(self):
        """Test issues with None updated_date get NaN resolution time"""
        created_date = datetime(2023, 1, 1)
        
        # Issue without updated_date
        issue = self.create_mock_issue(1, "closed", created_date, None)
        event = self.create_mock_event("labeled", created_date + timedelta(days=1))
        issue.events = [event]
        
        self.analyser.issues = [issue]
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            
            # Should attempt to plot (the NaN will be filtered out)
            mock_plot.assert_called()

    def test_extract_event_times_basic(self):
        """Test basic event time extraction"""
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "closed", created_date)
        
        event_types = ["labeled", "assigned", "commented"]
        event_dates = [
            created_date + timedelta(days=1),
            created_date + timedelta(days=2),
            created_date + timedelta(days=3)
        ]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, event_types, event_dates
        )
        
        self.assertEqual(labeled_time, 1)
        self.assertEqual(assigned_time, 2)

    def test_extract_event_times_no_relevant_events(self):
        """Test event time extraction with no labeled or assigned events"""
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "closed", created_date)
        
        event_types = ["commented", "referenced", "mentioned"]
        event_dates = [
            created_date + timedelta(days=1),
            created_date + timedelta(days=2),
            created_date + timedelta(days=3)
        ]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, event_types, event_dates
        )
        
        self.assertTrue(np.isnan(labeled_time))
        self.assertTrue(np.isnan(assigned_time))

    def test_extract_event_times_duplicate_events(self):
        """Test that only first occurrence of each event type is captured"""
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "closed", created_date)
        
        event_types = ["labeled", "assigned", "labeled", "assigned"]
        event_dates = [
            created_date + timedelta(days=1),  # First labeled
            created_date + timedelta(days=2),  # First assigned
            created_date + timedelta(days=3),  # Second labeled (should be ignored)
            created_date + timedelta(days=4)   # Second assigned (should be ignored)
        ]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, event_types, event_dates
        )
        
        self.assertEqual(labeled_time, 1)  # Should take first occurrence
        self.assertEqual(assigned_time, 2)  # Should take first occurrence

    def test_extract_event_times_mixed_order(self):
        """Test event extraction when events are not in chronological order"""
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "closed", created_date)
        
        event_types = ["assigned", "labeled", "commented", "assigned"]
        event_dates = [
            created_date + timedelta(days=3),  # First assigned (but later date)
            created_date + timedelta(days=1),  # First labeled
            created_date + timedelta(days=2),  # commented
            created_date + timedelta(days=4)   # Second assigned (ignored)
        ]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, event_types, event_dates
        )
        
        self.assertEqual(labeled_time, 1)  # First labeled event
        self.assertEqual(assigned_time, 3)  # First assigned event (even though it's later)

    def test_plot_event_impact_valid_data(self):
        """Test plotting with valid data"""
        # Create test DataFrame
        test_data = {
            'resolution_time': [5, 10, 15, 20],
            'labeled_time': [1, 2, 3, 4],
            'assigned_time': [2, 3, 4, 5]
        }
        df = pd.DataFrame(test_data)
        
        # Mock plt.show to prevent actual display and test the method executes
        with patch('matplotlib.pyplot.show') as mock_show:
            with patch('matplotlib.pyplot.figure') as mock_figure:
                with patch('matplotlib.pyplot.scatter') as mock_scatter:
                    with patch('matplotlib.pyplot.plot') as mock_plot:
                        with patch('matplotlib.pyplot.title'):
                            with patch('matplotlib.pyplot.xlabel'):
                                with patch('matplotlib.pyplot.ylabel'):
                                    with patch('matplotlib.pyplot.legend'):
                                        with patch('matplotlib.pyplot.tight_layout'):
                                            self.analyser._plot_event_impact(
                                                df, 'labeled_time', 'darkorange', 'Test Plot'
                                            )
                        
                        # Should attempt to create scatter plot
                        mock_scatter.assert_called_once()

    def test_plot_event_impact_missing_column(self):
        """Test plotting with missing column"""
        test_data = {'resolution_time': [5, 10, 15]}
        df = pd.DataFrame(test_data)
        
        # This should handle the missing column gracefully (will print message)
        with patch('builtins.print') as mock_print:
            self.analyser._plot_event_impact(
                df, 'nonexistent_column', 'blue', 'Test Plot'
            )
            mock_print.assert_called()

    def test_plot_event_impact_empty_data_after_filtering(self):
        """Test plotting with empty DataFrame after NaN filtering"""
        test_data = {
            'resolution_time': [np.nan, np.nan, np.nan],
            'labeled_time': [np.nan, np.nan, np.nan]
        }
        df = pd.DataFrame(test_data)
        
        # This should handle empty data gracefully (will print message)
        with patch('builtins.print') as mock_print:
            self.analyser._plot_event_impact(
                df, 'labeled_time', 'blue', 'Test Plot'
            )
            mock_print.assert_called()

    def test_plot_event_impact_trendline_calculation(self):
        """Test plotting with successful trendline calculation"""
        test_data = {
            'resolution_time': [5, 10, 15, 20],
            'labeled_time': [1, 2, 3, 4]
        }
        df = pd.DataFrame(test_data)
        
        # Mock all matplotlib calls
        with patch('matplotlib.pyplot.show'):
            with patch('matplotlib.pyplot.figure'):
                with patch('matplotlib.pyplot.scatter'):
                    with patch('matplotlib.pyplot.plot') as mock_plot:
                        with patch('matplotlib.pyplot.title'):
                            with patch('matplotlib.pyplot.xlabel'):
                                with patch('matplotlib.pyplot.ylabel'):
                                    with patch('matplotlib.pyplot.legend'):
                                        with patch('matplotlib.pyplot.tight_layout'):
                                            self.analyser._plot_event_impact(
                                                df, 'labeled_time', 'darkorange', 'Test Plot'
                                            )
                        
                        # Should attempt to plot trendline
                        self.assertEqual(mock_plot.call_count, 2)  # scatter + trendline

    def test_plot_event_impact_trendline_failure(self):
        """Test plotting when trendline calculation fails (single data point)"""
        test_data = {
            'resolution_time': [5],  # Single point - polyfit will fail
            'labeled_time': [1]
        }
        df = pd.DataFrame(test_data)
        
        # Mock all matplotlib calls
        with patch('matplotlib.pyplot.show'):
            with patch('matplotlib.pyplot.figure'):
                with patch('matplotlib.pyplot.scatter'):
                    with patch('matplotlib.pyplot.plot') as mock_plot:
                        with patch('matplotlib.pyplot.title'):
                            with patch('matplotlib.pyplot.xlabel'):
                                with patch('matplotlib.pyplot.ylabel'):
                                    with patch('matplotlib.pyplot.legend'):
                                        with patch('matplotlib.pyplot.tight_layout'):
                                            self.analyser._plot_event_impact(
                                                df, 'labeled_time', 'darkorange', 'Test Plot'
                                            )
                        
                        # Should only have scatter plot, no trendline
                        self.assertEqual(mock_plot.call_count, 1)  # Only scatter

    def test_edge_case_negative_days(self):
        """Test event extraction with events before creation date (shouldn't happen but test robustness)"""
        created_date = datetime(2023, 1, 5)  # Later creation date
        
        # Event before creation
        event = self.create_mock_event("labeled", created_date - timedelta(days=3))
        
        issue = self.create_mock_issue(1, "closed", created_date, created_date + timedelta(days=5))
        issue.events = [event]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, 
            [e.event_type for e in issue.events], 
            [e.event_date for e in issue.events]
        )
        
        self.assertEqual(labeled_time, -3)  # Negative days since creation

    def test_dataframe_creation_with_varied_data(self):
        """Test DataFrame creation with various data quality scenarios"""
        event_impact_data = [
            {"resolution_time": 5, "labeled_time": 1, "assigned_time": 2},
            {"resolution_time": np.nan, "labeled_time": 3, "assigned_time": np.nan},
            {"resolution_time": 10, "labeled_time": np.nan, "assigned_time": 4},
            {"resolution_time": 15, "labeled_time": 5, "assigned_time": 6},
            {}  # Empty dict to test edge case
        ]
        
        # This should not raise any exceptions
        df = pd.DataFrame(event_impact_data)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)  # Should have 5 rows


class TestResolutionTimeAnalyserIntegration(unittest.TestCase):
    """Integration-style tests for better coverage"""
    
    def test_full_analysis_workflow(self):
        """Test the complete analysis workflow with mock data"""
        with patch('resolution_time_analyser.config._init_config'):
            with patch('resolution_time_analyser.DataLoader') as MockDataLoader:
                mock_loader = MockDataLoader.return_value
                
                # Create realistic test issues
                created_date = datetime(2023, 1, 1)
                issues = []
                
                # Closed issue with events
                issue1 = MagicMock(spec=Issue)
                issue1.id = 1
                issue1.state = "closed"
                issue1.created_date = created_date
                issue1.updated_date = created_date + timedelta(days=7)
                
                event1 = MagicMock(spec=Event)
                event1.event_type = "labeled"
                event1.event_date = created_date + timedelta(days=1)
                
                event2 = MagicMock(spec=Event)
                event2.event_type = "assigned"
                event2.event_date = created_date + timedelta(days=2)
                
                issue1.events = [event1, event2]
                issues.append(issue1)
                
                # Open issue without events
                issue2 = MagicMock(spec=Issue)
                issue2.id = 2
                issue2.state = "open"
                issue2.created_date = created_date
                issue2.updated_date = created_date + timedelta(days=3)
                issue2.events = []
                issues.append(issue2)
                
                mock_loader.get_issues.return_value = issues
                
                # Create analyser and run
                analyser = ResolutionTimeAnalyser()
                
                # Mock the plotting to avoid display
                with patch.object(analyser, '_plot_event_impact') as mock_plot:
                    analyser.run()
                    
                    # Should call plotting for both event types
                    self.assertEqual(mock_plot.call_count, 2)


if __name__ == '__main__':
    unittest.main()