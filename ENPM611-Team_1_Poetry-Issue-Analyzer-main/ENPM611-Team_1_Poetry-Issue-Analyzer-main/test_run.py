import unittest
from unittest.mock import patch, MagicMock
import argparse
import sys
import os

# Add the path to import the actual module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run import parse_args


class TestRun(unittest.TestCase):
    """Test cases for the run.py module"""

    def test_parse_args_basic(self):
        """Test basic argument parsing with required feature flag"""
        test_args = ['--feature', '1']
        
        with patch('sys.argv', ['run.py'] + test_args):
            args = parse_args()
            
            self.assertEqual(args.feature, 1)
            self.assertIsNone(args.user)
            self.assertIsNone(args.label)

    def test_parse_args_all_optional_params(self):
        """Test argument parsing with all optional parameters"""
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
            args = parse_args()
            
            self.assertEqual(args.feature, 2)
            self.assertEqual(args.user, 'testuser')
            self.assertEqual(args.label, 'bug')
            self.assertEqual(args.year, 2023)
            self.assertEqual(args.start_year, 2020)
            self.assertEqual(args.end_year, 2023)
            self.assertEqual(args.top, 10)
            self.assertEqual(args.type, 'Bug,Feature')
            self.assertEqual(args.labels, 'priority:high,security')

    def test_parse_args_short_flags(self):
        """Test argument parsing with short flag versions"""
        test_args = [
            '-f', '3',
            '-u', 'shortuser',
            '-l', 'shortlabel'
        ]
        
        with patch('sys.argv', ['run.py'] + test_args):
            args = parse_args()
            
            self.assertEqual(args.feature, 3)
            self.assertEqual(args.user, 'shortuser')
            self.assertEqual(args.label, 'shortlabel')

    def test_parse_args_missing_required(self):
        """Test that missing required feature flag raises error"""
        test_args = []  # No --feature flag
        
        with patch('sys.argv', ['run.py'] + test_args):
            with self.assertRaises(SystemExit):  # argparse exits on error
                parse_args()

    def test_parse_args_default_values(self):
        """Test that default values are set correctly"""
        test_args = ['--feature', '4']
        
        with patch('sys.argv', ['run.py'] + test_args):
            args = parse_args()
            
            self.assertEqual(args.feature, 4)
            self.assertIsNone(args.year)
            self.assertIsNone(args.start_year)
            self.assertIsNone(args.end_year)
            self.assertEqual(args.top, 5)  # Default value
            self.assertIsNone(args.type)
            self.assertIsNone(args.labels)

    def test_feature_dispatch(self):
        """Test that features are correctly dispatched"""
        # Mock all the analysis classes to avoid actual execution
        with patch('run.config.overwrite_from_args') as mock_config:
            with patch('run.ExampleAnalysis') as mock_example:
                with patch('run.MostActiveCategoriesAnalyser') as mock_categories:
                    with patch('run.MultiAreaImpactAnalyzer') as mock_multi:
                        with patch('run.TopUserActivityAnalyser') as mock_user:
                            with patch('run.ResolutionTimeAnalyser') as mock_resolution:
                                
                                # Test each feature
                                test_cases = [
                                    (0, mock_example),
                                    (1, mock_categories),
                                    (2, mock_multi),
                                    (3, mock_user),
                                    (4, mock_resolution)
                                ]
                                
                                for feature_num, mock_class in test_cases:
                                    with self.subTest(feature=feature_num):
                                        # Reset mocks
                                        mock_config.reset_mock()
                                        mock_class.reset_mock()
                                        
                                        # Mock argparse to return specific feature
                                        with patch('run.parse_args') as mock_parse:
                                            mock_args = MagicMock()
                                            mock_args.feature = feature_num
                                            mock_args.user = None
                                            mock_args.label = None
                                            mock_args.year = None
                                            mock_args.start_year = None
                                            mock_args.end_year = None
                                            mock_args.top = 5
                                            mock_args.type = None
                                            mock_args.labels = None
                                            mock_parse.return_value = mock_args
                                            
                                            # Import and execute the main part of run.py
                                            import run
                                            
                                            # Check that config was updated
                                            mock_config.assert_called_once_with(mock_args)
                                            
                                            # Check that the correct analysis was run
                                            if feature_num == 1:
                                                # Feature 1 has additional parameters
                                                mock_class.return_value.run.assert_called_once_with(
                                                    year=None,
                                                    start_year=None,
                                                    end_year=None,
                                                    top_n=5,
                                                    filter_type=None,
                                                    filter_labels=None
                                                )
                                            else:
                                                mock_class.return_value.run.assert_called_once()

    def test_invalid_feature(self):
        """Test behavior with invalid feature number"""
        with patch('run.config.overwrite_from_args'):
            with patch('run.parse_args') as mock_parse:
                mock_args = MagicMock()
                mock_args.feature = 999  # Invalid feature number
                mock_parse.return_value = mock_args
                
                with patch('builtins.print') as mock_print:
                    # Import and execute the main part of run.py
                    import run
                    
                    # Should print error message for invalid feature
                    mock_print.assert_called_with('Need to specify which feature to run with --feature flag.')

    def test_feature_1_with_parameters(self):
        """Test feature 1 with all parameters passed"""
        with patch('run.config.overwrite_from_args'):
            with patch('run.parse_args') as mock_parse:
                with patch('run.MostActiveCategoriesAnalyser') as mock_categories:
                    
                    mock_args = MagicMock()
                    mock_args.feature = 1
                    mock_args.user = None
                    mock_args.label = None
                    mock_args.year = 2023
                    mock_args.start_year = 2020
                    mock_args.end_year = 2023
                    mock_args.top = 10
                    mock_args.type = 'Bug,Feature'
                    mock_args.labels = 'priority:high'
                    mock_parse.return_value = mock_args
                    
                    # Import and execute
                    import run
                    
                    # Check that feature 1 was called with all parameters
                    mock_categories.return_value.run.assert_called_once_with(
                        year=2023,
                        start_year=2020,
                        end_year=2023,
                        top_n=10,
                        filter_type='Bug,Feature',
                        filter_labels='priority:high'
                    )


if __name__ == '__main__':
    unittest.main()