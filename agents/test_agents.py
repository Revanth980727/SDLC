
#!/usr/bin/env python3
import unittest
import os
from unittest.mock import MagicMock, patch
from agents.planner_agent import PlannerAgent
from agents.developer_agent import DeveloperAgent
from agents.qa_agent import QAAgent
from agents.communicator_agent import CommunicatorAgent
from agents.agent_controller import AgentController

class TestAgents(unittest.TestCase):
    """Test cases for the agent system"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPO_OWNER': 'test-owner',
            'GITHUB_REPO_NAME': 'test-repo',
            'JIRA_URL': 'https://test.atlassian.net',
            'JIRA_USER': 'test-user',
            'JIRA_TOKEN': 'test-token',
            'REPO_PATH': '/tmp/test-repo'
        })
        self.env_patcher.start()
        
        # Sample ticket data
        self.ticket_data = {
            "ticket_id": "TEST-123",
            "title": "Test bug ticket",
            "description": "This is a test bug description"
        }
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    @patch('agents.planner_agent.PlannerAgent._query_gpt')
    def test_planner_agent(self, mock_query_gpt):
        """Test PlannerAgent"""
        # Mock GPT response
        mock_query_gpt.return_value = """
        {
            "root_cause": "Test root cause",
            "severity": "medium",
            "files": [
                {
                    "path": "src/main.py",
                    "reason": "Contains the bug"
                }
            ],
            "approach": "Fix the bug",
            "implementation_details": "Add a null check",
            "potential_risks": "None"
        }
        """
        
        # Run the planner agent
        agent = PlannerAgent()
        result = agent.run(self.ticket_data)
        
        # Verify result structure
        self.assertIn("root_cause", result)
        self.assertIn("files", result)
        self.assertIn("approach", result)
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["path"], "src/main.py")
    
    @patch('agents.developer_agent.DeveloperAgent._query_gpt')
    @patch('agents.developer_agent.DeveloperAgent._read_identified_files')
    def test_developer_agent(self, mock_read_files, mock_query_gpt):
        """Test DeveloperAgent"""
        # Mock file reading
        mock_read_files.return_value = {
            "src/main.py": "def main():\n    print('Hello, world!')\n"
        }
        
        # Mock GPT response
        mock_query_gpt.return_value = """
        Fix TEST-123: Add error handling
        
        ```patch
        --- a/src/main.py
        +++ b/src/main.py
        @@ -1,2 +1,5 @@
         def main():
        -    print('Hello, world!')
        +    try:
        +        print('Hello, world!')
        +    except Exception as e:
        +        print(f"Error: {str(e)}")
        ```
        """
        
        # Run the developer agent
        agent = DeveloperAgent()
        task_plan = {
            "ticket_id": "TEST-123",
            "root_cause": "Missing error handling",
            "files": [{"path": "src/main.py"}],
            "approach": "Add try/except block"
        }
        result = agent.run(task_plan)
        
        # Verify result structure
        self.assertIn("patch_content", result)
        self.assertIn("patched_files", result)
        self.assertIn("commit_message", result)
        self.assertIn("src/main.py", result["patched_files"])
        self.assertIn("try:", result["patch_content"])
    
    @patch('subprocess.run')
    def test_qa_agent(self, mock_run):
        """Test QAAgent"""
        # Mock subprocess.run
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.stdout = "All tests passed"
        process_mock.stderr = ""
        mock_run.return_value = process_mock
        
        # Run the QA agent
        agent = QAAgent()
        result = agent.run({
            "ticket_id": "TEST-123",
            "test_command": "pytest"
        })
        
        # Verify result structure
        self.assertIn("passed", result)
        self.assertTrue(result["passed"])
        self.assertIn("execution_time", result)
        self.assertIn("output", result)
    
    @patch('agents.utils.jira_client.JiraClient.add_comment')
    @patch('agents.utils.jira_client.JiraClient.update_ticket')
    @patch('agents.utils.github_client.GitHubClient.create_branch')
    @patch('agents.utils.github_client.GitHubClient.create_pull_request')
    def test_communicator_agent(self, mock_create_pr, mock_create_branch, 
                             mock_update_ticket, mock_add_comment):
        """Test CommunicatorAgent"""
        # Set up mocks
        mock_create_branch.return_value = True
        mock_create_pr.return_value = "https://github.com/test/test/pull/1"
        mock_update_ticket.return_value = True
        mock_add_comment.return_value = True
        
        # Run the communicator agent
        agent = CommunicatorAgent()
        
        # Test successful case
        result = agent.run({
            "ticket_id": "TEST-123",
            "patch_data": {
                "patch_content": "test patch",
                "patched_files": ["src/main.py"],
                "commit_message": "Fix bug",
                "attempt": 1
            },
            "test_results": {
                "passed": True,
                "execution_time": 1.5
            },
            "task_plan": {
                "root_cause": "Test root cause",
                "approach": "Test approach"
            }
        })
        
        # Verify result structure
        self.assertIn("jira_updated", result)
        self.assertIn("pr_created", result)
        self.assertIn("pr_url", result)
        self.assertTrue(result["jira_updated"])
        self.assertTrue(result["pr_created"])
        self.assertEqual(result["pr_url"], "https://github.com/test/test/pull/1")

if __name__ == "__main__":
    unittest.main()
