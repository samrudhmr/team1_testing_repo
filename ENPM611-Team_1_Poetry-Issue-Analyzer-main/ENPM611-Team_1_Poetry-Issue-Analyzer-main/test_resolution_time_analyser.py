import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import resolution_time_analyser
import model

class TestResolutionTimeAnalyser(unittest.TestCase):

    def setUp(self):
        self.config_patcher = patch('resolution_time_analyser.config._init_config')
        self.data_loader_patcher = patch('resolution_time_analyser.DataLoader')
        
        self.mock_config = self.config_patcher.start()
        self.mock_data_loader = self.data_loader_patcher.start()
        
        self.analyser = resolution_time_analyser.ResolutionTimeAnalyser()
        
    def tearDown(self):
        self.config_patcher.stop()
        self.data_loader_patcher.stop()

    def create_mock_issue(self, issue_id, state, created_date, updated_date=None, events=None):
        issue = MagicMock(spec=model.Issue)
        issue.id = issue_id
        issue.state = state
        issue.created_date = created_date
        issue.updated_date = updated_date or created_date
        issue.events = events or []
        return issue

    def create_mock_event(self, event_type, event_date, actor=None):
        event = MagicMock(spec=model.Event)
        event.event_type = event_type
        event.event_date = event_date
        event.actor = actor
        return event

    def test_run_method(self):
        with patch.object(self.analyser, 'analyze_event_impact_on_resolution_time') as mock_method:
            self.analyser.run()
            mock_method.assert_called_once()

    def test_analyze_event_impact_with_valid_open_closed_issues(self):
        created_date = datetime(2023, 1, 1)
        updated_date = datetime(2023, 1, 5)
        
        open_issue = self.create_mock_issue(1, "open", created_date, updated_date)
        closed_issue = self.create_mock_issue(2, "closed", created_date, updated_date)
        
        event1 = self.create_mock_event("labeled", created_date + timedelta(days=1))
        closed_issue.events = [event1]
        
        self.analyser.issues = [open_issue, closed_issue]
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            self.assertEqual(mock_plot.call_count, 2)

    def test_analyze_skips_invalid_issues(self):
        """Test that the analyzer skips issues based on validation logic."""
        created_date = datetime(2023, 1, 1)
        
        # 1. Skip: State is not open/closed
        issue_draft = self.create_mock_issue(1, "draft", created_date)
        
        # 2. Skip: No created_date
        issue_no_date = self.create_mock_issue(2, "open", None)
        
        # 3. Skip: Mismatched events (simulate corruption where types != dates length)
        # Note: We have to mock the events list carefully to trigger the len check inside the method
        issue_mismatch = self.create_mock_issue(3, "open", created_date)
        # We need events that produce types/dates lists of different lengths
        # The code derives these lists: [e.event_type for e in issue.events if e.event_type]
        # So we create an event with a type but no date, or vice versa, but the code checks
        # "if e.event_type" and "if e.event_date".
        # To fail `len(types) != len(dates)`, we need an event that has a type but NO date (or vice versa).
        
        e1 = MagicMock(spec=model.Event)
        e1.event_type = "labeled"
        e1.event_date = None # Has type, no date -> types len 1, dates len 0
        issue_mismatch.events = [e1]

        # 4. Valid issue to ensure loop continues
        issue_valid = self.create_mock_issue(4, "closed", created_date, created_date)
        issue_valid.events = [self.create_mock_event("labeled", created_date + timedelta(days=1))]

        self.analyser.issues = [issue_draft, issue_no_date, issue_mismatch, issue_valid]

        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            
            # Should still plot, but the dataframe passed should only contain data from issue 4
            self.assertEqual(mock_plot.call_count, 2)
            
            # Check the data passed to the plot. Args: (df, event_col, ...)
            # We get the first call args
            df_arg = mock_plot.call_args[0][0]
            self.assertEqual(len(df_arg), 1) # Only 1 valid issue
            self.assertEqual(df_arg.iloc[0]['labeled_time'], 1.0)

    def test_analyze_handles_no_updated_date(self):
        """Test calculating resolution time when updated_date is missing."""
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "open", created_date, None) # updated_date is None
        
        e1 = self.create_mock_event("labeled", created_date + timedelta(days=1))
        issue.events = [e1]
        
        self.analyser.issues = [issue]
        
        with patch.object(self.analyser, '_plot_event_impact') as mock_plot:
            self.analyser.analyze_event_impact_on_resolution_time()
            
            df_arg = mock_plot.call_args[0][0]
            # Resolution time should be np.nan
            self.assertTrue(np.isnan(df_arg.iloc[0]['resolution_time']))

    def test_extract_event_times_basic(self):
        created_date = datetime(2023, 1, 1)
        issue = self.create_mock_issue(1, "closed", created_date)
        
        event_types = ["labeled", "assigned"]
        event_dates = [
            created_date + timedelta(days=1),
            created_date + timedelta(days=2)
        ]
        
        labeled_time, assigned_time = self.analyser._extract_event_times(
            issue, event_types, event_dates
        )
        
        self.assertEqual(labeled_time, 1)
        self.assertEqual(assigned_time, 2)

    def test_plot_event_impact_missing_column(self):
        """Test _plot_event_impact returns early if column is missing."""
        df = pd.DataFrame({'a': [1, 2]})
        
        # We patch print to verify it printed the error message, ensuring that branch was hit
        with patch('builtins.print') as mock_print:
            with patch('matplotlib.pyplot.show') as mock_show:
                self.analyser._plot_event_impact(df, "missing_col", "red", "Title")
                
                # Should print error and NOT show plot
                mock_print.assert_called_with("No column 'missing_col' found in data.")
                mock_show.assert_not_called()

    def test_plot_event_impact_empty_filtered_data(self):
        """Test _plot_event_impact returns early if data is empty after NaNs removed."""
        # DataFrame has columns but values are NaN
        df = pd.DataFrame({
            'target_col': [np.nan, np.nan],
            'resolution_time': [1, 2]
        })
        
        with patch('builtins.print') as mock_print:
            with patch('matplotlib.pyplot.show') as mock_show:
                self.analyser._plot_event_impact(df, "target_col", "red", "Title")
                
                mock_print.assert_called_with("No valid data for 'target_col' to plot.")
                mock_show.assert_not_called()

    def test_plot_event_impact_trendline_failure(self):
        """Test plotting with single data point (trendline warning/pass)."""
        test_data = {
            'resolution_time': [5],
            'labeled_time': [1]
        }
        df = pd.DataFrame(test_data)
        
        with patch('matplotlib.pyplot.show'):
            with patch('matplotlib.pyplot.figure'):
                with patch('matplotlib.pyplot.scatter'):
                    with patch('matplotlib.pyplot.plot') as mock_plot:
                        self.analyser._plot_event_impact(
                            df, 'labeled_time', 'darkorange', 'Test Plot'
                        )
                        # Should still plot even if polyfit behaves oddly on 1 point
                        self.assertEqual(mock_plot.call_count, 1)

    def test_plot_event_impact_exception_handling(self):
        """Test that the try/except block catches exceptions during trendline calculation."""
        test_data = {
            'resolution_time': [5, 10],
            'labeled_time': [1, 2]
        }
        df = pd.DataFrame(test_data)
        
        with patch('matplotlib.pyplot.show'):
            with patch('matplotlib.pyplot.figure'):
                with patch('matplotlib.pyplot.scatter'):
                    with patch('matplotlib.pyplot.plot') as mock_plot:
                        # Force np.polyfit to raise an Exception
                        with patch('numpy.polyfit', side_effect=Exception("Boom")):
                            self.analyser._plot_event_impact(
                                df, 'labeled_time', 'darkorange', 'Test Plot'
                            )
                            
                        # The trendline plot should NOT be called because of exception
                        mock_plot.assert_not_called()

if __name__ == '__main__':
    unittest.main()