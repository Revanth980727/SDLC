
import os
import subprocess
import json
import time
from typing import Dict, Any, Optional, List
from .utils.logger import Logger

class QAAgent:
    """
    Agent responsible for running tests against the codebase to verify
    that the bug fix works and doesn't break existing functionality.
    """
    
    def __init__(self):
        """Initialize the QA agent"""
        self.logger = Logger("qa_agent")
        
        # Get repo path from environment
        self.repo_path = os.environ.get("REPO_PATH", "/mnt/codebase")
        
        # Get test command from environment or use default
        self.test_command = os.environ.get("TEST_COMMAND", "pytest")
        
    def run(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run tests on the codebase
        
        Args:
            test_config: Dictionary with test configuration:
                {
                    "ticket_id": "PROJ-123",
                    "test_command": "optional command to override default",
                    "timeout": 120,  # optional timeout in seconds
                    "specific_tests": ["optional", "list", "of", "test", "files"]
                }
                
        Returns:
            Dictionary with test results:
            {
                "passed": true/false,
                "execution_time": 10.5,
                "output": "test output",
                "error_message": "error message if failed",
                "test_coverage": 85.5  # if available
            }
        """
        ticket_id = test_config.get("ticket_id", "unknown")
        self.logger.start_task(f"Running tests for ticket {ticket_id}")
        
        # Override default test command if provided
        test_command = test_config.get("test_command", self.test_command)
        timeout = test_config.get("timeout", 120)
        specific_tests = test_config.get("specific_tests", None)
        
        try:
            # Prepare command
            command = self._prepare_test_command(test_command, specific_tests)
            
            # Run tests
            self.logger.info(f"Running test command: {' '.join(command)}")
            start_time = time.time()
            
            result = subprocess.run(
                command,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # Check if tests passed
            passed = result.returncode == 0
            
            # Get test output
            output = result.stdout
            error_output = result.stderr
            
            if passed:
                self.logger.info(f"Tests passed in {execution_time:.2f} seconds")
            else:
                self.logger.warning(f"Tests failed in {execution_time:.2f} seconds")
                self.logger.warning(f"Error output: {error_output}")
                
            # Save test results to log file
            log_file_path = f"logs/test_results_{ticket_id}.log"
            with open(log_file_path, "w") as f:
                f.write(f"Test Command: {' '.join(command)}\n")
                f.write(f"Return Code: {result.returncode}\n")
                f.write(f"Execution Time: {execution_time:.2f} seconds\n")
                f.write("\n--- STDOUT ---\n")
                f.write(output)
                f.write("\n--- STDERR ---\n")
                f.write(error_output)
                
            # Try to extract test coverage if available
            coverage = self._extract_coverage(output)
            
            # Extract error message for failing tests
            error_message = self._extract_error_message(output, error_output) if not passed else ""
            
            # Create result object
            test_result = {
                "passed": passed,
                "execution_time": execution_time,
                "output": output[:1000] + ("..." if len(output) > 1000 else ""),  # Truncate long output
                "error_message": error_message,
                "test_command": " ".join(command),
                "ticket_id": ticket_id
            }
            
            if coverage:
                test_result["test_coverage"] = coverage
                
            self.logger.end_task(f"Testing for ticket {ticket_id}", success=passed)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Tests timed out after {timeout} seconds")
            self.logger.end_task(f"Testing for ticket {ticket_id}", success=False)
            
            return {
                "passed": False,
                "execution_time": timeout,
                "output": "Tests timed out",
                "error_message": f"Tests timed out after {timeout} seconds",
                "ticket_id": ticket_id
            }
            
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            self.logger.end_task(f"Testing for ticket {ticket_id}", success=False)
            
            return {
                "passed": False,
                "execution_time": 0,
                "output": "",
                "error_message": str(e),
                "ticket_id": ticket_id
            }
            
    def _prepare_test_command(self, test_command: str, specific_tests: Optional[List[str]]) -> List[str]:
        """
        Prepare the command to run the tests
        
        Args:
            test_command: Base test command (e.g., "pytest", "npm test")
            specific_tests: Optional list of specific test files or patterns
            
        Returns:
            List of command parts to pass to subprocess.run
        """
        # Split command into parts
        command_parts = test_command.split()
        
        # Handle common test commands
        if test_command.startswith("pytest"):
            command_parts = ["python", "-m", "pytest"]
            
            # Add common pytest flags
            command_parts.extend(["-v", "--no-header"])
            
            # Add specific tests if provided
            if specific_tests:
                command_parts.extend(specific_tests)
                
        elif test_command.startswith("npm test"):
            command_parts = ["npm", "test"]
            
            # Add specific tests if provided
            if specific_tests:
                command_parts.append("--")
                command_parts.extend(specific_tests)
                
        elif test_command.startswith("python -m unittest"):
            command_parts = ["python", "-m", "unittest"]
            
            # Add specific tests if provided
            if specific_tests:
                command_parts.extend(specific_tests)
                
        elif test_command.startswith("yarn test"):
            command_parts = ["yarn", "test"]
            
            # Add specific tests if provided
            if specific_tests:
                command_parts.extend(specific_tests)
                
        else:
            # For other commands, just use as is and append specific tests
            if specific_tests:
                command_parts.extend(specific_tests)
                
        return command_parts
        
    def _extract_coverage(self, output: str) -> Optional[float]:
        """
        Extract test coverage percentage from output if available
        
        Args:
            output: Test command output
            
        Returns:
            Coverage percentage as float or None if not found
        """
        # Try to find coverage in pytest-cov output
        coverage_lines = [line for line in output.split('\n') if "TOTAL" in line and "%" in line]
        
        if coverage_lines:
            try:
                # Extract percentage from line like "TOTAL                  123     12    90%"
                parts = coverage_lines[0].split()
                for part in parts:
                    if "%" in part:
                        return float(part.strip("%"))
            except Exception:
                pass
                
        # Try to find coverage in Jest output
        if "All files" in output and "% Stmts" in output:
            try:
                # Find the line with "All files"
                lines = output.split('\n')
                for i, line in enumerate(lines):
                    if "All files" in line:
                        # Extract percentage from this line
                        parts = line.split()
                        for part in parts:
                            if "%" in part:
                                return float(part.strip("%"))
            except Exception:
                pass
                
        return None
        
    def _extract_error_message(self, output: str, error_output: str) -> str:
        """
        Extract a meaningful error message from test output
        
        Args:
            output: Standard output from test command
            error_output: Standard error from test command
            
        Returns:
            Extracted error message
        """
        # First check error_output
        if error_output:
            # Find first exception or error
            lines = error_output.split('\n')
            for i, line in enumerate(lines):
                if "error" in line.lower() or "exception" in line.lower():
                    # Return this line and a few more for context
                    return "\n".join(lines[i:i+5])
                    
        # Check main output
        if output:
            # Find test failure in pytest output
            if "FAILURES" in output:
                # Find the first failure
                parts = output.split("FAILURES")
                if len(parts) > 1:
                    failure_section = parts[1]
                    lines = failure_section.split('\n')
                    # Return first 10 lines of failure section
                    return "\n".join(lines[:10])
            
            # Look for "FAIL" lines in any test output
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if "FAIL" in line:
                    # Return this line and a few more for context
                    return "\n".join(lines[i:i+5])
                    
        # If nothing specific found, return generic message
        return "Tests failed but no specific error was identified"
