
import logging
import unittest
import pytest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_framework.agent_base import Agent, AgentStatus
from agent_framework.qa_agent import QAAgent

class TestQAAgent(unittest.TestCase):
    """Test cases for the QA Agent"""
    
    def setUp(self):
        """Set up the test environment"""
        self.qa_agent = QAAgent()
        
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.qa_agent.repo_path = self.temp_dir.name
        
        # Create test data
        self.test_input = {
            "ticket_id": "BUG-123",
            "test_command": "npm test",
            "target": "src/components/auth"
        }
        
    def tearDown(self):
        """Clean up after tests"""
        self.temp_dir.cleanup()
    
    @patch('subprocess.Popen')
    def test_run_test_command_success(self, mock_popen):
        """Test running a test command that succeeds"""
        # Mock the Popen process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("All tests passed", "")
        mock_popen.return_value = mock_process
        
        # Run the test command
        result = self.qa_agent._run_test_command("npm test")
        
        # Verify the result
        self.assertTrue(result["passed"])
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("All tests passed", result["stdout"])
        self.assertEqual(len(result["test_results"]), 1)
        self.assertEqual(result["test_results"][0]["status"], "pass")
    
    @patch('subprocess.Popen')
    def test_run_test_command_failure(self, mock_popen):
        """Test running a test command that fails"""
        # Mock the Popen process
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (
            "Error: Test failed\nFAILED test_example.py::test_fail",
            "AssertionError: assert False"
        )
        mock_popen.return_value = mock_process
        
        # Run the test command
        result = self.qa_agent._run_test_command("pytest")
        
        # Verify the result
        self.assertFalse(result["passed"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("FAILED test_example", result["stdout"])
        self.assertIn("AssertionError", result["stderr"])
        self.assertTrue(len(result["test_results"]) > 0)
        self.assertEqual(result["test_results"][0]["status"], "fail")
    
    @patch('subprocess.Popen')
    def test_run_test_command_timeout(self, mock_popen):
        """Test handling of timeout during test execution"""
        # Mock the Popen process to raise TimeoutExpired
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("npm test", 300)
        mock_popen.return_value = mock_process
        
        # Run the test command
        result = self.qa_agent._run_test_command("npm test", timeout=300)
        
        # Verify the result
        self.assertFalse(result["passed"])
        self.assertEqual(result["exit_code"], -1)
        self.assertIn("timeout", result["stderr"].lower())
        self.assertEqual(result["test_results"][0]["error_type"], "Timeout")
    
    def test_parse_pytest_failures(self):
        """Test parsing of pytest failure output"""
        # Sample pytest output with a failure
        sample_output = """
        ============================= test session starts ==============================
        platform linux -- Python 3.9.10, pytest-7.0.1
        rootdir: /app/tests
        collected 2 items
        
        test_example.py F.                                                      [100%]
        
        =================================== FAILURES ===================================
        _________________________________ test_fail __________________________________
        
        def test_fail():
        >       assert False
        E       assert False
        
        test_example.py:5: AssertionError
        =========================== 1 failed, 1 passed ============================
        """
        
        failures = self.qa_agent._parse_pytest_failures(sample_output)
        
        # Verify the parsing results
        self.assertTrue(len(failures) > 0)
        self.assertIn("test_fail", failures[0].get("test_name", ""))
        self.assertIn("AssertionError", failures[0].get("error_type", ""))
    
    def test_parse_unittest_failures(self):
        """Test parsing of unittest failure output"""
        # Sample unittest output with a failure
        sample_output = """
        Ran 3 tests in 0.005s
        
        FAILED (failures=1)
        
        FAIL: test_fail (tests.test_example.ExampleTest)
        ----------------------------------------------------------------------
        Traceback (most recent call last):
          File "/app/tests/test_example.py", line 10, in test_fail
            self.assertEqual(1, 2)
        AssertionError: 1 != 2
        """
        
        failures = self.qa_agent._parse_unittest_failures(sample_output)
        
        # Verify the parsing results
        self.assertTrue(len(failures) > 0)
        self.assertIn("test_fail", failures[0].get("test_name", ""))
        self.assertIn("AssertionError", failures[0].get("error_type", ""))
        
    def test_parse_jest_failures(self):
        """Test parsing of Jest/Node test failures"""
        # Sample Jest output with a failure
        sample_output = """
        FAIL  src/components/auth/__tests__/AuthService.test.js
          ● AuthService › should handle login
        
            Expected value to be defined, but got undefined
            
              10 | test('should handle login', () => {
              11 |   const result = authService.handleLogin();
            > 12 |   expect(result).toBeDefined();
                 |                  ^
              13 | });
              
        Test Suites: 1 failed, 0 passed, 1 total
        Tests:       1 failed, 0 passed, 1 total
        """
        
        failures = self.qa_agent._parse_jest_failures(sample_output)
        
        # Verify the parsing results
        self.assertTrue(len(failures) > 0)
        self.assertIn("AuthService › should handle login", failures[0].get("test_name", ""))
        
    @patch('subprocess.run')
    def test_get_available_commands(self, mock_run):
        """Test detection of available test commands"""
        # Mock subprocess.run to simulate available commands
        mock_run.return_value = MagicMock(returncode=0)
        
        commands = self.qa_agent._get_available_commands()
        
        # Verify that commands is a list
        self.assertIsInstance(commands, list)
        
    def test_generate_failure_summary(self):
        """Test generation of failure summaries"""
        # Sample test results
        test_results = [
            {"name": "test_pass", "status": "pass"},
            {
                "name": "test_fail_1", 
                "status": "fail",
                "error_type": "AssertionError",
                "error_message": "Expected value to be true but got false"
            },
            {
                "name": "test_fail_2", 
                "status": "fail",
                "error_type": "TypeError",
                "error_message": "Cannot read property 'data' of undefined"
            }
        ]
        
        summary = self.qa_agent._generate_failure_summary(test_results)
        
        # Verify the summary
        self.assertIn("test_fail_1", summary)
        self.assertIn("AssertionError", summary)
        self.assertIn("test_fail_2", summary)
        self.assertIn("TypeError", summary)

    @patch('subprocess.Popen')
    def test_qa_agent_run(self, mock_popen):
        """Test the QA agent's run method"""
        # Mock the Popen process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("All tests passed", "")
        mock_popen.return_value = mock_process
        
        # Run the QA agent
        result = self.qa_agent.run(self.test_input)
        
        # Verify the result
        self.assertEqual(result["ticket_id"], "BUG-123")
        self.assertTrue(result["passed"])
        self.assertTrue(len(result["test_results"]) > 0)
        
        # Check agent status
        self.assertEqual(self.qa_agent.status, AgentStatus.SUCCESS)

def test_qa_agent():
    """Simple test function for running the QA agent directly"""
    # Initialize the QA agent
    qa = QAAgent()
    
    # Test input
    test_input = {
        "ticket_id": "BUG-123",
        "test_command": "npm test",
        "target": "src/components/auth"
    }
    
    # Run QA agent with mocked subprocess
    with patch('subprocess.Popen') as mock_popen:
        # Mock the Popen process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("All tests passed", "")
        mock_popen.return_value = mock_process
        
        # Run QA agent
        try:
            result = qa.run(test_input)
            logger.info(f"\nQA Agent status: {qa.status}")
            logger.info(f"Processing result: {result}")
            assert result["passed"] == True
            assert len(result["test_results"]) > 0
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            assert False, f"Test failed: {str(e)}"

if __name__ == "__main__":
    unittest.main()