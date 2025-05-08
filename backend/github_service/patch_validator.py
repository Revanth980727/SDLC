
import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

class PatchValidator:
    """Validator for LLM-generated code patches"""
    
    def __init__(self, github_client=None):
        """Initialize with optional GitHub client"""
        self.logger = logging.getLogger("patch-validator")
        self.github_client = github_client
    
    def set_github_client(self, github_client):
        """Set the GitHub client instance"""
        self.github_client = github_client
    
    def validate_patch(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a code patch
        
        Args:
            patch: Patch dictionary with file_path and diff
            
        Returns:
            Validation result with details
        """
        if not patch:
            return self._failed_result("Empty patch")
        
        if "file_path" not in patch or "diff" not in patch:
            return self._failed_result("Patch missing required fields")
        
        file_path = patch["file_path"]
        diff = patch["diff"]
        
        # Track validation metrics
        metrics = {
            "total_checks": 3,  # File exists, diff syntax, placeholder detection
            "passed_checks": 0,
            "failures": []
        }
        
        # Check 1: File path exists in repository
        if not self._is_valid_file_path(file_path):
            metrics["failures"].append("file_path_invalid")
            self.logger.warning(f"Invalid file path: {file_path}")
        else:
            metrics["passed_checks"] += 1
        
        # Check 2: Diff has valid syntax
        if not self._is_valid_diff_syntax(diff):
            metrics["failures"].append("diff_syntax_invalid")
            self.logger.warning(f"Invalid diff syntax in {file_path}")
        else:
            metrics["passed_checks"] += 1
            
        # Check 3: No placeholder paths or TODOs in patch
        placeholders = self._check_for_placeholders(file_path, diff)
        if placeholders:
            metrics["failures"].append("contains_placeholders")
            self.logger.warning(f"Placeholders found in {file_path}: {placeholders}")
        else:
            metrics["passed_checks"] += 1
        
        # Calculate validation score
        validation_score = (metrics["passed_checks"] / metrics["total_checks"]) * 100
        
        # Create result object
        if metrics["failures"]:
            result = {
                "valid": False,
                "confidence_penalty": 30 if len(metrics["failures"]) >= 2 else 20,
                "rejection_reason": ", ".join(metrics["failures"]),
                "validation_score": validation_score,
                "validation_metrics": {
                    "total_checks": metrics["total_checks"],
                    "passed_checks": metrics["passed_checks"],
                    "failed_checks": len(metrics["failures"]),
                    "failures": metrics["failures"]
                }
            }
        else:
            result = {
                "valid": True,
                "confidence_boost": 10,  # Boost confidence for fully valid patches
                "validation_score": 100.0,
                "validation_metrics": {
                    "total_checks": metrics["total_checks"],
                    "passed_checks": metrics["passed_checks"],
                    "failed_checks": 0,
                    "failures": []
                }
            }
        
        return result
    
    def _is_valid_file_path(self, file_path: str) -> bool:
        """
        Check if a file path exists in the repository
        
        Args:
            file_path: Path to check
            
        Returns:
            True if valid, False otherwise
        """
        # If no GitHub client is set, do basic path validation
        if not self.github_client:
            # Basic checks - no absolute paths, no suspicious patterns
            if file_path.startswith("/") or file_path.startswith("\\"):
                return False
            if "example" in file_path.lower() or "sample" in file_path.lower():
                return False
            return True
        
        # If GitHub client is available, check if file exists in repo
        try:
            # Use GitHub client to check file existence
            exists = self.github_client.check_file_exists(file_path)
            return exists
        except Exception as e:
            self.logger.error(f"Error checking file path {file_path}: {str(e)}")
            return False
    
    def _is_valid_diff_syntax(self, diff: str) -> bool:
        """
        Check if a diff has valid syntax
        
        Args:
            diff: Diff string to check
            
        Returns:
            True if valid, False otherwise
        """
        if not diff or not isinstance(diff, str):
            return False
        
        # Check for common diff formats (unified diff)
        if "@@ " in diff and " @@" in diff:
            # Contains diff headers
            return True
            
        # Check for simple add/remove lines format
        has_add = bool(re.search(r'^\+(?!\+\+)', diff, re.MULTILINE))
        has_remove = bool(re.search(r'^-(?!--)', diff, re.MULTILINE))
        has_context = bool(re.search(r'^ [^ ]', diff, re.MULTILINE))
        
        # Valid diff should have add, remove, or both with context
        return (has_add or has_remove) and has_context
    
    def _check_for_placeholders(self, file_path: str, diff: str) -> List[str]:
        """
        Check for placeholder text in file path or diff
        
        Args:
            file_path: File path to check
            diff: Diff content to check
            
        Returns:
            List of placeholder patterns found
        """
        placeholders = []
        
        # Check file path for placeholders
        path_patterns = [
            r'/path/to/',
            r'example\.py',
            r'your_',
            r'my_',
            r'placeholder',
            r'sample',
            r'/tmp/',
            r'foo\.py',
            r'bar\.py'
        ]
        
        for pattern in path_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                placeholders.append(f"path_placeholder:{pattern}")
        
        # Check diff for placeholders
        diff_patterns = [
            r'# TODO',
            r'# FIXME',
            r'# NOTE',
            r'your_function',
            r'your_variable',
            r'your_class',
            r'insert your',
            r'replace this',
            r'xyz\.py',
            r'example\.com'
        ]
        
        for pattern in diff_patterns:
            if re.search(pattern, diff, re.IGNORECASE):
                placeholders.append(f"diff_placeholder:{pattern}")
        
        return placeholders
    
    def _failed_result(self, reason: str) -> Dict[str, Any]:
        """
        Create a failed validation result
        
        Args:
            reason: Reason for failure
            
        Returns:
            Validation result dictionary
        """
        return {
            "valid": False,
            "confidence_penalty": 50,
            "rejection_reason": reason,
            "validation_score": 0.0,
            "validation_metrics": {
                "total_checks": 3,
                "passed_checks": 0,
                "failed_checks": 3,
                "failures": [reason]
            }
        }

    def validate_patches(self, patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate multiple patches and return aggregated results
        
        Args:
            patches: List of patch dictionaries with file_path and diff
            
        Returns:
            Validation result with details
        """
        if not patches:
            return self._failed_result("No patches provided")
        
        total_patches = len(patches)
        valid_patches = 0
        rejections = {}
        all_metrics = []
        
        for patch in patches:
            result = self.validate_patch(patch)
            all_metrics.append(result["validation_metrics"])
            
            if result["valid"]:
                valid_patches += 1
            else:
                rejection_reason = result["rejection_reason"]
                rejections[rejection_reason] = rejections.get(rejection_reason, 0) + 1
        
        # Calculate aggregate validation score
        avg_score = sum(m["passed_checks"] for m in all_metrics) / sum(m["total_checks"] for m in all_metrics) * 100
        
        validation_result = {
            "valid": valid_patches == total_patches,
            "validation_score": avg_score,
            "validation_metrics": {
                "total_patches": total_patches,
                "valid_patches": valid_patches,
                "rejected_patches": total_patches - valid_patches,
                "rejection_reasons": rejections
            }
        }
        
        # Add confidence adjustment
        if validation_result["valid"]:
            validation_result["confidence_boost"] = 10
        else:
            validation_result["confidence_penalty"] = 20 + (10 * (total_patches - valid_patches))
            
        return validation_result