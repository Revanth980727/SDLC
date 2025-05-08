
import asyncio
import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator import Orchestrator
from agent_framework.agent_base import AgentStatus

# Ensure we have subprocess available for mocking
import subprocess


@pytest.fixture
def mock_jira_client():
    """Create a mock JIRA client"""
    mock = MagicMock()
    mock.fetch_bug_tickets = AsyncMock(return_value=[
        {
            "ticket_id": "BUG-123",
            "title": "Test Bug",
            "description": "This is a test bug description"
        }
    ])
    mock.add_comment = AsyncMock(return_value=True)
    mock.update_ticket = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_github_service():
    """Create a mock GitHub service"""
    mock = MagicMock()
    mock.create_branch = MagicMock(return_value="fix/BUG-123")
    mock.create_pull_request = MagicMock(return_value="https://github.com/org/repo/pull/123")
    mock.add_pr_comment = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_planner_agent():
    """Create a mock Planner agent"""
    mock = MagicMock()
    mock.process = MagicMock(return_value={
        "ticket_id": "BUG-123",
        "affected_files": ["src/components/test.js"],
        "root_cause": "Test root cause",
        "suggested_approach": "Test approach"
    })
    mock.name = "PlannerAgent"
    mock.status = AgentStatus.SUCCESS
    return mock


@pytest.fixture
def mock_developer_agent():
    """Create a mock Developer agent"""
    mock = MagicMock()
    mock.process = MagicMock(return_value={
        "ticket_id": "BUG-123",
        "files_modified": ["src/components/test.js"],
        "patches_applied": 1,
        "diff_summary": "1 change applied"
    })
    mock.name = "DeveloperAgent"
    mock.status = AgentStatus.SUCCESS
    return mock


@pytest.fixture
def mock_qa_agent_success():
    """Create a mock QA agent that succeeds"""
    mock = MagicMock()
    mock.process = MagicMock(return_value={
        "ticket_id": "BUG-123",
        "passed": True,
        "test_results": [{"name": "test1", "status": "pass"}]
    })
    mock.name = "QAAgent"
    mock.status = AgentStatus.SUCCESS
    return mock


@pytest.fixture
def mock_qa_agent_failure():
    """Create a mock QA agent that fails"""
    mock = MagicMock()
    mock.process = MagicMock(return_value={
        "ticket_id": "BUG-123",
        "passed": False,
        "test_results": [{"name": "test1", "status": "fail"}]
    })
    mock.name = "QAAgent"
    mock.status = AgentStatus.FAILED
    return mock


@pytest.fixture
def mock_communicator_agent():
    """Create a mock Communicator agent"""
    mock = MagicMock()
    mock.process = MagicMock(return_value={
        "ticket_id": "BUG-123",
        "communications_success": True,
        "jira_updated": True,
        "github_updated": True
    })
    mock.name = "CommunicatorAgent"
    mock.status = AgentStatus.SUCCESS
    return mock


@pytest.mark.asyncio
async def test_successful_ticket_processing(
    mock_jira_client,
    mock_github_service,
    mock_planner_agent,
    mock_developer_agent,
    mock_qa_agent_success,
    mock_communicator_agent
):
    """Test successful processing of a ticket through the entire pipeline"""
    # Set up orchestrator with mocks
    orchestrator = Orchestrator()
    orchestrator.jira_client = mock_jira_client
    orchestrator.github_service = mock_github_service
    orchestrator.planner_agent = mock_planner_agent
    orchestrator.developer_agent = mock_developer_agent
    orchestrator.qa_agent = mock_qa_agent_success
    orchestrator.communicator_agent = mock_communicator_agent
    
    # Create test ticket
    test_ticket = {
        "ticket_id": "BUG-123",
        "title": "Test Bug",
        "description": "This is a test bug description"
    }
    
    # Mock ticket_status functions
    with patch('orchestrator.orchestrator.initialize_ticket') as mock_init_ticket, \
         patch('orchestrator.orchestrator.update_ticket_status') as mock_update_ticket:
        mock_init_ticket.return_value = None
        mock_update_ticket.return_value = None
        
        # Process ticket
        await orchestrator.process_ticket(test_ticket)
        
        # Check that all agents were called
        mock_planner_agent.process.assert_called_once()
        mock_developer_agent.process.assert_called_once()
        mock_qa_agent_success.process.assert_called_once()
        mock_communicator_agent.process.assert_called_once()
        
        # Check that ticket status was updated
        mock_init_ticket.assert_called_once()
        assert mock_update_ticket.call_count > 0
        
        # Last update should set status to completed
        last_call = mock_update_ticket.call_args_list[-1]
        assert last_call[0][1] == "completed"


@pytest.mark.asyncio
async def test_retry_mechanism(
    mock_jira_client,
    mock_github_service,
    mock_planner_agent,
    mock_developer_agent,
    mock_qa_agent_failure,
    mock_communicator_agent
):
    """Test the retry mechanism for failed QA tests"""
    # Set up orchestrator with mocks
    orchestrator = Orchestrator()
    orchestrator.jira_client = mock_jira_client
    orchestrator.github_service = mock_github_service
    orchestrator.planner_agent = mock_planner_agent
    orchestrator.developer_agent = mock_developer_agent
    orchestrator.qa_agent = mock_qa_agent_failure
    orchestrator.communicator_agent = mock_communicator_agent
    
    # Create a dictionary to track active tickets
    orchestrator.active_tickets = {}
    
    # Mock ticket_status functions
    with patch('orchestrator.orchestrator.initialize_ticket') as mock_init_ticket, \
         patch('orchestrator.orchestrator.update_ticket_status') as mock_update_ticket, \
         patch('orchestrator.orchestrator.MAX_RETRIES', 2):  # Mock max retries to 2 for faster test
         
        mock_init_ticket.return_value = None
        
        # Mock update_ticket_status to update our local active_tickets
        def update_mock(ticket_id, status, details=None):
            if ticket_id not in orchestrator.active_tickets:
                orchestrator.active_tickets[ticket_id] = {"status": "new"}
            orchestrator.active_tickets[ticket_id]["status"] = status
            if details:
                orchestrator.active_tickets[ticket_id].update(details)
        
        mock_update_ticket.side_effect = update_mock
        
        # Create test ticket
        test_ticket = {
            "ticket_id": "BUG-123",
            "title": "Test Bug",
            "description": "This is a test bug description"
        }
        
        # Process ticket
        await orchestrator.process_ticket(test_ticket)
        
        # Check that planner was called once
        mock_planner_agent.process.assert_called_once()
        
        # Developer should be called for each retry attempt plus initial attempt
        assert mock_developer_agent.process.call_count >= 2
        
        # QA should be called for each development attempt
        assert mock_qa_agent_failure.process.call_count >= 2
        
        # Communicator should be called once for escalation
        mock_communicator_agent.process.assert_called_once()
        
        # Check ticket status - should be escalated after max retries
        assert orchestrator.active_tickets["BUG-123"]["status"] == "escalated"


@pytest.mark.asyncio
async def test_fetch_eligible_tickets(mock_jira_client):
    """Test fetching eligible tickets from JIRA"""
    orchestrator = Orchestrator()
    orchestrator.jira_client = mock_jira_client
    
    # Get tickets
    tickets = await orchestrator.fetch_eligible_tickets()
    
    # Check that fetch_bug_tickets was called
    mock_jira_client.fetch_bug_tickets.assert_called_once()
    
    # Check returned tickets
    assert len(tickets) == 1
    assert tickets[0]["ticket_id"] == "BUG-123"


@pytest.mark.asyncio
async def test_acquire_ticket_lock():
    """Test the ticket locking mechanism"""
    orchestrator = Orchestrator()
    
    # Create temporary directory for lock files
    import tempfile
    temp_dir = tempfile.TemporaryDirectory()
    orchestrator.lock_dir = temp_dir.name
    
    try:
        # Test acquiring a lock
        lock_acquired = await orchestrator.acquire_ticket_lock("BUG-123")
        assert lock_acquired == True
        
        # Test trying to acquire same lock again
        lock_acquired_again = await orchestrator.acquire_ticket_lock("BUG-123")
        assert lock_acquired_again == False
        
        # Release the lock
        await orchestrator.release_ticket_lock("BUG-123")
        
        # Should be able to acquire it again
        lock_acquired_after_release = await orchestrator.acquire_ticket_lock("BUG-123")
        assert lock_acquired_after_release == True
    finally:
        # Clean up
        temp_dir.cleanup()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])