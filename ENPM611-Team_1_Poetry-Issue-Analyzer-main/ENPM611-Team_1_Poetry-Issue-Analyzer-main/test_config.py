import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import os
import tempfile

import config


class TestConfig(unittest.TestCase):
    """Test suite for config.py with 100% statement coverage."""

    def setUp(self):
        """Reset config._config before each test."""
        config._config = None

    def test_init_config_already_initialized(self):
        """Test _init_config when _config is already set."""
        config._config = {'existing': 'config'}
        config._init_config()
        self.assertEqual(config._config, {'existing': 'config'})

    def test_init_config_no_file_found(self):
        """Test _init_config when config file is not found."""
        with patch('config._get_default_path', return_value=None):
            config._config = None
            config._init_config()
            self.assertEqual(config._config, {})

    def test_init_config_file_found(self):
        """Test _init_config when config file is found."""
        test_config = {'key1': 'value1', 'key2': 42}
        with patch('config._get_default_path', return_value='/fake/path/config.json'):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))):
                config._config = None
                config._init_config()
                self.assertEqual(config._config, test_config)

    def test_get_default_path_no_config_found(self):
        """Test _get_default_path when no config.json is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = config._get_default_path()
                self.assertIsNone(result)
            finally:
                os.chdir(original_cwd)

    def test_get_default_path_in_current_directory(self):
        """Test _get_default_path finds config.json in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                config_path = os.path.join(tmpdir, 'config.json')
                test_config = {'test': 'value'}
                with open(config_path, 'w') as f:
                    json.dump(test_config, f)
                
                os.chdir(tmpdir)
                result = config._get_default_path()
                self.assertIsNotNone(result)
                # Use realpath to handle macOS symlink differences
                self.assertEqual(os.path.realpath(result), os.path.realpath(config_path))
            finally:
                os.chdir(original_cwd)

    def test_get_default_path_in_parent_directory(self):
        """Test _get_default_path finds config.json in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                parent_dir = tmpdir
                child_dir = os.path.join(tmpdir, 'child')
                os.makedirs(child_dir)
                
                config_path = os.path.join(parent_dir, 'config.json')
                test_config = {'parent': 'value'}
                with open(config_path, 'w') as f:
                    json.dump(test_config, f)
                
                os.chdir(child_dir)
                result = config._get_default_path()
                self.assertIsNotNone(result)
                # Use realpath to handle macOS symlink differences
                self.assertEqual(os.path.realpath(result), os.path.realpath(config_path))
            finally:
                os.chdir(original_cwd)

    def test_get_parameter_env_var_raw_value(self):
        """Test get_parameter with env var present (raw value)."""
        with patch.dict(os.environ, {'TEST_PARAM': 'raw_value'}, clear=False):
            config._config = None
            with patch('config._init_config'):
                config._config = {}
                result = config.get_parameter('TEST_PARAM')
                self.assertEqual(result, 'raw_value')

    def test_get_parameter_env_var_json_prefix(self):
        """Test get_parameter with env var with 'json:{...}' prefix."""
        with patch.dict(os.environ, {'TEST_PARAM': 'json:{"key": "value"}'}, clear=False):
            config._config = None
            with patch('config._init_config'):
                config._config = {}
                result = config.get_parameter('TEST_PARAM')
                self.assertEqual(result, {'key': 'value'})

    def test_get_parameter_env_var_json_string(self):
        """Test get_parameter with env var containing JSON string."""
        with patch.dict(os.environ, {'TEST_PARAM': '{"nested": {"key": 123}}'}, clear=False):
            config._config = None
            with patch('config._init_config'):
                config._config = {}
                result = config.get_parameter('TEST_PARAM')
                self.assertEqual(result, {'nested': {'key': 123}})

    def test_get_parameter_key_in_config(self):
        """Test get_parameter with key inside _config."""
        config._config = None
        with patch('config._init_config'):
            config._config = {'param1': 'config_value', 'param2': 42}
            result = config.get_parameter('param1')
            self.assertEqual(result, 'config_value')
            result = config.get_parameter('param2')
            self.assertEqual(result, 42)

    def test_get_parameter_missing_key_with_default(self):
        """Test get_parameter with missing key but default provided."""
        config._config = None
        with patch('config._init_config'):
            config._config = {}
            result = config.get_parameter('missing_param', default='default_value')
            self.assertEqual(result, 'default_value')

    def test_get_parameter_missing_key_no_default(self):
        """Test get_parameter with missing key and no default -> expect None."""
        config._config = None
        with patch('config._init_config'):
            config._config = {}
            result = config.get_parameter('missing_param')
            self.assertIsNone(result)

    def test_convert_to_typed_value_none(self):
        """Test convert_to_typed_value with None."""
        result = config.convert_to_typed_value(None)
        self.assertIsNone(result)

    def test_convert_to_typed_value_valid_json_string_dict(self):
        """Test convert_to_typed_value with valid JSON string (dict)."""
        result = config.convert_to_typed_value('{"key": "value"}')
        self.assertEqual(result, {'key': 'value'})

    def test_convert_to_typed_value_valid_json_string_array(self):
        """Test convert_to_typed_value with valid JSON string (array)."""
        result = config.convert_to_typed_value('[1, 2, 3]')
        self.assertEqual(result, [1, 2, 3])

    def test_convert_to_typed_value_valid_json_string_number(self):
        """Test convert_to_typed_value with valid JSON string (number)."""
        result = config.convert_to_typed_value('42')
        self.assertEqual(result, 42)
        result = config.convert_to_typed_value('3.14')
        self.assertEqual(result, 3.14)

    def test_convert_to_typed_value_invalid_json_string(self):
        """Test convert_to_typed_value with invalid JSON string."""
        result = config.convert_to_typed_value('not json')
        self.assertEqual(result, 'not json')
        result = config.convert_to_typed_value('{invalid json}')
        self.assertEqual(result, '{invalid json}')

    def test_convert_to_typed_value_non_string(self):
        """Test convert_to_typed_value with non-string values."""
        result = config.convert_to_typed_value(42)
        self.assertEqual(result, 42)
        result = config.convert_to_typed_value([1, 2, 3])
        self.assertEqual(result, [1, 2, 3])
        result = config.convert_to_typed_value({'key': 'value'})
        self.assertEqual(result, {'key': 'value'})

    def test_set_parameter_string_value(self):
        """Test set_parameter with string values."""
        with patch('config._init_config'):
            with patch.dict(os.environ, {}, clear=True):
                config.set_parameter('TEST_STR_PARAM', 'string_value')
                self.assertEqual(os.environ['TEST_STR_PARAM'], 'string_value')

    def test_set_parameter_dict_value(self):
        """Test set_parameter with dict -> json:{...}."""
        with patch('config._init_config'):
            with patch.dict(os.environ, {}, clear=True):
                config.set_parameter('TEST_DICT_PARAM', {'key': 'value'})
                self.assertEqual(os.environ['TEST_DICT_PARAM'], 'json:{"key": "value"}')

    def test_set_parameter_list_value(self):
        """Test set_parameter with list -> json:{...}."""
        with patch('config._init_config'):
            with patch.dict(os.environ, {}, clear=True):
                config.set_parameter('TEST_LIST_PARAM', [1, 2, 3])
                self.assertEqual(os.environ['TEST_LIST_PARAM'], 'json:[1, 2, 3]')

    def test_set_parameter_int_value(self):
        """Test set_parameter with int -> json:{...}."""
        with patch('config._init_config'):
            with patch.dict(os.environ, {}, clear=True):
                config.set_parameter('TEST_INT_PARAM', 42)
                self.assertEqual(os.environ['TEST_INT_PARAM'], 'json:42')

    def test_overwrite_from_args_python3_items(self):
        """Test overwrite_from_args using Python 3 items()."""
        args = MagicMock()
        args.param1 = 'value1'
        args.param2 = None
        args.param3 = {'key': 'value'}
        
        # Mock vars(args) to return a dict (Python 3 style - no iteritems, uses items)
        mock_vars_dict = {'param1': 'value1', 'param2': None, 'param3': {'key': 'value'}}
        with patch('builtins.vars', return_value=mock_vars_dict):
            with patch('config._init_config'):
                with patch('config.set_parameter') as mock_set:
                    with patch.dict(os.environ, {}, clear=True):
                        config.overwrite_from_args(args)
                        # Should call set_parameter for param1 and param3 (not param2 which is None)
                        self.assertEqual(mock_set.call_count, 2)
                        mock_set.assert_any_call('param1', 'value1')
                        mock_set.assert_any_call('param3', {'key': 'value'})

    def test_overwrite_from_args_iteritems_branch(self):
        """Test overwrite_from_args iteritems() branch (should fail gracefully)."""
        args = MagicMock()
        args.param1 = 'value1'
        args.param2 = None
        
        # Create a mock object that has iteritems() method (Python 2 style)
        # items() should raise exception so only iteritems() branch executes
        class MockVars:
            def iteritems(self):
                return iter([('param1', 'value1'), ('param2', None)])
            
            def items(self):
                raise AttributeError("items not available")
        
        mock_vars = MockVars()
        with patch('builtins.vars', return_value=mock_vars):
            with patch('config._init_config'):
                with patch('config.set_parameter') as mock_set:
                    with patch.dict(os.environ, {}, clear=True):
                        config.overwrite_from_args(args)
                        # Should call set_parameter for param1 (not param2 which is None)
                        mock_set.assert_called_once_with('param1', 'value1')

    def test_overwrite_from_args_iteritems_fails_then_items_works(self):
        """Test overwrite_from_args when iteritems fails but items works."""
        args = MagicMock()
        args.param1 = 'value1'
        args.param2 = None
        
        # Mock vars(args) to raise exception on iteritems, but work with items
        class MockVars:
            def iteritems(self):
                raise AttributeError("iteritems not available")
            
            def items(self):
                return iter([('param1', 'value1'), ('param2', None)])
        
        mock_vars = MockVars()
        with patch('builtins.vars', return_value=mock_vars):
            with patch('config._init_config'):
                with patch('config.set_parameter') as mock_set:
                    with patch.dict(os.environ, {}, clear=True):
                        config.overwrite_from_args(args)
                        mock_set.assert_called_once_with('param1', 'value1')

    def test_overwrite_from_args_contains_none(self):
        """Test overwrite_from_args with args containing None (ignored)."""
        args = MagicMock()
        args.param1 = 'value1'
        args.param2 = None
        args.param3 = 42
        
        mock_vars_dict = {'param1': 'value1', 'param2': None, 'param3': 42}
        with patch('builtins.vars', return_value=mock_vars_dict):
            with patch('config._init_config'):
                with patch('config.set_parameter') as mock_set:
                    with patch.dict(os.environ, {}, clear=True):
                        config.overwrite_from_args(args)
                        # Should call set_parameter for param1 and param3 (not param2 which is None)
                        self.assertEqual(mock_set.call_count, 2)
                        mock_set.assert_any_call('param1', 'value1')
                        mock_set.assert_any_call('param3', 42)

    def test_integration_full_flow_current_dir(self):
        """Integration test: full flow with config.json in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                config_path = os.path.join(tmpdir, 'config.json')
                test_config = {'test_key': 'test_value', 'num_key': 42}
                with open(config_path, 'w') as f:
                    json.dump(test_config, f)
                
                os.chdir(tmpdir)
                config._config = None
                config._init_config()
                self.assertEqual(config._config, test_config)
                
                result = config.get_parameter('test_key')
                self.assertEqual(result, 'test_value')
            finally:
                os.chdir(original_cwd)

    def test_integration_full_flow_parent_dir(self):
        """Integration test: full flow with config.json in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                parent_dir = tmpdir
                child_dir = os.path.join(tmpdir, 'child')
                os.makedirs(child_dir)
                
                config_path = os.path.join(parent_dir, 'config.json')
                test_config = {'parent_key': 'parent_value'}
                with open(config_path, 'w') as f:
                    json.dump(test_config, f)
                
                os.chdir(child_dir)
                config._config = None
                config._init_config()
                self.assertEqual(config._config, test_config)
            finally:
                os.chdir(original_cwd)


if __name__ == '__main__':
    unittest.main()
