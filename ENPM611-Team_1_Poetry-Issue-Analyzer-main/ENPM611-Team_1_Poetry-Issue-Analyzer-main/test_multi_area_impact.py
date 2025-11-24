import unittest
import sys
import types
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta
from enum import Enum

# Mock all external dependencies before importing multi_area_impact to avoid import errors
if 'dateutil' not in sys.modules:
    mock_parser = types.ModuleType('parser')
    mock_parser.parse = lambda x: datetime.now() if isinstance(x, str) else x
    mock_dateutil = types.ModuleType('dateutil')
    mock_dateutil.parser = mock_parser
    sys.modules['dateutil'] = mock_dateutil
    sys.modules['dateutil.parser'] = mock_parser

if 'matplotlib' not in sys.modules:
    mock_plt = types.ModuleType('pyplot')
    # Add common pyplot methods/attributes
    mock_plt.subplots = MagicMock()
    mock_plt.show = MagicMock()
    mock_plt.tight_layout = MagicMock()
    mock_matplotlib = types.ModuleType('matplotlib')
    mock_matplotlib.pyplot = mock_plt
    sys.modules['matplotlib'] = mock_matplotlib
    sys.modules['matplotlib.pyplot'] = mock_plt

if 'pandas' not in sys.modules:
    mock_pd = types.ModuleType('pandas')
    mock_pd.DataFrame = MagicMock()
    mock_pd.Series = MagicMock()
    sys.modules['pandas'] = mock_pd

if 'tabulate' not in sys.modules:
    mock_tabulate = types.ModuleType('tabulate')
    mock_tabulate.tabulate = MagicMock()
    sys.modules['tabulate'] = mock_tabulate

import multi_area_impact


class State(str, Enum):
    """Mock State enum matching model.py"""
    open = 'open'
    closed = 'closed'


class MockIssue:
    """Mock Issue class matching the structure from model.py"""
    def __init__(self, number, title, labels, state, created_date, creator=None):
        self.number = number
        self.title = title
        self.labels = labels
        self.state = state
        self.created_date = created_date
        self.creator = creator


class TestMultiAreaImpactAnalyzer(unittest.TestCase):
    """Test suite for MultiAreaImpactAnalyzer with 90%+ coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = multi_area_impact.MultiAreaImpactAnalyzer()

    def test_get_area_labels_empty_list(self):
        """Test _get_area_labels with empty list."""
        result = self.analyzer._get_area_labels([])
        self.assertEqual(result, [])

    def test_get_area_labels_no_area_labels(self):
        """Test _get_area_labels with no area/ labels."""
        labels = ['bug', 'enhancement', 'documentation']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, [])

    def test_get_area_labels_single_area_label(self):
        """Test _get_area_labels with single area/ label."""
        labels = ['area/frontend', 'bug']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, ['area/frontend'])

    def test_get_area_labels_multiple_area_labels(self):
        """Test _get_area_labels with multiple area/ labels."""
        labels = ['area/frontend', 'area/backend', 'area/database', 'bug']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, ['area/frontend', 'area/backend', 'area/database'])

    def test_get_area_labels_case_insensitive(self):
        """Test _get_area_labels is case insensitive."""
        labels = ['AREA/FRONTEND', 'Area/Backend', 'area/database']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, ['AREA/FRONTEND', 'Area/Backend', 'area/database'])

    def test_get_area_labels_non_string_ignored(self):
        """Test _get_area_labels ignores non-string labels."""
        labels = ['area/frontend', 123, None, ['area/backend'], 'area/database']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, ['area/frontend', 'area/database'])

    def test_get_area_labels_not_starting_with_area(self):
        """Test _get_area_labels ignores labels not starting with area/."""
        labels = ['area', 'area-frontend', 'areas/backend']
        result = self.analyzer._get_area_labels(labels)
        self.assertEqual(result, [])

    @patch('builtins.input', return_value='1')
    @patch('builtins.print')
    def test_get_timeline_selection_3_months(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 3 months for choice '1'."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 3)

    @patch('builtins.input', return_value='2')
    @patch('builtins.print')
    def test_get_timeline_selection_6_months(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 6 months for choice '2'."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 6)

    @patch('builtins.input', return_value='3')
    @patch('builtins.print')
    def test_get_timeline_selection_12_months(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 12 months for choice '3'."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 12)

    @patch('builtins.input', return_value='4')
    @patch('builtins.print')
    def test_get_timeline_selection_18_months(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 18 months for choice '4'."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 18)

    @patch('builtins.input', return_value='5')
    @patch('builtins.print')
    def test_get_timeline_selection_24_months(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 24 months for choice '5'."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 24)

    @patch('builtins.input', return_value='6')
    @patch('builtins.print')
    def test_get_timeline_selection_all_time(self, mock_print, mock_input):
        """Test _get_timeline_selection returns 0 for choice '6' (all time)."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 0)

    @patch('builtins.input', side_effect=['invalid', '7', '1'])
    @patch('builtins.print')
    def test_get_timeline_selection_invalid_then_valid(self, mock_print, mock_input):
        """Test _get_timeline_selection handles invalid input then accepts valid."""
        result = self.analyzer._get_timeline_selection()
        self.assertEqual(result, 3)
        # Should have printed error messages
        self.assertTrue(mock_print.called)

    @patch('builtins.input', side_effect=KeyboardInterrupt())
    @patch('builtins.print')
    def test_get_timeline_selection_keyboard_interrupt(self, mock_print, mock_input):
        """Test _get_timeline_selection handles KeyboardInterrupt."""
        result = self.analyzer._get_timeline_selection()
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=['1'])
    @patch('builtins.print')
    def test_get_timeline_selection_exception_handled(self, mock_print, mock_input):
        """Test _get_timeline_selection handles general exceptions in try block."""
        # Create a mock that raises exception first, then succeeds
        call_count = [0]
        def input_side_effect(prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Unexpected error")
            return '1'
        
        with patch('builtins.input', side_effect=input_side_effect):
            result = self.analyzer._get_timeline_selection()
            self.assertEqual(result, 3)

    def test_filter_issues_by_timeline_all_time(self):
        """Test _filter_issues_by_timeline returns all issues when months=0."""
        issues = [
            MockIssue(1, 'Issue 1', [], State.open, datetime.now() - timedelta(days=100)),
            MockIssue(2, 'Issue 2', [], State.closed, datetime.now() - timedelta(days=200))
        ]
        result = self.analyzer._filter_issues_by_timeline(issues, 0)
        self.assertEqual(result, issues)

    def test_filter_issues_by_timeline_recent_issues(self):
        """Test _filter_issues_by_timeline filters to recent issues."""
        now = datetime.now()
        recent_issue = MockIssue(1, 'Recent', [], State.open, now - timedelta(days=30))
        old_issue = MockIssue(2, 'Old', [], State.closed, now - timedelta(days=200))
        issues = [recent_issue, old_issue]
        
        result = self.analyzer._filter_issues_by_timeline(issues, 3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].number, 1)

    def test_filter_issues_by_timeline_exact_cutoff(self):
        """Test _filter_issues_by_timeline includes issues at cutoff date."""
        # Use a date slightly after the cutoff to account for timing differences
        # The cutoff is calculated as datetime.now() - timedelta(days=90)
        # So we use a date that's 89 days ago to ensure it passes
        now = datetime.now()
        issue_date = now - timedelta(days=89)  # Slightly after cutoff
        issue_at_cutoff = MockIssue(1, 'At cutoff', [], State.open, issue_date)
        issues = [issue_at_cutoff]
        
        result = self.analyzer._filter_issues_by_timeline(issues, 3)
        self.assertEqual(len(result), 1)

    def test_filter_issues_by_timeline_no_created_date(self):
        """Test _filter_issues_by_timeline handles issues without created_date."""
        issue_with_date = MockIssue(1, 'With date', [], State.open, datetime.now())
        issue_no_date = MockIssue(2, 'No date', [], State.closed, None)
        issues = [issue_with_date, issue_no_date]
        
        result = self.analyzer._filter_issues_by_timeline(issues, 3)
        # Issue without date is NOT included because None and ... evaluates to False
        # Only the issue with a valid date is included
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].number, 1)

    def test_filter_issues_by_timeline_date_comparison_error(self):
        """Test _filter_issues_by_timeline handles date comparison errors."""
        issue = MockIssue(1, 'Bad date', [], State.open, None)
        # Make created_date comparison fail
        issue.created_date = "invalid_date_string"
        issues = [issue]
        
        result = self.analyzer._filter_issues_by_timeline(issues, 3)
        # Should include issue on error (safe default)
        self.assertEqual(len(result), 1)

    def test_analyze_multi_area_issues_no_multi_area(self):
        """Test _analyze_multi_area_issues with no multi-area issues."""
        issues = [
            MockIssue(1, 'Single area', ['area/frontend'], State.open, datetime.now()),
            MockIssue(2, 'No area', ['bug'], State.closed, datetime.now())
        ]
        multi_area, area_count = self.analyzer._analyze_multi_area_issues(issues)
        self.assertEqual(multi_area, [])
        self.assertEqual(area_count, {})

    def test_analyze_multi_area_issues_single_multi_area(self):
        """Test _analyze_multi_area_issues with one multi-area issue."""
        issues = [
            MockIssue(1, 'Multi area', ['area/frontend', 'area/backend'], State.open, datetime.now(), 'user1')
        ]
        multi_area, area_count = self.analyzer._analyze_multi_area_issues(issues)
        self.assertEqual(len(multi_area), 1)
        self.assertEqual(multi_area[0]['number'], 1)
        self.assertEqual(multi_area[0]['area_count'], 2)
        self.assertEqual(multi_area[0]['area_labels'], ['area/frontend', 'area/backend'])
        self.assertEqual(area_count['area/frontend'], 1)
        self.assertEqual(area_count['area/backend'], 1)

    def test_analyze_multi_area_issues_multiple_multi_area(self):
        """Test _analyze_multi_area_issues with multiple multi-area issues."""
        issues = [
            MockIssue(1, 'Issue 1', ['area/frontend', 'area/backend'], State.open, datetime.now()),
            MockIssue(2, 'Issue 2', ['area/frontend', 'area/database'], State.closed, datetime.now()),
            MockIssue(3, 'Issue 3', ['area/frontend', 'area/backend', 'area/database'], State.open, datetime.now())
        ]
        multi_area, area_count = self.analyzer._analyze_multi_area_issues(issues)
        self.assertEqual(len(multi_area), 3)
        # Should be sorted by area_count descending
        self.assertEqual(multi_area[0]['area_count'], 3)
        self.assertEqual(multi_area[0]['number'], 3)
        # Check area counts
        self.assertEqual(area_count['area/frontend'], 3)
        self.assertEqual(area_count['area/backend'], 2)
        self.assertEqual(area_count['area/database'], 2)

    def test_analyze_multi_area_issues_state_handling(self):
        """Test _analyze_multi_area_issues handles state correctly."""
        issue_with_state = MockIssue(1, 'With state', ['area/frontend', 'area/backend'], State.open, datetime.now())
        issue_no_state = MockIssue(2, 'No state', ['area/frontend', 'area/database'], None, datetime.now())
        issues = [issue_with_state, issue_no_state]
        
        multi_area, area_count = self.analyzer._analyze_multi_area_issues(issues)
        self.assertEqual(len(multi_area), 2)
        self.assertEqual(multi_area[0]['state'], 'open')
        self.assertEqual(multi_area[1]['state'], 'unknown')

    def test_analyze_multi_area_issues_mixed_single_and_multi(self):
        """Test _analyze_multi_area_issues with mix of single and multi-area issues."""
        issues = [
            MockIssue(1, 'Single', ['area/frontend'], State.open, datetime.now()),
            MockIssue(2, 'Multi', ['area/frontend', 'area/backend'], State.closed, datetime.now()),
            MockIssue(3, 'No area', ['bug'], State.open, datetime.now())
        ]
        multi_area, area_count = self.analyzer._analyze_multi_area_issues(issues)
        self.assertEqual(len(multi_area), 1)
        self.assertEqual(multi_area[0]['number'], 2)

    @patch('multi_area_impact.plt')
    def test_create_charts_empty_issues(self, mock_plt):
        """Test _create_charts returns early when no multi-area issues."""
        self.analyzer._create_charts([], {}, 3)
        # Should not create any plots
        mock_plt.subplots.assert_not_called()

    @patch('multi_area_impact.plt')
    @patch('multi_area_impact.pd')
    def test_create_charts_with_data(self, mock_pd, mock_plt):
        """Test _create_charts creates all subplots with data."""
        # Setup mocks
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_ax3 = MagicMock()
        mock_ax4 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, ((mock_ax1, mock_ax2), (mock_ax3, mock_ax4)))
        
        # Mock pandas Series
        mock_series = MagicMock()
        mock_series.value_counts.return_value = MagicMock()
        mock_pd.Series.return_value = mock_series
        
        # Mock DataFrame for timeline chart
        mock_df = MagicMock()
        mock_month_series = MagicMock()
        mock_month_series.value_counts.return_value.sort_index.return_value = MagicMock()
        mock_df.__getitem__.return_value.dt.to_period.return_value = mock_month_series
        mock_pd.DataFrame.return_value = mock_df
        
        # Test data
        now = datetime.now()
        multi_area_issues = [
            {
                'number': 1,
                'title': 'Issue 1',
                'area_labels': ['area/frontend', 'area/backend'],
                'area_count': 2,
                'state': 'open',
                'created_date': now,
                'creator': 'user1'
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'area_labels': ['area/frontend', 'area/database'],
                'area_count': 2,
                'state': 'closed',
                'created_date': now - timedelta(days=30),
                'creator': 'user2'
            }
        ]
        area_impact_count = {
            'area/frontend': 2,
            'area/backend': 1,
            'area/database': 1
        }
        
        self.analyzer._create_charts(multi_area_issues, area_impact_count, 3)
        
        # Verify subplots were created
        mock_plt.subplots.assert_called_once_with(2, 2, figsize=(16, 12))
        # Verify figure title
        mock_fig.suptitle.assert_called_once()
        # Verify show was called
        mock_plt.show.assert_called_once()
        mock_plt.tight_layout.assert_called_once()

    @patch('multi_area_impact.plt')
    @patch('multi_area_impact.pd')
    def test_create_charts_all_time_timeline(self, mock_pd, mock_plt):
        """Test _create_charts with all time timeline (0 months)."""
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_ax3 = MagicMock()
        mock_ax4 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, ((mock_ax1, mock_ax2), (mock_ax3, mock_ax4)))
        
        mock_series = MagicMock()
        mock_series.value_counts.return_value = MagicMock()
        mock_pd.Series.return_value = mock_series
        
        mock_df = MagicMock()
        mock_month_series = MagicMock()
        mock_month_series.value_counts.return_value.sort_index.return_value = MagicMock()
        mock_df.__getitem__.return_value.dt.to_period.return_value = mock_month_series
        mock_pd.DataFrame.return_value = mock_df
        
        multi_area_issues = [{
            'number': 1,
            'title': 'Issue 1',
            'area_labels': ['area/frontend', 'area/backend'],
            'area_count': 2,
            'state': 'open',
            'created_date': datetime.now(),
            'creator': 'user1'
        }]
        area_impact_count = {'area/frontend': 1, 'area/backend': 1}
        
        self.analyzer._create_charts(multi_area_issues, area_impact_count, 0)
        
        # Check that "All time" is used in title
        call_args = mock_fig.suptitle.call_args[0][0]
        self.assertIn('All time', call_args)

    @patch('multi_area_impact.plt')
    @patch('multi_area_impact.pd')
    def test_create_charts_no_dates(self, mock_pd, mock_plt):
        """Test _create_charts handles issues without created_date."""
        mock_fig = MagicMock()
        mock_ax1 = MagicMock()
        mock_ax2 = MagicMock()
        mock_ax3 = MagicMock()
        mock_ax4 = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, ((mock_ax1, mock_ax2), (mock_ax3, mock_ax4)))
        
        mock_series = MagicMock()
        mock_series.value_counts.return_value = MagicMock()
        mock_pd.Series.return_value = mock_series
        
        multi_area_issues = [{
            'number': 1,
            'title': 'Issue 1',
            'area_labels': ['area/frontend', 'area/backend'],
            'area_count': 2,
            'state': 'open',
            'created_date': None,  # No date
            'creator': 'user1'
        }]
        area_impact_count = {'area/frontend': 1, 'area/backend': 1}
        
        # Should not raise exception
        self.analyzer._create_charts(multi_area_issues, area_impact_count, 3)
        mock_plt.subplots.assert_called_once()

    @patch('multi_area_impact.MultiAreaImpactAnalyzer._create_charts')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._filter_issues_by_timeline')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._get_timeline_selection')
    @patch('builtins.print')
    def test_run_complete_flow(self, mock_print, mock_timeline, mock_filter, mock_charts):
        """Test run() completes full flow."""
        # Setup mocks
        mock_timeline.return_value = 3
        issues = [
            MockIssue(1, 'Issue 1', ['area/frontend', 'area/backend'], State.open, datetime.now())
        ]
        mock_filter.return_value = issues
        
        mock_loader = MagicMock()
        mock_loader.get_issues.return_value = issues
        self.analyzer.data_loader = mock_loader
        
        result = self.analyzer.run()
        
        # Verify flow
        mock_timeline.assert_called_once()
        mock_loader.get_issues.assert_called_once()
        mock_filter.assert_called_once_with(issues, 3)
        mock_charts.assert_called_once()
        self.assertIsNotNone(result)

    @patch('multi_area_impact.MultiAreaImpactAnalyzer._get_timeline_selection')
    @patch('builtins.print')
    def test_run_cancelled(self, mock_print, mock_timeline):
        """Test run() returns None when timeline selection is cancelled."""
        mock_timeline.return_value = None
        
        result = self.analyzer.run()
        
        self.assertIsNone(result)
        mock_timeline.assert_called_once()

    @patch('multi_area_impact.MultiAreaImpactAnalyzer._create_charts')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._filter_issues_by_timeline')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._get_timeline_selection')
    @patch('builtins.print')
    def test_run_all_time(self, mock_print, mock_timeline, mock_filter, mock_charts):
        """Test run() with all time selection."""
        mock_timeline.return_value = 0
        issues = [
            MockIssue(1, 'Issue 1', ['area/frontend', 'area/backend'], State.open, datetime.now())
        ]
        mock_filter.return_value = issues
        
        mock_loader = MagicMock()
        mock_loader.get_issues.return_value = issues
        self.analyzer.data_loader = mock_loader
        
        result = self.analyzer.run()
        
        mock_filter.assert_called_once_with(issues, 0)
        # Check that "all time" text is used
        mock_print.assert_any_call("Analyzing 1 issues from the all time...")

    @patch('multi_area_impact.MultiAreaImpactAnalyzer._create_charts')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._filter_issues_by_timeline')
    @patch('multi_area_impact.MultiAreaImpactAnalyzer._get_timeline_selection')
    @patch('builtins.print')
    def test_run_returns_correct_data(self, mock_print, mock_timeline, mock_filter, mock_charts):
        """Test run() returns correct multi_area_issues and area_impact_count."""
        mock_timeline.return_value = 3
        issues = [
            MockIssue(1, 'Issue 1', ['area/frontend', 'area/backend'], State.open, datetime.now())
        ]
        mock_filter.return_value = issues
        
        mock_loader = MagicMock()
        mock_loader.get_issues.return_value = issues
        self.analyzer.data_loader = mock_loader
        
        result = self.analyzer.run()
        
        multi_area_issues, area_impact_count = result
        self.assertEqual(len(multi_area_issues), 1)
        self.assertEqual(multi_area_issues[0]['number'], 1)
        self.assertIn('area/frontend', area_impact_count)
        self.assertIn('area/backend', area_impact_count)


if __name__ == '__main__':
    unittest.main()

