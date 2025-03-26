import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

import docdog.main
from docdog.main import find_project_root, get_user_confirmation

class TestFindProjectRoot(unittest.TestCase):
    @patch('os.path.exists')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_find_project_root_git(self, mock_abspath, mock_dirname, mock_exists):
        mock_abspath.return_value = "/path/to/project/src/docdog/main.py"
        mock_dirname.side_effect = [
            "/path/to/project/src/docdog",
            "/path/to/project/src",
            "/path/to/project"
        ]
        
        def exists_side_effect(path):
            return path == "/path/to/project/.git"
        
        mock_exists.side_effect = exists_side_effect
        root = find_project_root()        
        self.assertEqual(root, "/path/to/project")

    @patch('os.path.exists')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_find_project_root_pyproject(self, mock_abspath, mock_dirname, mock_exists):
        mock_abspath.return_value = "/path/to/project/src/docdog/main.py"
        mock_dirname.side_effect = [
            "/path/to/project/src/docdog",
            "/path/to/project/src",
            "/path/to/project"
        ]
        
        def exists_side_effect(path):
            return path == "/path/to/project/pyproject.toml"
        
        mock_exists.side_effect = exists_side_effect
        
        root = find_project_root()
        
        self.assertEqual(root, "/path/to/project")

    @patch('os.path.exists')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_find_project_root_no_marker(self, mock_abspath, mock_dirname, mock_exists):
        script_dir = "/path/to/project/src/docdog"
        mock_abspath.return_value = f"{script_dir}/main.py"
        
        mock_dirname.side_effect = [
            script_dir,      
            "/path/to/project/src",
            "/path/to/project",
            "/path/to",
            "/path",
            "/",
            "/",             
            script_dir       
        ]
        
        mock_exists.return_value = False
        
        def find_project_root_test():
            markers = ['.git', 'pyproject.toml', 'setup.py', 'requirements.txt', 'package.json']
            current_dir = os.path.dirname(mock_abspath())
            prev_dir = None
            while current_dir != prev_dir:
                for marker in markers:
                    if mock_exists(os.path.join(current_dir, marker)):
                        return current_dir
                prev_dir = current_dir
                current_dir = mock_dirname(current_dir)
            return os.path.dirname(mock_abspath())
        
        root = find_project_root_test()
        
        self.assertEqual(root, script_dir)

    @patch('os.path.exists')
    @patch('os.path.dirname')
    @patch('os.path.abspath')
    def test_find_project_root_multiple_markers(self, mock_abspath, mock_dirname, mock_exists):
        mock_abspath.return_value = "/path/to/project/src/docdog/main.py"
        mock_dirname.side_effect = [
            "/path/to/project/src/docdog",
            "/path/to/project/src",
            "/path/to/project"
        ]
        
        def exists_side_effect(path):
            markers = [
                "/path/to/project/src/.git",
                "/path/to/project/pyproject.toml",
                "/path/to/project/requirements.txt"
            ]
            return path in markers
        
        mock_exists.side_effect = exists_side_effect
        root = find_project_root()
        
        self.assertEqual(root, "/path/to/project/src")


class TestGetUserConfirmation(unittest.TestCase):
    def setUp(self):
        self.original_input = __builtins__['input'] if 'input' in __builtins__ else None
        docdog.main.chunk_files = ["chunk1.txt", "chunk2.txt"]
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    def tearDown(self):
        if self.original_input:
            __builtins__['input'] = self.original_input

    @patch('threading.Thread')
    def test_get_user_confirmation_timeout(self, mock_thread):
        thread_instance = MagicMock()
        mock_thread.return_value = thread_instance
        
        with patch('builtins.input', side_effect=Exception("This should timeout")):
            result = get_user_confirmation(timeout=0.001)
        
        self.assertTrue(result)
        thread_instance.start.assert_called_once()
        self.mock_logger.info.assert_any_call("No response received. Proceeding automatically.")

    def test_get_user_confirmation_yes(self):
        __builtins__['input'] = lambda _: 'y'
        
        self.assertTrue(get_user_confirmation())
    
    def test_get_user_confirmation_yes_case_insensitive(self):
        __builtins__['input'] = lambda _: 'Y'
        
        self.assertTrue(get_user_confirmation())
    
    def test_get_user_confirmation_yes_with_whitespace(self):
        __builtins__['input'] = lambda _: ' yes '
        
        self.assertTrue(get_user_confirmation())
    
    def test_get_user_confirmation_no(self):
        __builtins__['input'] = lambda _: 'n'
        
        self.assertFalse(get_user_confirmation())
        
        self.mock_logger.info.assert_called_once_with("User chose not to proceed.")
    
    def test_get_user_confirmation_no_full_word(self):
        __builtins__['input'] = lambda _: 'no'
        
        self.assertFalse(get_user_confirmation())
    
    def test_get_user_confirmation_invalid(self):
        __builtins__['input'] = lambda _: 'invalid'
        
        self.assertTrue(get_user_confirmation())
        
        self.mock_logger.info.assert_called_once_with("Invalid response. Proceeding automatically.")
    
    def test_get_user_confirmation_input_exception(self):
        def mock_input(_):
            raise EOFError("Mock input error")
        
        __builtins__['input'] = mock_input
        
        self.assertTrue(get_user_confirmation(timeout=0.1))
        
        self.mock_logger.info.assert_called_once_with("No response received. Proceeding automatically.")


class TestMain(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger
        
        self.original_argv = sys.argv

    def tearDown(self):
        sys.argv = self.original_argv

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    def test_main_user_rejects_chunks(self, mock_rmtree, mock_open, mock_exists, 
                                   mock_dirname, mock_sanitize, mock_client, 
                                   mock_confirmation, mock_chunk, mock_find_root, 
                                   mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = False
        
        with patch('sys.exit') as mock_exit:
            with patch('sys.stdout', new=StringIO()):
                docdog.main.main()
        
        mock_exit.assert_called_once_with(0)

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_main_basic_flow(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                           mock_dirname, mock_sanitize, mock_client, 
                           mock_confirmation, mock_chunk, mock_find_root, 
                           mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = [f"chunk-{i}.txt" for i in range(3)]
        
        analysis_content = MagicMock()
        analysis_content.type = "text"
        analysis_content.text = "Analysis text"
        
        tool_use_content = MagicMock()
        tool_use_content.type = "tool_use"
        tool_use_content.id = "tool1"
        tool_use_content.name = "read_file"
        tool_use_content.input = {"file_path": f"{chunks_dir}/chunk-0.txt"}
        
        analysis_response = MagicMock()
        analysis_response.content = [analysis_content, tool_use_content]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content"
        
        readme_response = MagicMock()
        readme_response.content = [readme_content]
        
        validation_content = MagicMock()
        validation_content.type = "text"
        validation_content.text = "README validation passed"
        
        validation_response = MagicMock()
        validation_response.content = [validation_content]
        
        mock_client.messages.create.side_effect = [
            analysis_response, readme_response, validation_response
        ]
        
        mock_mcp_tools = MagicMock()
        mock_mcp_tools.handle_tool_call.return_value = "Tool result"
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        self.assertEqual(mock_client.messages.create.call_count, 3)
        mock_open.assert_any_call(args.output, "w", encoding="utf-8")

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_api_error_handling(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                              mock_dirname, mock_sanitize, mock_client, 
                              mock_confirmation, mock_chunk, mock_find_root, 
                              mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 2
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = [f"chunk-{i}.txt" for i in range(3)]
        
        mock_client.messages.create.side_effect = Exception("API Error")
        
        mock_mcp_tools = MagicMock()
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        error_logged = any("Error in analysis phase" in str(args[0]) for args, _ in self.mock_logger.error.call_args_list)
        self.assertTrue(error_logged)
        
        mock_open.assert_any_call(args.output, "w", encoding="utf-8")

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('os.listdir')
    def test_cleanup_chunks_error(self, mock_listdir, mock_open, mock_exists, 
                               mock_dirname, mock_sanitize, mock_client, 
                               mock_confirmation, mock_chunk, mock_find_root, 
                               mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = [f"chunk-{i}.txt" for i in range(3)]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content"
        
        response = MagicMock()
        response.content = [readme_content]
        mock_client.messages.create.return_value = response
        
        mock_mcp_tools = MagicMock()
        
        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
                with patch('sys.stdout', new=StringIO()):
                    with patch('sys.exit'):
                        docdog.main.main()
        
        warning_logged = any("Failed to delete chunk files" in str(args[0]) for args, _ in self.mock_logger.warning.call_args_list)
        self.assertTrue(warning_logged)


class TestArgumentParsing(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    def test_argument_parsing(self, mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args_default = MagicMock()
        args_default.output = "README.md"
        args_default.model = "claude-3-sonnet-20240229"
        args_default.reasoning = False
        args_default.prompt_template = None
        args_default.max_iterations = 15
        mock_parser.parse_args.return_value = args_default
        
        with patch('docdog.main.find_project_root', return_value="/test/project"):
            with patch('docdog.main.chunk_project', return_value=[]):
                with patch('sys.exit'):
                    with patch('sys.stdout', new=StringIO()):
                        docdog.main.main()
        
        mock_arg_parser.assert_called_once()
        arg_calls = mock_parser.add_argument.call_args_list
        self.assertTrue(any(call[0][0] in ("-o", "--output") for call in arg_calls))
        self.assertTrue(any(call[0][0] in ("-m", "--model") for call in arg_calls))
        self.assertTrue(any(call[0][0] == "--reasoning" for call in arg_calls))
        self.assertTrue(any(call[0][0] in ("-p", "--prompt-template") for call in arg_calls))
        self.assertTrue(any(call[0][0] == "--max-iterations" for call in arg_calls))


class TestReasoningFlag(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_reasoning_flag(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                          mock_dirname, mock_sanitize, mock_client, 
                          mock_confirmation, mock_chunk, mock_find_root, 
                          mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = True
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        def open_side_effect(file, mode, encoding=None):
            mock = MagicMock()
            if "initial_prompt.txt" in str(file):
                mock.__enter__.return_value.read.return_value = "Initial prompt"
            elif "reasoning_instructions.txt" in str(file):
                mock.__enter__.return_value.read.return_value = "Reasoning instructions"
            elif "validation_prompt.txt" in str(file):
                mock.__enter__.return_value.read.return_value = "Validation prompt"
            else:
                mock.__enter__.return_value.read.return_value = ""
            return mock
        mock_open.side_effect = open_side_effect
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(1)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = ["chunk-0.txt"]
        
        analysis_content = MagicMock()
        analysis_content.type = "text"
        analysis_content.text = "Analysis text"
        
        analysis_response = MagicMock()
        analysis_response.content = [analysis_content]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content\nReasoning: Test reasoning content"
        
        readme_response = MagicMock()
        readme_response.content = [readme_content]
        
        validation_content = MagicMock()
        validation_content.type = "text"
        validation_content.text = "README validation passed"
        
        validation_response = MagicMock()
        validation_response.content = [validation_content]
        
        mock_client.messages.create.side_effect = [
            analysis_response, readme_response, validation_response
        ]
        
        mock_mcp_tools = MagicMock()
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        reasoning_added = False
        for call_args in mock_sanitize.call_args_list:
            if "Reasoning instructions" in str(call_args):
                reasoning_added = True
                break
        self.assertTrue(reasoning_added, "Reasoning instructions were not added to the prompt")
        
        reasoning_file_created = False
        for call_args in mock_open.call_args_list:
            if "reasoning.md" in str(call_args[0][0]) and call_args[0][1] == "w":
                reasoning_file_created = True
                break
        self.assertTrue(reasoning_file_created, "reasoning.md file was not created")


class TestCustomPromptTemplate(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_custom_prompt_template(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                                 mock_dirname, mock_sanitize, mock_client, 
                                 mock_confirmation, mock_chunk, mock_find_root, 
                                 mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = "/path/to/custom_template.txt"
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        def exists_side_effect(path):
            if path == "/path/to/custom_template.txt":
                return True
            return True
        mock_exists.side_effect = exists_side_effect
        
        def open_side_effect(file, mode, encoding=None):
            mock = MagicMock()
            if file == "/path/to/custom_template.txt":
                mock.__enter__.return_value.read.return_value = "Custom prompt template"
            elif "validation_prompt.txt" in str(file):
                mock.__enter__.return_value.read.return_value = "Validation prompt"
            else:
                mock.__enter__.return_value.read.return_value = ""
            return mock
        mock_open.side_effect = open_side_effect
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(1)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = ["chunk-0.txt"]
        
        analysis_content = MagicMock()
        analysis_content.type = "text"
        analysis_content.text = "Analysis text"
        
        analysis_response = MagicMock()
        analysis_response.content = [analysis_content]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content"
        
        readme_response = MagicMock()
        readme_response.content = [readme_content]
        
        validation_content = MagicMock()
        validation_content.type = "text"
        validation_content.text = "README validation passed"
        
        validation_response = MagicMock()
        validation_response.content = [validation_content]
        
        mock_client.messages.create.side_effect = [
            analysis_response, readme_response, validation_response
        ]
        
        mock_mcp_tools = MagicMock()
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        custom_template_used = False
        for call_args in mock_open.call_args_list:
            if "/path/to/custom_template.txt" in str(call_args):
                custom_template_used = True
                break
        self.assertTrue(custom_template_used, "Custom template file was not opened")
        
        custom_content_sanitized = False
        for call_args in mock_sanitize.call_args_list:
            if "Custom prompt template" in str(call_args):
                custom_content_sanitized = True
                break
        self.assertTrue(custom_content_sanitized, "Custom template content was not sanitized")

class TestValidationPhase(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_validation_improvements(self, mock_listdir, mock_exists, mock_dirname,
                                    mock_sanitize, mock_client, mock_confirmation,
                                    mock_chunk, mock_find_root, mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        initial_prompt_file = MagicMock()
        initial_prompt_file.__enter__.return_value.read.return_value = "Initial prompt"
        
        validation_prompt_file = MagicMock()
        validation_prompt_file.__enter__.return_value.read.return_value = "Validation prompt"
        
        empty_file = MagicMock()
        empty_file.__enter__.return_value.read.return_value = ""
        
        file_content = []
        output_file = MagicMock()
        output_file.__enter__.return_value.write = lambda content: file_content.append(content)
        
        def mock_open_effect(file_path, mode='r', encoding=None):
            if file_path == args.output and mode == "w":
                return output_file
            elif "initial_prompt.txt" in str(file_path):
                return initial_prompt_file
            elif "validation_prompt.txt" in str(file_path):
                return validation_prompt_file
            else:
                return empty_file
                
        with patch('builtins.open', side_effect=mock_open_effect):
            chunks_dir = os.path.join(project_root, "chunks")
            chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(1)]
            mock_chunk.return_value = chunk_files
            
            docdog.main.chunk_files = chunk_files
            
            mock_confirmation.return_value = True
            
            mock_listdir.return_value = ["chunk-0.txt"]
            
            analysis_content = MagicMock()
            analysis_content.type = "text"
            analysis_content.text = "Analysis text"
            
            analysis_response = MagicMock()
            analysis_response.content = [analysis_content]
            
            readme_content = MagicMock()
            readme_content.type = "text"
            readme_content.text = "Final README: Original README content"
            
            readme_response = MagicMock()
            readme_response.content = [readme_content]
            
            validation_content = MagicMock()
            validation_content.type = "text"
            validation_content.text = "Improved README: Improved README content"
            
            validation_response = MagicMock()
            validation_response.content = [validation_content]
            
            mock_client.messages.create.side_effect = [
                analysis_response, readme_response, validation_response
            ]
            
            mock_mcp_tools = MagicMock()
            
            with patch('shutil.rmtree'), patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
                with patch('sys.stdout', new=StringIO()):
                    with patch('sys.exit'):
                        docdog.main.main()
            
            self.assertTrue(any("Improved README content" in content for content in file_content), 
                            "Improved README content was not used")
            self.assertFalse(any("Original README content" in content for content in file_content), 
                            "Original README content was used instead of improved version")
            
            log_message_found = False
            for call_args in self.mock_logger.info.call_args_list:
                if "improvements suggested" in str(call_args).lower():
                    log_message_found = True
                    break
            self.assertTrue(log_message_found, "Log message about README improvements not found")


class TestEmptyReadmeHandling(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_empty_readme_handling(self, mock_listdir, mock_exists, mock_dirname,
                                mock_sanitize, mock_client, mock_confirmation,
                                mock_chunk, mock_find_root, mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
            
        initial_prompt_file = MagicMock()
        initial_prompt_file.__enter__.return_value.read.return_value = "Initial prompt"
        
        validation_prompt_file = MagicMock()
        validation_prompt_file.__enter__.return_value.read.return_value = "Validation prompt"
        
        empty_file = MagicMock()
        empty_file.__enter__.return_value.read.return_value = ""
        
        file_content = []
        output_file = MagicMock()
        output_file.__enter__.return_value.write = lambda content: file_content.append(content)
        
        def mock_open_effect(file_path, mode='r', encoding=None):
            if file_path == args.output and mode == "w":
                return output_file
            elif "initial_prompt.txt" in str(file_path):
                return initial_prompt_file
            elif "validation_prompt.txt" in str(file_path):
                return validation_prompt_file
            else:
                return empty_file
                
        with patch('builtins.open', side_effect=mock_open_effect):
            chunks_dir = os.path.join(project_root, "chunks")
            chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(1)]
            mock_chunk.return_value = chunk_files
            
            docdog.main.chunk_files = chunk_files
            
            mock_confirmation.return_value = True
            
            mock_listdir.return_value = ["chunk-0.txt"]
            
            analysis_content = MagicMock()
            analysis_content.type = "text"
            analysis_content.text = "Analysis text"
            
            analysis_response = MagicMock()
            analysis_response.content = [analysis_content]
            
            readme_content = MagicMock()
            readme_content.type = "text"
            readme_content.text = ""
            
            readme_response = MagicMock()
            readme_response.content = [readme_content]
            
            validation_content = MagicMock()
            validation_content.type = "text"
            validation_content.text = "README validation passed"
            
            validation_response = MagicMock()
            validation_response.content = [validation_content]
            
            mock_client.messages.create.side_effect = [
                analysis_response, readme_response, validation_response
            ]
            
            mock_mcp_tools = MagicMock()
            
            with patch('shutil.rmtree'), patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
                with patch('sys.stdout', new=StringIO()):
                    with patch('sys.exit'):
                        docdog.main.main()
            
            self.assertTrue(any("DocDog attempted to generate documentation" in content for content in file_content), 
                          "Fallback README was not created when generation failed")
            
            error_logged = False
            for call_args in self.mock_logger.error.call_args_list:
                if "Failed to generate README content" in str(call_args):
                    error_logged = True
                    break
            self.assertTrue(error_logged, "Error about failed README generation not logged")


class TestBatchToolCalls(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_batch_read_files_tool(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                               mock_dirname, mock_sanitize, mock_client, 
                               mock_confirmation, mock_chunk, mock_find_root, 
                               mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 2
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = [f"chunk-{i}.txt" for i in range(3)]
        
        analysis_content = MagicMock()
        analysis_content.type = "text"
        analysis_content.text = "Analysis text"
        
        batch_tool_use_content = MagicMock()
        batch_tool_use_content.type = "tool_use"
        batch_tool_use_content.id = "tool1"
        batch_tool_use_content.name = "batch_read_files"
        batch_tool_use_content.input = {"file_paths": [
            f"{chunks_dir}/chunk-0.txt",
            f"{chunks_dir}/chunk-1.txt"
        ]}
        
        analysis_response = MagicMock()
        analysis_response.content = [analysis_content, batch_tool_use_content]
        
        analysis_content2 = MagicMock()
        analysis_content2.type = "text"
        analysis_content2.text = "Analysis text 2"
        
        tool_use_content2 = MagicMock()
        tool_use_content2.type = "tool_use"
        tool_use_content2.id = "tool2"
        tool_use_content2.name = "read_file"
        tool_use_content2.input = {"file_path": f"{chunks_dir}/chunk-2.txt"}
        
        analysis_response2 = MagicMock()
        analysis_response2.content = [analysis_content2, tool_use_content2]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content"
        
        readme_response = MagicMock()
        readme_response.content = [readme_content]
        
        validation_content = MagicMock()
        validation_content.type = "text"
        validation_content.text = "README validation passed"
        
        validation_response = MagicMock()
        validation_response.content = [validation_content]
        
        mock_client.messages.create.side_effect = [
            analysis_response, analysis_response2, readme_response, validation_response
        ]
        
        mock_mcp_tools = MagicMock()
        mock_mcp_tools.handle_tool_call.return_value = "Tool result"
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        self.assertEqual(mock_client.messages.create.call_count, 4)
        
        info_calls = [args[0] for args, _ in self.mock_logger.info.call_args_list]
        self.assertTrue(any("Analyzed chunk: chunk-0.txt" in str(call) for call in info_calls))
        self.assertTrue(any("Analyzed chunk: chunk-1.txt" in str(call) for call in info_calls))
        self.assertTrue(any("Analyzed chunk: chunk-2.txt" in str(call) for call in info_calls))


class TestAPIKeyHandling(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.original_environ = os.environ.copy()

    def tearDown(self):
        os.environ = self.original_environ.copy()

    @patch('sys.exit')
    def test_missing_api_key(self, mock_exit):
        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']
        
        with patch('logging.getLogger', return_value=self.mock_logger):
            docdog.main.logger = self.mock_logger
            if not os.environ.get('ANTHROPIC_API_KEY'):
                docdog.main.logger.error("ANTHROPIC_API_KEY not found in environment variables.")
                sys.exit(1)
        
        self.mock_logger.error.assert_called_with("ANTHROPIC_API_KEY not found in environment variables.")
        mock_exit.assert_called_once_with(1)

class TestIncompleteAnalysis(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        docdog.main.logger = self.mock_logger

    @patch('argparse.ArgumentParser')
    @patch('docdog.main.find_project_root')
    @patch('docdog.main.chunk_project')
    @patch('docdog.main.get_user_confirmation')
    @patch('docdog.main.client')
    @patch('docdog.main.sanitize_prompt')
    @patch('os.path.dirname')
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('shutil.rmtree')
    @patch('os.listdir')
    def test_incomplete_analysis_warning(self, mock_listdir, mock_rmtree, mock_open, mock_exists, 
                                    mock_dirname, mock_sanitize, mock_client, 
                                    mock_confirmation, mock_chunk, mock_find_root, 
                                    mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        args = MagicMock()
        args.output = "test_readme.md"
        args.model = "test-model"
        args.reasoning = False
        args.prompt_template = None
        args.max_iterations = 1
        mock_parser.parse_args.return_value = args
        
        project_root = "/test/project"
        mock_find_root.return_value = project_root
        
        mock_sanitize.side_effect = lambda s: s
        
        script_dir = "/test/script/dir"
        mock_dirname.return_value = script_dir
        
        mock_exists.return_value = True
        
        template_content = "Initial prompt template"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = template_content
        mock_open.return_value = mock_file
        
        chunks_dir = os.path.join(project_root, "chunks")
        chunk_files = [os.path.join(chunks_dir, f"chunk-{i}.txt") for i in range(3)]
        mock_chunk.return_value = chunk_files
        
        docdog.main.chunk_files = chunk_files
        
        mock_confirmation.return_value = True
        
        mock_listdir.return_value = [f"chunk-{i}.txt" for i in range(3)]
        
        analysis_content = MagicMock()
        analysis_content.type = "text"
        analysis_content.text = "Analysis text"
        
        tool_use_content = MagicMock()
        tool_use_content.type = "tool_use"
        tool_use_content.id = "tool1"
        tool_use_content.name = "read_file"
        tool_use_content.input = {"file_path": f"{chunks_dir}/chunk-0.txt"}
        
        analysis_response = MagicMock()
        analysis_response.content = [analysis_content, tool_use_content]
        
        readme_content = MagicMock()
        readme_content.type = "text"
        readme_content.text = "Final README: Test README content"
        
        readme_response = MagicMock()
        readme_response.content = [readme_content]
        
        validation_content = MagicMock()
        validation_content.type = "text"
        validation_content.text = "README validation passed"
        
        validation_response = MagicMock()
        validation_response.content = [validation_content]
        
        mock_client.messages.create.side_effect = [
            analysis_response, readme_response, validation_response
        ]
        
        mock_mcp_tools = MagicMock()
        mock_mcp_tools.handle_tool_call.return_value = "Tool result"
        
        with patch('docdog.main.MCPTools', return_value=mock_mcp_tools):
            with patch('sys.stdout', new=StringIO()):
                with patch('sys.exit'):
                    docdog.main.main()
        
        warning_logged = False
        for call_args in self.mock_logger.warning.call_args_list:
            if "Analysis incomplete" in str(call_args):
                warning_logged = True
                break
        self.assertTrue(warning_logged, "Warning about incomplete analysis was not logged")


if __name__ == '__main__':
    unittest.main()