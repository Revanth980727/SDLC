
import logging
import unittest
import pytest
import os
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_framework.agent_base import Agent, AgentStatus
from agent_framework.planner_agent import PlannerAgent
from agent_framework.qa_agent import QAAgent

class TestAgentFramework(unittest.TestCase):
    """Test cases for the agent framework"""
    
    def setUp(self):
        """Set up test environment"""
        # Sample ticket data
        self.ticket_data = {
            "ticket_id": "TEST-123",
            "title": "Test bug ticket",
            "description": "This is a test bug description"
        }
    
    def test_planner_agent(self):
        """Test PlannerAgent"""
        # Initialize the planner
        planner = PlannerAgent()
        
        # Run analysis
        try:
            result = planner.process(self.ticket_data)
            logger.info(f"\nPlanner status: {planner.status}")
            logger.info(f"Analysis result: {result}")
            
            # Verify result structure
            self.assertIn("ticket_id", result)
            self.assertEqual(result["ticket_id"], "TEST-123")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            self.fail(f"PlannerAgent test failed: {str(e)}")
            
    def test_qa_agent_test_discovery(self):
        """Test QA agent's test discovery functionality"""
        qa = QAAgent()
        
        # Test _get_available_commands method
        commands = qa._get_available_commands()
        self.assertIsInstance(commands, list)
        
        # Test _get_best_test_command method
        test_command = qa._get_best_test_command("pytest", commands)
        self.assertIsInstance(test_command, str)
        
        # Test parsing functions
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
        
        failures = qa._parse_test_failures(sample_output, "")
        self.assertIsInstance(failures, list)
        self.assertTrue(len(failures) > 0)
        
    def test_failure_summary_generation(self):
        """Test failure summary generation"""
        qa = QAAgent()
        
        # Test _generate_failure_summary method
        test_results = [
            {"name": "test_pass", "status": "pass"},
            {"name": "test_fail", "status": "fail", "error_type": "AssertionError", "error_message": "Expected value was not equal to actual value"}
        ]
        
        summary = qa._generate_failure_summary(test_results)
        self.assertIsInstance(summary, str)
        self.assertIn("test_fail", summary)
        self.assertIn("AssertionError", summary)

def test_planner_agent_standalone():
    """Test PlannerAgent as a standalone function"""
    # Initialize the planner
    planner = PlannerAgent()
    
    # Test input
    test_ticket = {
        "ticket_id": "BUG-123",
        "title": "Fix login error in AuthService.tsx",
        "description": """
        When logging in on mobile devices, the handleLogin function in src/components/auth/AuthService.tsx
        throws an error. Stack trace shows:
        Error: Cannot read property 'data' of undefined
        
        This affects the following files:
        - src/components/auth/AuthService.tsx
        - src/utils/validation.ts
        - src/api/loginApi.ts
        
        The LoginComponent and ValidationHelper modules need to be checked.
        """
    }
    
    # Run analysis
    try:
        result = planner.process(test_ticket)
        logger.info(f"\nPlanner status: {planner.status}")
        logger.info(f"Analysis result: {result}")
        
        assert "ticket_id" in result
        assert result["ticket_id"] == "BUG-123"
        
        # Also test fallback functionality by forcing an invalid response
        logger.info("\nTesting fallback functionality:")
        
        # Create a test version of the planner that returns invalid JSON
        class TestPlannerWithForcedFailure(PlannerAgent):
            def _query_gpt(self, prompt: str) -> str:
                # Return invalid JSON to trigger fallback
                return "This is not JSON and will trigger the fallback mechanism"
        
        test_planner = TestPlannerWithForcedFailure()
        fallback_result = test_planner.process(test_ticket)
        
        logger.info(f"Fallback result: {fallback_result}")
        logger.info(f"Is using fallback: {fallback_result.get('using_fallback', False)}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        assert False, f"PlannerAgent test failed: {str(e)}"

if __name__ == "__main__":
    unittest.main()
