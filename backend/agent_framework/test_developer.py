import logging
from agent_base import Agent, AgentStatus
from developer_agent import DeveloperAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_developer_agent():
    # Initialize the developer agent
    developer = DeveloperAgent()
    
    # Test input (based on output from PlannerAgent)
    test_input = {
        "ticket_id": "BUG-123",
        "summary": "Fix login error in AuthService.tsx where it's unable to read property 'data' of undefined",
        "affected_files": [
            "src/components/auth/AuthService.tsx",
            "src/utils/validation.ts",
            "src/api/loginApi.ts"
        ],
        "affected_modules": [
            "AuthService", 
            "ValidationHelper", 
            "LoginComponent"
        ],
        "affected_functions": [
            "handleLogin",
            "validateCredentials",
            "submitLoginRequest"
        ],
        "errors_identified": [
            "Cannot read property 'data' of undefined"
        ]
    }
    
    # Run developer agent
    try:
        result = developer.process(test_input)
        logger.info(f"\nDeveloper status: {developer.status}")
        logger.info(f"Processing result: {result}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_developer_agent()