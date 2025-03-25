import os
import unittest
import json
import ast
import concurrent.futures
from unittest.mock import patch, mock_open, MagicMock, call
from docdog.mcp_tools import MCPTools

class TestMCPTools(unittest.TestCase):
    def setUp(self):
        self.project_root = "/test/project/root"
        # Update initialization to include new parameters
        self.tools = MCPTools(self.project_root, max_workers=None, cache_size=128)
    
    def test_initialization(self):
        """Test initialization of MCPTools with different parameters"""
        # Test default initialization
        tools = MCPTools(self.project_root)
        self.assertEqual(tools.project_root, self.project_root)
        self.assertIsNone(tools.max_workers)
        self.assertEqual(tools.cache_size, 128)
        
        # Test with custom parameters
        tools_custom = MCPTools(self.project_root, max_workers=4, cache_size=256)
        self.assertEqual(tools_custom.project_root, self.project_root)
        self.assertEqual(tools_custom.max_workers, 4)
        self.assertEqual(tools_custom.cache_size, 256)
        
        # Check ignore patterns are correctly set
        self.assertIn("**/.git/**", tools.ignore_patterns)
        self.assertIn("**/*.jpg", tools.ignore_patterns)
    
    # The should_ignore test remains the same
    def test_should_ignore(self):
        """Test pattern matching for files that should be ignored"""
        with patch('os.path.relpath') as mock_relpath:
            # Make the relative path return exactly the path portion after the project root
            # This ensures the pattern matching works as expected
            mock_relpath.side_effect = lambda path, root: path[len(root)+1:] if path.startswith(root) else path
            
            # Test patterns that should be ignored
            self.assertTrue(self.tools.should_ignore(os.path.join(self.project_root, ".git/config")))
            self.assertTrue(self.tools.should_ignore(os.path.join(self.project_root, "venv/lib/python")))
            self.assertTrue(self.tools.should_ignore(os.path.join(self.project_root, "image.jpg")))
            self.assertTrue(self.tools.should_ignore(os.path.join(self.project_root, "subfolder/image.jpeg")))
            self.assertTrue(self.tools.should_ignore(os.path.join(self.project_root, "__pycache__/module.pyc")))
            
            # Test patterns that should not be ignored
            self.assertFalse(self.tools.should_ignore(os.path.join(self.project_root, "main.py")))
            self.assertFalse(self.tools.should_ignore(os.path.join(self.project_root, "README.md")))
            self.assertFalse(self.tools.should_ignore(os.path.join(self.project_root, "src/app.py")))
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.listdir')
    @patch('os.path.relpath')
    def test_list_files(self, mock_relpath, mock_listdir, mock_isfile, mock_exists):
        """Test listing files in a directory"""
        mock_exists.return_value = True
        mock_listdir.return_value = ["main.py", "README.md", ".git", "image.jpg"]
        mock_isfile.return_value = True
        mock_relpath.side_effect = lambda path, root: os.path.basename(path)
        
        with patch.object(self.tools, 'should_ignore', side_effect=lambda p: p.endswith(('.git', '.jpg'))):
            result = self.tools.list_files("")
            
            self.assertIn("main.py", result)
            self.assertIn("README.md", result)
            self.assertNotIn(".git", result)
            self.assertNotIn("image.jpg", result)
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.listdir')
    @patch('os.path.relpath')
    def test_list_files_caching(self, mock_relpath, mock_listdir, mock_isfile, mock_exists):
        """Test that list_files uses caching"""
        mock_exists.return_value = True
        mock_listdir.return_value = ["main.py", "README.md", ".git", "image.jpg"]
        mock_isfile.return_value = True
        mock_relpath.side_effect = lambda path, root: os.path.basename(path)

        with patch.object(self.tools, 'should_ignore', side_effect=lambda p: p.endswith(('.git', '.jpg'))):
            # First call: should miss cache
            result1 = self.tools.list_files("src")
            self.assertEqual(mock_listdir.call_count, 1)
            info1 = self.tools._cached_list_files.cache_info()
            self.assertEqual(info1.misses, 1)
            self.assertEqual(info1.hits, 0)

            # Second call with same directory: should hit cache
            result2 = self.tools.list_files("src")
            self.assertEqual(mock_listdir.call_count, 1)  # No additional call
            info2 = self.tools._cached_list_files.cache_info()
            self.assertEqual(info2.misses, 1)
            self.assertEqual(info2.hits, 1)
            self.assertEqual(result1, result2)  # Results should be consistent

            # Call with different directory: should miss cache again
            result3 = self.tools.list_files("tests")
            self.assertEqual(mock_listdir.call_count, 2)  # New call
            info3 = self.tools._cached_list_files.cache_info()
            self.assertEqual(info3.misses, 2)
            self.assertEqual(info3.hits, 1)
    
    # Additional tests for path handling remain the same
    @patch('os.path.abspath')
    def test_list_files_outside_repo(self, mock_abspath):
        """Test handling of paths outside the project root"""
        mock_abspath.return_value = "/some/other/path"
        
        result = self.tools.list_files("../some/path")
        self.assertEqual(result, "Error: Directory is outside the repo!")
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_list_files_error(self, mock_listdir, mock_exists):
        """Test error handling in list_files"""
        mock_exists.return_value = True
        mock_listdir.side_effect = PermissionError("Permission denied")
        
        result = self.tools.list_files("some/dir")
        self.assertIn("Error listing files", result)
        self.assertIn("Permission denied", result)
    
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.listdir')
    def test_list_files_empty(self, mock_listdir, mock_isfile, mock_exists):
        """Test handling of directories with no files"""
        mock_exists.return_value = True
        mock_listdir.return_value = []
        mock_isfile.return_value = True
        
        result = self.tools.list_files("empty/dir")
        self.assertEqual(result, "No files found.")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    def test_read_file(self, mock_file, mock_exists):
        """Test reading a file's contents"""
        mock_exists.return_value = True
        
        with patch.object(self.tools, 'should_ignore', return_value=False):
            result = self.tools.read_file("test.txt")
            self.assertEqual(result, "test content")
        
        with patch.object(self.tools, 'should_ignore', return_value=True):
            result = self.tools.read_file("ignored.txt")
            self.assertEqual(result, "Error: File ignored!")
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="test content")
    def test_read_file_caching(self, mock_file, mock_exists):
        """Test that read_file uses caching"""
        mock_exists.return_value = True
        with patch.object(self.tools, 'should_ignore', return_value=False):
            # First call: should miss cache
            result1 = self.tools.read_file("test.txt")
            self.assertEqual(mock_file.call_count, 1)
            info1 = self.tools._cached_read_file.cache_info()
            self.assertEqual(info1.misses, 1)
            self.assertEqual(info1.hits, 0)

            # Second call with same file: should hit cache
            result2 = self.tools.read_file("test.txt")
            self.assertEqual(mock_file.call_count, 1)  # No additional open
            info2 = self.tools._cached_read_file.cache_info()
            self.assertEqual(info2.misses, 1)
            self.assertEqual(info2.hits, 1)
            self.assertEqual(result1, result2)  # Results should be consistent

            # Call with different file: should miss cache again
            result3 = self.tools.read_file("other.txt")
            self.assertEqual(mock_file.call_count, 2)  # New open
            info3 = self.tools._cached_read_file.cache_info()
            self.assertEqual(info3.misses, 2)
            self.assertEqual(info3.hits, 1)
    
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_read_file_error(self, mock_open, mock_exists):
        """Test error handling in read_file"""
        mock_exists.return_value = True
        mock_open.side_effect = IOError("File not found")
        
        with patch.object(self.tools, 'should_ignore', return_value=False):
            result = self.tools.read_file("nonexistent.txt")
            self.assertIn("Error reading file", result)
    
    @patch('os.path.exists')
    @patch('ast.parse')
    @patch('builtins.open', new_callable=mock_open, read_data="def test():\n    # Test comment\n    pass")
    def test_read_python_file(self, mock_file, mock_parse, mock_exists):
        """Test reading a Python file with comments and docstrings"""
        mock_exists.return_value = True
        
        # Create a properly structured mock AST tree with a docstring
        mock_tree = MagicMock()
        
        # Create a function definition mock that matches the exact conditions in the implementation
        mock_func_def = MagicMock(spec=ast.FunctionDef)
        mock_func_def.body = [MagicMock(spec=ast.Expr)]
        
        # The value needs to be a string (ast.Str)
        str_node = MagicMock(spec=ast.Str)
        str_node.s = "Test docstring"
        mock_func_def.body[0].value = str_node
        
        # Setup the AST walk to return our function definition mock
        mock_parse.return_value = mock_tree
        
        with patch('ast.walk', return_value=[mock_func_def]):
            with patch.object(self.tools, 'should_ignore', return_value=False):
                result = self.tools.read_file("test.py")
                
                self.assertIn("Content:", result)
                self.assertIn("def test():", result)
                self.assertIn("# Test comment", result)
                self.assertIn("Docstrings:", result)
                self.assertIn("Test docstring", result)
                self.assertIn("Comments:", result)
                self.assertIn("# Test comment", result)
    
    def test_clear_caches(self):
        """Test clearing the LRU caches"""
        with patch.object(self.tools._cached_read_file, 'cache_clear') as mock_read_clear:
            with patch.object(self.tools._cached_list_files, 'cache_clear') as mock_list_clear:
                self.tools.clear_caches()
                mock_read_clear.assert_called_once()
                mock_list_clear.assert_called_once()
    
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_batch_read_files_threading(self, mock_executor_class):
        """Test that batch_read_files uses ThreadPoolExecutor"""
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Set up mock futures and their results
        mock_future1 = MagicMock()
        mock_future1.result.return_value = "content1"
        
        mock_future2 = MagicMock()
        mock_future2.result.return_value = "content2"
        
        # Configure the executor to return our mock futures
        mock_executor.submit.side_effect = [mock_future1, mock_future2]
        # Configure as_completed to return futures in order
        with patch('concurrent.futures.as_completed', return_value=[mock_future1, mock_future2]):
            # Call the method with multiple files
            result = self.tools.batch_read_files(["file1.txt", "file2.txt"])
            
            # Verify ThreadPoolExecutor was created with the right parameters
            mock_executor_class.assert_called_once_with(max_workers=self.tools.max_workers)
            
            # Verify submit was called for each file
            self.assertEqual(mock_executor.submit.call_count, 2)
            
            # Parse the result and check the content
            parsed = json.loads(result)
            self.assertEqual(len(parsed), 2)
            self.assertEqual(parsed[0]["file"], "file1.txt")
            self.assertEqual(parsed[0]["content"], "content1")
            self.assertEqual(parsed[1]["file"], "file2.txt")
            self.assertEqual(parsed[1]["content"], "content2")
    
    def test_batch_read_files(self):
        """Test batch reading multiple files"""
        with patch.object(self.tools, 'read_file', side_effect=["content1", "Error: File ignored!", "content3"]):
            result = self.tools.batch_read_files(["file1.txt", "file2.txt", "file3.txt"])
            
            parsed = json.loads(result)
            
            self.assertEqual(len(parsed), 3)
            self.assertEqual(parsed[0]["file"], "file1.txt")
            self.assertEqual(parsed[0]["content"], "content1")
            self.assertEqual(parsed[1]["file"], "file2.txt")
            self.assertEqual(parsed[1]["error"], "Error: File ignored!")
            self.assertEqual(parsed[2]["file"], "file3.txt")
            self.assertEqual(parsed[2]["content"], "content3")
    
    def test_batch_read_files_empty(self):
        """Test batch reading with empty file list"""
        result = self.tools.batch_read_files([])
        parsed = json.loads(result)
        self.assertEqual(parsed, [])
    
    def test_handle_tool_call(self):
        """Test the tool call handler for all tools"""
        with patch.object(self.tools, 'list_files', return_value="file1.txt\nfile2.txt"):
            result = self.tools.handle_tool_call("list_files", {"directory": "src"})
            self.assertEqual(result, "file1.txt\nfile2.txt")
        
        with patch.object(self.tools, 'read_file', return_value="file content"):
            result = self.tools.handle_tool_call("read_file", {"file_path": "file.txt"})
            self.assertEqual(result, "file content")
        
        with patch.object(self.tools, 'batch_read_files', return_value='[{"file": "test.txt", "content": "data"}]'):
            result = self.tools.handle_tool_call("batch_read_files", {"file_paths": ["test.txt"]})
            self.assertEqual(result, '[{"file": "test.txt", "content": "data"}]')
        
        result = self.tools.handle_tool_call("unknown_tool", {})
        self.assertIn("Unknown tool", result)