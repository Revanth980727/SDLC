
import os
import logging
import subprocess
import json
import sys
import time
from typing import Dict, Any, Optional, List
from .agent_base import Agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qa_agent")

class QAAgent(Agent):
    """
    Agent responsible for running tests to validate developer-generated fixes.
    Ensures that fixes pass all tests before proceeding.
    """
    
    def __init__(self):
        """Initialize the QA agent"""
        super().__init__(name="QA Agent")
    
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input from developer agent and run tests to validate the fix
        
        Args:
            input_data: Dictionary with data from developer agent including patch data
            
        Returns:
            Dictionary with test results
        """
        logger.info("QA Agent starting test process")
        
        # Initialize result structure
        result = {
            "passed": False,
            "test_results": [],
            "execution_time": 0,
            "error_message": None,
            "code_changes_detected": False,
            "validation_errors": [],
            "success": False
        }
        
        # Log the developer agent input
        logger.info(f"QA Agent received input with keys: {list(input_data.keys())}")
        
        # Debug input data to better diagnose issues
        debug_dir = "debug_logs"
        os.makedirs(debug_dir, exist_ok=True)
        try:
            with open(f"{debug_dir}/qa_received_input.json", "w") as f:
                json.dump(input_data, f, indent=2)
            logger.info(f"Saved received input to {debug_dir}/qa_received_input.json")
        except Exception as e:
            logger.error(f"Error saving input for debugging: {str(e)}")
        
        # Validate developer input
        if not self._validate_developer_input(input_data, result):
            result["error_message"] = "Invalid input from developer agent"
            logger.error(f"Developer input validation failed: {result['validation_errors']}")
            return result
            
        # Check if developer agent reported success
        if not input_data.get("success", False):
            result["error_message"] = "Developer agent reported failure"
            logger.error("Developer agent reported failure, skipping QA tests")
            return result
            
        # Verify that code changes were actually made
        logger.info("Verifying code changes")
        if not self._verify_code_changes(result):
            result["error_message"] = "No code changes detected"
            logger.error("No code changes detected in the repository")
            return result
            
        # Run tests
        logger.info("Running tests")
        test_command = os.environ.get("TEST_COMMAND", "python -m pytest")
        logger.info(f"Using test command from environment: {test_command}")
        success, test_output = self._run_test_command(test_command)
        
        # Parse and process test results
        if success:
            logger.info("Tests passed successfully")
            result["passed"] = True
            result["test_results"] = self._parse_test_output(test_output)
            result["execution_time"] = self._calculate_execution_time(test_output)
            result["success"] = True
            
            # Add a failure_summary field for consistency even when tests pass
            result["failure_summary"] = ""
        else:
            logger.error("Tests failed")
            result["passed"] = False
            result["error_message"] = "Tests failed"
            result["test_results"] = self._parse_test_output(test_output)
            result["execution_time"] = self._calculate_execution_time(test_output)
            
            # Extract a failure summary from the test output
            result["failure_summary"] = self._extract_failure_summary(test_output)
            
        logger.info(f"QA Agent completed with success={result['success']} and passed={result['passed']}")
        return result
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method for backwards compatibility.
        Delegates to run() method.
        """
        return self.run(input_data)
        
    def _validate_developer_input(self, input_data: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        Validate input from developer agent
        
        Args:
            input_data: Dictionary with data from developer agent
            result: Result dictionary to update with validation errors
            
        Returns:
            Boolean indicating if input is valid
        """
        valid = True
        validation_errors = []
        
        # Log the received input keys to help debugging
        logger.info(f"Validating developer input with keys: {list(input_data.keys())}")
        
        # Check if patched_code exists and is not empty
        if "patched_code" not in input_data:
            validation_errors.append("Missing patched_code in developer output")
            valid = False
            logger.error(f"Missing patched_code in developer output. Keys available: {list(input_data.keys())}")
        elif not input_data["patched_code"]:
            validation_errors.append("Empty patched_code in developer output")
            valid = False
            logger.error("Empty patched_code in developer output")
        else:
            logger.info(f"Found patched_code with {len(input_data['patched_code'])} entries")
            
        # Check confidence score
        if "confidence_score" not in input_data:
            validation_errors.append("Missing confidence_score in developer output")
            valid = False
            logger.error(f"Missing confidence_score in developer output. Keys available: {list(input_data.keys())}")
        elif input_data.get("confidence_score", 0) <= 0:
            validation_errors.append(f"Invalid confidence score: {input_data.get('confidence_score', 0)}")
            valid = False
            logger.error(f"Invalid confidence score: {input_data.get('confidence_score', 0)}")
        else:
            logger.info(f"Found confidence_score: {input_data.get('confidence_score')}")
            
        # Check patch file paths
        if "patched_files" not in input_data:
            validation_errors.append("Missing patched_files in developer output")
            valid = False
            logger.error(f"Missing patched_files in developer output. Keys available: {list(input_data.keys())}")
        elif not input_data.get("patched_files", []):
            validation_errors.append("Empty patched_files list in developer output")
            valid = False
            logger.error("Empty patched_files list in developer output")
        else:
            logger.info(f"Found patched_files: {input_data.get('patched_files')}")
            
        # Add relaxed validation - if we have diffs but not patched_code or patched_files
        if "diffs" in input_data and input_data.get("diffs") and "patched_code" not in input_data:
            logger.warning("Using 'diffs' instead of missing 'patched_code'")
            input_data["patched_code"] = {d["file"]: d["content"] for d in input_data["diffs"] if "file" in d and "content" in d}
            if not "patched_files" in input_data:
                input_data["patched_files"] = [d["file"] for d in input_data["diffs"] if "file" in d]
            logger.info(f"Constructed patched_code and patched_files from diffs: {list(input_data['patched_code'].keys())}")
            
        # Log validation results
        if validation_errors:
            result["validation_errors"] = validation_errors
            logger.warning(f"Developer input validation failed: {validation_errors}")
            try:
                # Log a limited sample of the input for debugging
                sample_input = {k: str(v)[:100] + "..." if isinstance(v, str) and len(str(v)) > 100 else v 
                              for k, v in input_data.items()}
                logger.warning(f"Developer input sample: {json.dumps(sample_input, indent=2)}")
            except Exception as e:
                logger.warning(f"Could not serialize developer input for logging: {str(e)}")
                # Try to log keys at least
                logger.warning(f"Developer input keys: {list(input_data.keys())}")
        else:
            logger.info("Developer input validation passed")
        
        return valid
        
    def _verify_code_changes(self, result: Dict[str, Any]) -> bool:
        """
        Verify that code changes were actually made using git diff
        
        Args:
            result: Result dictionary to update
            
        Returns:
            Boolean indicating if code changes were detected
        """
        try:
            # Run git diff to check for changes
            diff_process = subprocess.run(
                ["git", "diff", "--exit-code"],
                cwd=os.environ.get("REPO_PATH", "/mnt/codebase"),
                capture_output=True,
                text=True
            )
            
            # If git diff exits with code 0, there are no changes
            if diff_process.returncode == 0:
                logger.warning("No code changes detected by git diff")
                result["code_changes_detected"] = False
                return False
                
            # Changes detected
            logger.info("Code changes detected by git diff")
            result["code_changes_detected"] = True
            return True
            
        except Exception as e:
            logger.error(f"Error checking for code changes: {str(e)}")
            result["error_message"] = f"Error checking for code changes: {str(e)}"
            result["code_changes_detected"] = False
            return False
    
    def _run_test_command(self, test_command: str, timeout: int = 300) -> tuple:
        """
        Run tests using the specified command
        
        Args:
            test_command: Command to run tests
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, output)
        """
        try:
            logger.info(f"Running test command: {test_command}")
            
            # Check if pytest is available
            try:
                import pytest
                logger.info(f"Found pytest version: {pytest.__version__}")
            except ImportError:
                logger.warning("Pytest not found, attempting to install...")
                try:
                    subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], check=True)
                    logger.info("Successfully installed pytest")
                except Exception as e:
                    logger.error(f"Failed to install pytest: {str(e)}")
                    return False, f"Failed to install pytest: {str(e)}"
            
            # Handle different test command formats properly
            if "python -m pytest" in test_command:
                # Handle as Python module
                command_parts = ["python", "-m", "pytest"]
                
                # Add any additional arguments
                extra_args = test_command.replace("python -m pytest", "").strip().split()
                if extra_args:
                    command_parts.extend(extra_args)
            elif test_command.startswith("pytest"):
                # Convert pytest to python -m pytest for reliability
                command_parts = ["python", "-m", "pytest"]
                extra_args = test_command.replace("pytest", "").strip().split()
                if extra_args:
                    command_parts.extend(extra_args)
            else:
                # For other commands, use regular splitting
                command_parts = test_command.split()
                
            logger.info(f"Executing test command: {' '.join(command_parts)}")
            
            # Print environment info for debugging
            env = os.environ.copy()
            logger.info(f"Environment variables for test command: PATH={env.get('PATH', '')}, PYTHONPATH={env.get('PYTHONPATH', '')}")
            
            process = subprocess.run(
                command_parts,
                cwd=os.environ.get("REPO_PATH", "/mnt/codebase"),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env  # Pass environment variables
            )
            
            # Check if tests passed
            success = process.returncode == 0
            logger.info(f"Test command exited with code {process.returncode}")
            
            # Log output for debugging
            logger.info(f"Test stdout: {process.stdout}")
            if process.stderr:
                logger.info(f"Test stderr: {process.stderr}")
            
            return success, process.stdout + process.stderr
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Test command timed out after {timeout} seconds")
            return False, f"Timeout: Test execution exceeded {timeout} seconds"
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return False, str(e)
            
    def _parse_test_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse test output into structured format
        
        Args:
            output: Test output to parse
            
        Returns:
            List of test results
        """
        # Simple implementation - in a real system, you would parse the test output
        # into a structured format based on the testing framework used
        return [{"raw_output": output}]
        
    def _calculate_execution_time(self, output: str) -> float:
        """
        Calculate test execution time from output
        
        Args:
            output: Test output
            
        Returns:
            Execution time in seconds
        """
        # Simple implementation - in a real system, you would extract the actual
        # execution time from the test output
        return 1.5  # Mock execution time
        
    def _extract_failure_summary(self, output: str) -> str:
        """
        Extract a concise failure summary from test output
        
        Args:
            output: Test output
            
        Returns:
            Concise failure summary
        """
        # Look for common failure patterns in test output
        failure_lines = []
        
        # Process the output line by line to extract key failure information
        for line in output.split('\n'):
            if "FAILED" in line or "Error:" in line or "Exception:" in line or "No module named" in line:
                failure_lines.append(line.strip())
                
        # If we found specific failure lines, join them
        if failure_lines:
            return "\n".join(failure_lines[:3])  # Limit to first 3 failures for conciseness
            
        # Fallback: Return a generic message with a snippet of the output
        return f"Tests failed. Output: {output[:200]}..." if len(output) > 200 else output