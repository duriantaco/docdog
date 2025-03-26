import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import docdog.main
from docdog.main import find_project_root

class TestFindProjectRoot(unittest.TestCase):
    @patch('os.path.exists')
    @patch('os.getcwd')
    @patch('sys.exit')
    def test_find_project_root_no_marker(self, mock_exit, mock_getcwd, mock_exists):
        """Test behavior when no project markers are found - should error and exit"""
        mock_getcwd.return_value = "/path/to/random/directory"
        
        mock_exists.return_value = False
        
        mock_logger = MagicMock()
        docdog.main.logger = mock_logger
        
        find_project_root()
        
        mock_logger.error.assert_any_call("No project markers found. Please run DocDog from a valid project directory.")
        
        second_call_args = mock_logger.error.call_args_list[1][0][0]
        self.assertTrue("markers" in second_call_args)
        for marker in ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json']:
            self.assertIn(marker, second_call_args)
        
        mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()