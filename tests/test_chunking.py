import os
import shutil
import unittest
from unittest.mock import patch, MagicMock, mock_open
from docdog.chunking import chunk_project

class TestChunking(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_project"
        self.chunks_dir = "test_chunks"
        
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "test.py"), "w") as f:
            f.write("def test_function():\n    pass\n")
        with open(os.path.join(self.test_dir, "test.md"), "w") as f:
            f.write("# Test Document\n\nThis is a test.")
        with open(os.path.join(self.test_dir, "test.jpg"), "wb") as f:
            f.write(b"\xFF\xD8\xFF")  
    
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        if os.path.exists(self.chunks_dir):
            shutil.rmtree(self.chunks_dir)
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    def test_chunk_project_with_tokenbased_chunker(self, mock_chunker, mock_exists, mock_makedirs, mock_rmtree):
        mock_exists.return_value = True
        instance = mock_chunker.return_value
        instance.process_directory.return_value = None
        mock_files = ["chunk-0.txt", "chunk-1.txt"]
        
        instance.loaded_files = [
            ("test.py", b"test content", 0),
            ("test.md", b"more content", 0)
        ]
        instance.count_tokens.return_value = 100
        
        with patch('os.listdir', return_value=mock_files):
            result = chunk_project(self.test_dir, self.chunks_dir)
            
            mock_chunker.assert_called()
            
            instance.process_directory.assert_called_with(self.test_dir)
            
            self.assertEqual(len(result), 2)
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    @patch('docdog.chunking.ParallelChunker')
    def test_fallback_to_parallel_chunker(self, mock_parallel, mock_token, mock_exists, mock_makedirs, mock_rmtree):
        mock_exists.return_value = True
        mock_token.side_effect = Exception("Token chunker failed")
        
        instance = mock_parallel.return_value
        instance.process_directory.return_value = None
        mock_files = ["chunk-0.txt"]
        
        with patch('os.listdir', return_value=mock_files):
            result = chunk_project(self.test_dir, self.chunks_dir)
            
            mock_parallel.assert_called()
            instance.process_directory.assert_called_with(self.test_dir)
    
    def test_empty_directory(self):
        empty_dir = "empty_test_dir"
        os.makedirs(empty_dir, exist_ok=True)
        
        try:
            result = chunk_project(empty_dir, self.chunks_dir)
            self.assertEqual(result, [])
        finally:
            if os.path.exists(empty_dir):
                shutil.rmtree(empty_dir)
                    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    def test_default_config(self, mock_chunker, mock_exists, mock_makedirs, mock_rmtree):
        """Test chunking with no config provided (should use defaults)"""
        mock_exists.return_value = True
        instance = mock_chunker.return_value
        instance.process_directory.return_value = None
        instance.loaded_files = [("test.py", b"content", 0)]
        instance.count_tokens.return_value = 50
        
        with patch('os.listdir', return_value=["chunk-0.txt"]):
            result = chunk_project(self.test_dir, self.chunks_dir, None)
            
            args, kwargs = mock_chunker.call_args_list[0]
            self.assertEqual(kwargs['user_ignore'][0], "**/chunks/**")
            self.assertTrue(any("**/venv/**" in ign for ign in kwargs['user_ignore']))
    
    @patch('docdog.chunking.TokenBasedChunker')
    @patch('os.makedirs')
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_output_dir_cleanup(self, mock_exists, mock_rmtree, mock_makedirs, mock_chunker):
        """Test that the output directory is cleaned up before processing"""
        mock_exists.return_value = True
        instance = mock_chunker.return_value
        instance.process_directory.return_value = None
        instance.loaded_files = [("test.py", b"content", 0)]
        instance.count_tokens.return_value = 50
        
        with patch('os.listdir', return_value=["chunk-0.txt"]):
            chunk_project(self.test_dir, self.chunks_dir)
            mock_rmtree.assert_any_call(self.chunks_dir)
            temp_dir = os.path.join(self.chunks_dir, "temp")
            mock_rmtree.assert_any_call(temp_dir)
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    def test_temp_dir_cleanup(self, mock_chunker, mock_exists, mock_makedirs, mock_rmtree):
        """Test that the temporary directory is cleaned up"""
        mock_exists.return_value = True
        analyzer = MagicMock()
        analyzer.loaded_files = [("test.py", b"content", 0)]
        analyzer.count_tokens.return_value = 50
        
        chunker = MagicMock()
        chunker.process_directory.return_value = None
        
        mock_chunker.side_effect = [analyzer, chunker]
        
        with patch('os.listdir', return_value=["chunk-0.txt"]):
            chunk_project(self.test_dir, self.chunks_dir)
            
            temp_dir = os.path.join(self.chunks_dir, "temp")
            mock_makedirs.assert_any_call(temp_dir, exist_ok=True)
            
            mock_rmtree.assert_any_call(temp_dir)
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    def test_custom_max_tokens(self, mock_chunker, mock_exists, mock_makedirs, mock_rmtree):
        """Test with custom max_tokens_per_chunk value"""
        mock_exists.return_value = True
        config = {
            "max_tokens_per_chunk": 75000,  
            "allowed_extensions": [".py", ".md"]
        }
        
        instance = mock_chunker.return_value
        instance.process_directory.return_value = None
        instance.loaded_files = [("test.py", b"content", 0)]
        instance.count_tokens.return_value = 100
        
        with patch('os.listdir', return_value=["chunk-0.txt"]):
            chunk_project(self.test_dir, self.chunks_dir, config)
            
            calls = mock_chunker.call_args_list
            self.assertEqual(len(calls), 2) 
            
            _, first_kwargs = calls[0]
            self.assertEqual(first_kwargs['equal_chunks'], 1)
            
            _, second_kwargs = calls[1]
            self.assertEqual(second_kwargs['equal_chunks'], 1)
    
    @patch('shutil.rmtree')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('docdog.chunking.TokenBasedChunker')
    @patch('docdog.chunking.ParallelChunker')
    def test_both_chunkers_fail(self, mock_parallel, mock_token, mock_exists, mock_makedirs, mock_rmtree):
        """Test when both TokenBasedChunker and ParallelChunker fail"""
        mock_exists.return_value = True
        mock_token.side_effect = Exception("Token chunker failed")
        mock_parallel.side_effect = Exception("Parallel chunker failed")
        
        result = chunk_project(self.test_dir, self.chunks_dir)
        
        self.assertEqual(result, [])
    
    @patch('docdog.chunking.PYKOMODO_AVAILABLE', False)
    def test_pykomodo_not_available(self):
        """Test when pykomodo is not available"""
        result = chunk_project(self.test_dir, self.chunks_dir)
        
        self.assertEqual(result, [])