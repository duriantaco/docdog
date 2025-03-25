import os
import shutil
import unittest
import hashlib
import tempfile
from unittest.mock import patch, MagicMock, mock_open, call

from docdog.summary_cache import (
    SummaryCache, 
    summarize_chunk_with_retry, 
    batch_summarize_chunks,
    memory_cache
)

class TestSummaryCacheAdvanced(unittest.TestCase):
    def setUp(self):
        self.cache_dir = ".test_summary_cache"
        self.cache = SummaryCache(self.cache_dir)
        memory_cache.clear()
    
    def tearDown(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
    
    def test_cache_directory_creation(self):
        test_dir = ".test_cache_dir_creation"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        try:
            cache = SummaryCache(test_dir)
            self.assertTrue(os.path.exists(test_dir))
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
    
    def test_real_file_operations(self):
        content = "Test content for real file operations"
        model = "test-model"
        summary = "This is a real summary"
        
        self.cache.set(content, model, summary)
        self.assertTrue(os.path.exists(self.cache_dir))
        
        key = self.cache._get_cache_key(content, model)
        cache_path = self.cache._get_cache_path(key)
        self.assertTrue(os.path.exists(cache_path))
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            stored_summary = f.read()
        self.assertEqual(stored_summary, summary)
        
        retrieved = self.cache.get(content, model)
        self.assertEqual(retrieved, summary)
    
    def test_missing_cache_returns_none(self):
        self.assertIsNone(self.cache.get("nonexistent content", "model"))
    
    def test_cache_overwrite(self):
        content = "Overwrite test content"
        model = "test-model"
        summary1 = "First summary"
        summary2 = "Updated summary"
        
        self.cache.set(content, model, summary1)
        retrieved1 = self.cache.get(content, model)
        self.assertEqual(retrieved1, summary1)
        
        self.cache.set(content, model, summary2)
        retrieved2 = self.cache.get(content, model)
        self.assertEqual(retrieved2, summary2)


class TestSummarizeChunkWithRetryAdvanced(unittest.TestCase):
    def setUp(self):
        self.cache_dir = ".test_summary_cache"
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.client = MagicMock()
        self.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test summary"))]
        )
        
        memory_cache.clear()
        
        self.mock_summary_cache = MagicMock()
        self.mock_summary_cache.get.return_value = None
        
        self.patcher = patch('docdog.summary_cache.summary_cache', self.mock_summary_cache)
        self.patcher.start()
    
    def tearDown(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        self.patcher.stop()
    
    @patch('docdog.summary_cache.time.sleep')
    def test_retry_logic(self, mock_sleep):
        self.client.chat.completions.create.side_effect = [
            Exception("First error"),
            Exception("Second error"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Success after retries"))])
        ]
        
        result = summarize_chunk_with_retry("test.py", "test content", self.client, max_retries=3)
        
        self.assertEqual(self.client.chat.completions.create.call_count, 3)
        
        self.assertEqual(mock_sleep.call_count, 2)

        self.assertEqual(result['summary'], "Success after retries")
        self.assertEqual(result['cached'], False)
    
    @patch('docdog.summary_cache.time.sleep')
    def test_backoff_mechanism(self, mock_sleep):
        self.client.chat.completions.create.side_effect = [
            Exception("First error"),
            Exception("Second error"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Success"))])
        ]
        
        summarize_chunk_with_retry("test.py", "test content", self.client, 
                                   max_retries=3, backoff_factor=2.0)
        

        mock_sleep.assert_has_calls([call(1.0), call(2.0)])
    
    def test_memory_cache(self):
        memory_cache.clear()
        
        self.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Memory cached summary"))]
        )
        
        content = "memory cache test"
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        cache_key = f"gpt-3.5-turbo_{content_hash}"  
        
        result1 = summarize_chunk_with_retry("test.py", content, self.client)
        self.assertEqual(result1['summary'], "Memory cached summary")
        self.assertEqual(result1['cached'], False)
        self.assertEqual(self.client.chat.completions.create.call_count, 1)
        
        memory_cache[cache_key] = "Memory cached summary"
        
        self.client.chat.completions.create.reset_mock()
        
        result2 = summarize_chunk_with_retry("test.py", content, self.client)
        self.assertEqual(result2['summary'], "Memory cached summary")
        self.assertEqual(result2['cached'], True)
        self.assertEqual(self.client.chat.completions.create.call_count, 0)


class TestBatchSummarizeChunks(unittest.TestCase):
    def setUp(self):
        self.cache_dir = ".test_summary_cache"
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.client = MagicMock()
        
        self.temp_dir = tempfile.mkdtemp()
        self.chunk_files = []
        for i in range(3):
            path = os.path.join(self.temp_dir, f"chunk-{i}.txt")
            with open(path, 'w') as f:
                f.write(f"Content for chunk {i}")
            self.chunk_files.append(path)
        
        memory_cache.clear()
        
        self.mock_encoding = MagicMock()
        self.mock_encoding.encode.return_value = [1] * 10  
        
        self.mock_summary_cache = MagicMock()
        self.mock_summary_cache.get.return_value = None
        
        self.summary_cache_patcher = patch('docdog.summary_cache.summary_cache', self.mock_summary_cache)
        self.summary_cache_patcher.start()
    
    def tearDown(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        self.summary_cache_patcher.stop()
    
    @patch('docdog.summary_cache.tiktoken.get_encoding')
    @patch('docdog.summary_cache.time.sleep')
    def test_batch_processing(self, mock_sleep, mock_get_encoding):
        mock_get_encoding.return_value = self.mock_encoding
        
        self.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary 1\n---\nSummary 2\n---\nSummary 3"))]
        )
        
        results = batch_summarize_chunks(self.chunk_files, self.client)
        
        self.assertEqual(len(results), len(self.chunk_files))
        
        self.assertEqual(self.client.chat.completions.create.call_count, 1)
        
        self.assertEqual(results[0]['summary'], "Summary 1")
        self.assertEqual(results[1]['summary'], "Summary 2")
        self.assertEqual(results[2]['summary'], "Summary 3")
        
        self.assertEqual(sum(r['cached'] for r in results), 0)

        for i, path in enumerate(self.chunk_files):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            cache_key = f"gpt-3.5-turbo_{content_hash}"
            memory_cache[cache_key] = f"Summary {i+1}"
        
        self.client.chat.completions.create.reset_mock()
        results2 = batch_summarize_chunks(self.chunk_files, self.client)
        
        self.assertEqual(self.client.chat.completions.create.call_count, 0)
        
        self.assertEqual(sum(r['cached'] for r in results2), len(self.chunk_files))
    
    @patch('docdog.summary_cache.tiktoken.get_encoding')
    @patch('docdog.summary_cache.time.sleep')
    def test_batch_size_limiting(self, mock_sleep, mock_get_encoding):
        mock_get_encoding.return_value = self.mock_encoding

        self.mock_encoding.encode.side_effect = lambda x: [1] * 15000  
        self.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary for single chunk"))]
        )
        
        results = batch_summarize_chunks(self.chunk_files, self.client, model="gpt-3.5-turbo")
        
        self.assertEqual(len(results), len(self.chunk_files))

        self.assertGreaterEqual(self.client.chat.completions.create.call_count, 3)
    
    @patch('docdog.summary_cache.tiktoken.get_encoding')
    @patch('docdog.summary_cache.time.sleep')
    @patch('docdog.summary_cache.summarize_chunk_with_retry')
    def test_batch_fallback(self, mock_summarize, mock_sleep, mock_get_encoding):
        mock_get_encoding.return_value = self.mock_encoding
        
        self.client.chat.completions.create.side_effect = Exception("Batch processing failed")
        
        mock_summarize.return_value = {'file': 'test.py', 'summary': 'Fallback summary', 'cached': False}
        
        results = batch_summarize_chunks(self.chunk_files, self.client)
        
        self.assertEqual(mock_summarize.call_count, len(self.chunk_files))
        
        self.assertEqual(len(results), len(self.chunk_files))
    
    @patch('docdog.summary_cache.tiktoken.get_encoding')
    def test_file_error_handling(self, mock_get_encoding):
        mock_get_encoding.return_value = self.mock_encoding
        
        with patch('builtins.open', side_effect=Exception("File read error")):
            results = batch_summarize_chunks(self.chunk_files, self.client)
            
            self.assertEqual(len(results), len(self.chunk_files))
            
            for result in results:
                self.assertIn('error', result)
                self.assertIn('Error reading file', result['summary'])


if __name__ == '__main__':
    unittest.main()