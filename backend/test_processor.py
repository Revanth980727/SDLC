
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-processor")

def process_qa_results(ticket_id: str, developer_response: Dict[str, Any], qa_response: Dict[str, Any]) -> bool:
    """Process the QA test results and determine if the fix passed"""
    try:
        # Extract test results
        test_results = qa_response.get("test_results", [])
        passed = qa_response.get("passed", False)
        
        # Log the test result summary
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.get("status") == "pass")
        
        logger.info(f"Ticket {ticket_id} QA results: {passed_tests}/{total_tests} tests passed")
        
        # If any tests failed, log the details
        if not passed:
            for test_result in test_results:
                if test_result.get("status") != "pass":
                    logger.warning(f"Ticket {ticket_id} failed test: {test_result.get('name')}")
                    logger.warning(f"Error message: {test_result.get('error_message')}")
        
        return passed
    
    except Exception as e:
        logger.error(f"Error processing QA results for ticket {ticket_id}: {str(e)}")
        return False

def analyze_test_failures(test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze test failures to provide insights for the Developer agent"""
    failure_categories = {
        "syntax_errors": [],
        "runtime_errors": [],
        "assertion_failures": [],
        "other": []
    }
    
    for result in test_results:
        if result.get("status") == "fail":
            error_msg = result.get("error_message", "")
            
            if "SyntaxError" in error_msg:
                failure_categories["syntax_errors"].append(result)
            elif any(e in error_msg for e in ["TypeError", "NameError", "AttributeError"]):
                failure_categories["runtime_errors"].append(result)
            elif "AssertionError" in error_msg:
                failure_categories["assertion_failures"].append(result)
            else:
                failure_categories["other"].append(result)
    
    # Count failures by category
    summary = {
        "total_failures": sum(len(v) for v in failure_categories.values()),
        "categorized_failures": {k: len(v) for k, v in failure_categories.items()}
    }
    
    # Generate insights
    insights = []
    
    if failure_categories["syntax_errors"]:
        insights.append("Fix syntax errors in the code.")
    
    if failure_categories["runtime_errors"]:
        insights.append("Address runtime errors such as undefined variables or properties.")
    
    if failure_categories["assertion_failures"]:
        insights.append("The logic is not producing the expected results. Review business logic.")
    
    summary["insights"] = insights
    
    return summary
