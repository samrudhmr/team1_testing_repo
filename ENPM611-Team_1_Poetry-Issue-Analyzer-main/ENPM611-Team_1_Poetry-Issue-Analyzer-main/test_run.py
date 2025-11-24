import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import importlib

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Prevent run.py from executing main logic on import by patching args and config
with patch('sys.argv', ['run.py', '--feature', '0']):
    with patch('example_analysis.ExampleAnalysis') as MockExample:
        with patch('most_active_categories_analyser.MostActiveCategoriesAnalyser') as MockCat:
            with patch('multi_area_impact.MultiAreaImpactAnalyzer') as MockMulti:
                with patch('top_user_activity.TopUserActivityAnalyser') as MockUser:
                    with patch('resolution_time_analyser.ResolutionTimeAnalyser') as MockRes:
                        with patch('config.overwrite_from_args'):
                            import run

class TestRun(unittest.TestCase):

    def test_parse_args_basic(self):
        test_args = ['--feature', '1']
        
        with patch('sys.argv', ['run.py'] + test_args):
            args = run.parse_args()
            self.assertEqual(args.feature, 1)

    def test_parse_args_all_optional_params(self):
        test_args = [
            '--feature', '2',
            '--user', 'testuser',
            '--label', 'bug',
            '--year', '2023',
            '--start-year', '2020',
            '--end-year', '2023',
            '--top', '10',
            '--type', 'Bug,Feature',
            '--labels', 'priority:high,security'
        ]
        
        with patch('sys.argv', ['run.py'] + test_args):
            args = run.parse_args()
            
            self.assertEqual(args.feature, 2)
            self.assertEqual(args.user, 'testuser')
            self.assertEqual(args.label, 'bug')
            self.assertEqual(args.year, 2023)
            self.assertEqual(args.start_year, 2020)
            self.assertEqual(args.end_year, 2023)
            self.assertEqual(args.top, 10)
            self.assertEqual(args.type, 'Bug,Feature')
            self.assertEqual(args.labels, 'priority:high,security')

    def test_parse_args_missing_required(self):
        test_args = []
        with patch('sys.argv', ['run.py'] + test_args):
            with self.assertRaises(SystemExit):
                run.parse_args()

    def test_feature_dispatch_mocked(self):
        # Reload run to trigger the dispatch logic with fresh mocks
        with patch('sys.argv', ['run.py', '--feature', '4']):
            with patch('resolution_time_analyser.ResolutionTimeAnalyser') as MockRes:
                with patch('config.overwrite_from_args'):
                    importlib.reload(run)
                    MockRes.return_value.run.assert_called_once()

    def test_feature_1_parameters(self):
        with patch('sys.argv', ['run.py', '--feature', '1', '--year', '2023']):
            with patch('most_active_categories_analyser.MostActiveCategoriesAnalyser') as MockCat:
                with patch('config.overwrite_from_args'):
                    importlib.reload(run)
                    call_args = MockCat.return_value.run.call_args
                    self.assertEqual(call_args.kwargs['year'], 2023)

    def test_invalid_feature(self):
        with patch('sys.argv', ['run.py', '--feature', '999']):
            with patch('builtins.print') as mock_print:
                with patch('config.overwrite_from_args'):
                    importlib.reload(run)
                    mock_print.assert_called_with('Need to specify which feature to run with --feature flag.')

if __name__ == '__main__':
    unittest.main()