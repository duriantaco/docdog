import unittest
from unittest.mock import patch, MagicMock, call
from docdog.summarizer import summarize_code_chunk, summarize_chunks, summarize_content, batch_summarize_files

class TestSummarizer(unittest.TestCase):
    def setUp(self):
        self.openai_mock = MagicMock()
        self.openai_mock.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test summary"))]
        )
    
    @patch('docdog.summarizer.client')
    def test_summarize_code_chunk(self, mock_client):
        mock_client.chat.completions.create = self.openai_mock.chat.completions.create
        
        chunk = {
            "name": "test_function",
            "type": "function",
            "code": "def test_function():\n    return True"
        }
        
        result = summarize_code_chunk(chunk)
        self.assertEqual(result["name"], "test_function")
        self.assertEqual(result["type"], "function")
        self.assertEqual(result["summary"], "Test summary")
        
        args, kwargs = self.openai_mock.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-3.5-turbo")
        self.assertLessEqual(kwargs["max_tokens"], 150)
        
        custom_config = {
            "model": "gpt-4",
            "max_tokens": 300,
            "temperature": 0.5,
            "verbose": True
        }
        
        result = summarize_code_chunk(chunk, custom_config)
        args, kwargs = self.openai_mock.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-4")
        self.assertEqual(kwargs["max_tokens"], 300)
        self.assertEqual(kwargs["temperature"], 0.5)
    
    @patch('docdog.summarizer.client')
    @patch('docdog.summarizer.logger')
    def test_summarize_code_chunk_error(self, mock_logger, mock_client):
        """Test error handling in summarize_code_chunk"""
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        chunk = {
            "name": "test_function",
            "type": "function",
            "code": "def test_function():\n    return True"
        }
        
        config = {"verbose": True}
        result = summarize_code_chunk(chunk, config)
        
        self.assertEqual(result["name"], "test_function")
        self.assertEqual(result["type"], "function")
        self.assertTrue(result["summary"].startswith("Summary generation failed"))
        self.assertIn("API Error", result["summary"])
        
        mock_logger.error.assert_called_once()
    
    @patch('docdog.summarizer.summarize_code_chunk')
    def test_summarize_chunks(self, mock_summarize):
        mock_summarize.side_effect = lambda chunk, config: {
            "name": chunk["name"],
            "type": chunk["type"],
            "summary": f"Summary for {chunk['name']}"
        }
        
        chunks = [
            {"name": "func1", "type": "function", "code": "code1"},
            {"name": "class1", "type": "class", "code": "code2"}
        ]
        
        results = summarize_chunks(chunks, verbose=True)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "func1")
        self.assertEqual(results[0]["summary"], "Summary for func1")
        self.assertEqual(results[1]["name"], "class1")
        self.assertEqual(results[1]["summary"], "Summary for class1")
    
    @patch('docdog.summarizer.concurrent.futures.ThreadPoolExecutor')
    @patch('docdog.summarizer.logger')
    def test_summarize_chunks_concurrency(self, mock_logger, mock_executor):
        """Test concurrent processing in summarize_chunks"""
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        future1 = MagicMock()
        future2 = MagicMock()
        
        chunk1 = {"name": "func1", "type": "function", "code": "code1"}
        chunk2 = {"name": "class1", "type": "class", "code": "code2"}
        
        result1 = {"name": "func1", "type": "function", "summary": "Summary for func1"}
        result2 = {"name": "class1", "type": "class", "summary": "Summary for class1"}
        
        future1.result.return_value = result1
        future2.result.return_value = result2
                
        mock_executor_instance.submit.side_effect = [future1, future2]
        
        with patch('docdog.summarizer.concurrent.futures.as_completed', 
                  return_value=[future1, future2]):
            
            config = {
                "model": "gpt-4",
                "max_tokens": 200,
                "temperature": 0.4,
                "verbose": True
            }
            
            results = summarize_chunks(
                [chunk1, chunk2], 
                config=config,
                verbose=True, 
                max_workers=3
            )
            
            self.assertEqual(len(results), 2)
            self.assertIn(result1, results)
            self.assertIn(result2, results)
            
            mock_executor.assert_called_with(max_workers=3)
            
            self.assertEqual(mock_executor_instance.submit.call_count, 2)
    
    @patch('docdog.summarizer.concurrent.futures.ThreadPoolExecutor')
    @patch('docdog.summarizer.time.sleep')
    @patch('docdog.summarizer.logger')
    def test_summarize_chunks_error_handling(self, mock_logger, mock_sleep, mock_executor):
        """Test error handling in summarize_chunks"""
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        future1 = MagicMock()
        future2 = MagicMock()
        
        chunk1 = {"name": "func1", "type": "function", "code": "code1"}
        chunk2 = {"name": "class1", "type": "class", "code": "code2"}
        
        result1 = {"name": "func1", "type": "function", "summary": "Summary for func1"}
        
        future1.result.return_value = result1
        future2.result.side_effect = Exception("Processing error")
        
        mock_executor_instance.submit.side_effect = [future1, future2]
        
        with patch('docdog.summarizer.concurrent.futures.as_completed', 
                  return_value=[future1, future2]):
            
            results = summarize_chunks([chunk1, chunk2], verbose=True)
            
            self.assertEqual(len(results), 2)
            self.assertIn(result1, results)
            
            error_result = [r for r in results if r["name"] == "class1"][0]
            self.assertTrue(error_result["summary"].startswith("Summary generation failed"))
            
            mock_logger.error.assert_called_once()
            
            mock_sleep.assert_called()
    
    @patch('docdog.summarizer.client')
    def test_summarize_content(self, mock_client):
        mock_client.chat.completions.create = self.openai_mock.chat.completions.create
        
        result = summarize_content("This is some test content that needs to be summarized.")
        self.assertEqual(result, "Test summary")
        
        long_text = "a" * 20000
        result = summarize_content(long_text)
        self.assertEqual(result, "Test summary")
        
        args, kwargs = self.openai_mock.chat.completions.create.call_args
        prompt = kwargs["messages"][1]["content"]
        self.assertIn("text truncated", prompt)

    @patch('docdog.summarizer.client')
    @patch('docdog.summarizer.logger')
    def test_summarize_content_with_custom_params(self, mock_logger, mock_client):
        """Test summarize_content with custom parameters"""
        mock_client.chat.completions.create = self.openai_mock.chat.completions.create
        
        result = summarize_content(
            "Custom parameter test",
            model="gpt-4",
            max_tokens=500,
            temperature=0.3
        )
        
        args, kwargs = self.openai_mock.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-4")
        self.assertEqual(kwargs["max_tokens"], 500)
        self.assertEqual(kwargs["temperature"], 0.3)
    
    @patch('docdog.summarizer.client')
    @patch('docdog.summarizer.logger')
    def test_summarize_content_error(self, mock_logger, mock_client):
        """Test error handling in summarize_content"""
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        result = summarize_content("Test content")
        
        self.assertTrue(result.startswith("Summary generation failed"))
        self.assertIn("API Error", result)
        
        mock_logger.error.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="File content")
    @patch('docdog.summarizer.summarize_content')
    def test_batch_summarize_files(self, mock_summarize, mock_open, mock_exists):
        mock_exists.return_value = True
        mock_summarize.return_value = "Summary of file"
        
        file_paths = ["file1.py", "file2.py"]
        results = batch_summarize_files(file_paths, verbose=True)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["file"], "file1.py")
        self.assertEqual(results[0]["summary"], "Summary of file")
        self.assertEqual(results[1]["file"], "file2.py")
        self.assertEqual(results[1]["summary"], "Summary of file")
        
        self.assertEqual(mock_open.call_count, 2)
        
        self.assertEqual(mock_summarize.call_count, 2)
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('docdog.summarizer.summarize_content')
    @patch('docdog.summarizer.logger')
    def test_batch_summarize_files_with_missing_files(self, mock_logger, mock_summarize, mock_open, mock_exists):
        """Test batch_summarize_files with missing files"""
        mock_exists.side_effect = lambda path: path == "file1.py"
        mock_open.return_value.__enter__.return_value.read.return_value = "File content"
        mock_summarize.return_value = "Summary of file"
        
        file_paths = ["file1.py", "file2.py"]
        results = batch_summarize_files(file_paths, verbose=True)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["file"], "file1.py")
        
        mock_logger.warning.assert_called_once_with("File not found: file2.py")
        
        mock_open.assert_called_once_with("file1.py", 'r', encoding='utf-8')
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('docdog.summarizer.concurrent.futures.ThreadPoolExecutor')
    @patch('docdog.summarizer.time.sleep')
    @patch('docdog.summarizer.logger')
    def test_batch_summarize_files_file_read_error(self, mock_logger, mock_sleep, mock_executor, 
                                                  mock_open, mock_exists):
        """Test batch_summarize_files with file read errors"""
        mock_exists.return_value = True
        mock_open.side_effect = IOError("Read error")
        
        file_paths = ["file1.py", "file2.py"]
        results = batch_summarize_files(file_paths, verbose=True)
        
        self.assertEqual(results, [])
        self.assertEqual(mock_logger.error.call_count, 2)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="File content")
    @patch('docdog.summarizer.concurrent.futures.ThreadPoolExecutor')
    @patch('docdog.summarizer.time.sleep')
    @patch('docdog.summarizer.logger')
    def test_batch_summarize_files_processing_error(self, mock_logger, mock_sleep, 
                                                   mock_executor, mock_open, mock_exists):
        """Test batch_summarize_files with processing errors"""
        mock_exists.return_value = True
        
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        future1 = MagicMock()
        future2 = MagicMock()
        
        future1.result.return_value = "Summary 1"
        future2.result.side_effect = Exception("Processing error")
        
        mock_executor_instance.submit.side_effect = [future1, future2]
        
        with patch('docdog.summarizer.concurrent.futures.as_completed', 
                  return_value=[future1, future2]):
            
            file_paths = ["file1.py", "file2.py"]
            results = batch_summarize_files(file_paths, verbose=True)
            
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["file"], "file1.py")
            self.assertEqual(results[0]["summary"], "Summary 1")
            
            self.assertEqual(results[1]["file"], "file2.py")
            self.assertTrue(results[1]["summary"].startswith("Summary generation failed"))
            
            mock_logger.error.assert_called_once()
            
            mock_sleep.assert_called_once()
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="File content")
    @patch('docdog.summarizer.summarize_content')
    def test_batch_summarize_files_custom_params(self, mock_summarize, mock_open, mock_exists):
        """Test batch_summarize_files with custom parameters"""
        mock_exists.return_value = True
        mock_summarize.return_value = "Summary of file"
        
        file_paths = ["file1.py", "file2.py"]
        results = batch_summarize_files(
            file_paths, 
            model="gpt-4",
            max_workers=10,
            verbose=True
        )
        
        mock_summarize.assert_has_calls([
            call("File content", model="gpt-4"),
            call("File content", model="gpt-4")
        ])