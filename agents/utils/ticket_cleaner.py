
import re
from typing import Dict, Any, Optional, List

class TicketCleaner:
    """
    Utility class to clean ticket text by removing noise such as:
    - Email signatures
    - Disclaimers
    - Repeated headers
    - Greetings
    - Excessive whitespace
    """
    
    # Common patterns to clean
    SIGNATURE_PATTERNS = [
        r"Thanks(?:,| and regards,?|,? regards)?[\s\r\n]+[A-Za-z]+",
        r"Best regards,?[\s\r\n]+[A-Za-z]+",
        r"Regards,?[\s\r\n]+[A-Za-z]+",
        r"--[\s\r\n]+[A-Za-z]+[\s\r\n]+(?:.*?[\s\r\n]+)*?(?:Email|Tel|Phone|Mobile|www\.)",
        r"Sent from my (?:iPhone|Android|mobile device|tablet)",
    ]
    
    GREETING_PATTERNS = [
        r"^(?:Hi|Hello|Hey)(?:,| team| all| everyone| there)?(?:,|\.)?[\s\r\n]+",
        r"^Good (?:morning|afternoon|evening|day)(?:,| team| all| everyone| there)?(?:,|\.)?[\s\r\n]+",
        r"^Dear (?:team|support|all|everyone)(?:,|\.)?[\s\r\n]+"
    ]
    
    DISCLAIMER_PATTERNS = [
        r"DISCLAIMER[\s\r\n]+(?:.*?[\s\r\n]+)*?(?:confidential|intended|recipient)",
        r"This email (?:and any attachments )?(?:is|are) confidential",
        r"This message contains confidential information",
        r"This communication is intended solely for"
    ]
    
    HEADERS_PATTERNS = [
        r"^From:.*?[\r\n]+",
        r"^To:.*?[\r\n]+",
        r"^Date:.*?[\r\n]+",
        r"^Sent:.*?[\r\n]+",
        r"^Subject:.*?[\r\n]+"
    ]
    
    @classmethod
    def clean_ticket(cls, text: str) -> str:
        """
        Clean a ticket description by removing noise elements
        
        Args:
            text: The original ticket description text
            
        Returns:
            Cleaned ticket text
        """
        if not text:
            return ""
            
        # Make a copy to work with
        cleaned_text = text
        
        # Remove signatures
        for pattern in cls.SIGNATURE_PATTERNS:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove greetings
        for pattern in cls.GREETING_PATTERNS:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove disclaimers
        for pattern in cls.DISCLAIMER_PATTERNS:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Remove email headers
        for pattern in cls.HEADERS_PATTERNS:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
        
        # Clean excessive whitespace
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text

class StackTraceExtractor:
    """
    Utility class to extract and highlight stack traces from ticket descriptions
    """
    
    # Common stack trace patterns
    STACK_TRACE_PATTERNS = [
        # Python stack traces
        r"Traceback \(most recent call last\):\s+(?:.*\n)+?(?:.*Error:.*(?:\n\s+.*)*)",
        
        # Java stack traces
        r"(?:[a-zA-Z_$][a-zA-Z\d_$]*\.)*[a-zA-Z_$][a-zA-Z\d_$]*(?:Exception|Error).*?(?:\n\s+at .*)+",
        
        # JavaScript stack traces
        r"(?:Error|Exception|TypeError|ReferenceError).*\n(?:\s+at .*\n)+",
        
        # Generic stack trace patterns (line numbers, file paths)
        r"(?:in|at) .*?:[0-9]+(?:\n|$)"
    ]
    
    @classmethod
    def extract_stack_traces(cls, text: str) -> List[str]:
        """
        Extract stack traces from text
        
        Args:
            text: The ticket description text
            
        Returns:
            List of extracted stack traces
        """
        stack_traces = []
        
        for pattern in cls.STACK_TRACE_PATTERNS:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                stack_traces.append(match.group(0))
        
        return stack_traces
    
    @classmethod
    def highlight_stack_traces(cls, text: str) -> str:
        """
        Highlight stack traces in the text by wrapping them in markers
        
        Args:
            text: The ticket description text
            
        Returns:
            Text with highlighted stack traces
        """
        result = text
        stack_traces = cls.extract_stack_traces(text)
        
        for trace in stack_traces:
            # Replace the trace with a highlighted version
            highlighted = f"\n[STACK TRACE START]\n{trace}\n[STACK TRACE END]\n"
            result = result.replace(trace, highlighted)
        
        return result

class RepositoryValidator:
    """
    Utility class to validate file paths against actual repository structure
    """
    
    def __init__(self, repo_files: List[str] = None):
        """
        Initialize with a list of valid repository files
        
        Args:
            repo_files: List of valid file paths in the repository
        """
        self.repo_files = repo_files or []
        
    def load_repo_structure(self, repo_path: str = None, file_list: List[str] = None):
        """
        Load repository file structure either from a path or a provided list
        
        Args:
            repo_path: Path to the repository root
            file_list: List of files in the repository
        """
        if file_list:
            self.repo_files = file_list
        elif repo_path:
            import os
            import glob
            
            # Walk through the repository and collect all file paths
            self.repo_files = []
            for root, _, files in os.walk(repo_path):
                for file in files:
                    # Skip hidden files and directories
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    # Convert to relative path
                    rel_path = os.path.relpath(file_path, repo_path)
                    self.repo_files.append(rel_path)
        
    def validate_file(self, file_path: str) -> bool:
        """
        Check if a file exists in the repository
        
        Args:
            file_path: File path to validate
            
        Returns:
            True if the file exists in the repository, False otherwise
        """
        # Normalize path separators
        normalized_path = file_path.replace('\\', '/')
        
        # Direct match
        if normalized_path in self.repo_files:
            return True
            
        # Try with/without leading slash
        if normalized_path.startswith('/'):
            if normalized_path[1:] in self.repo_files:
                return True
        else:
            if f"/{normalized_path}" in self.repo_files:
                return True
                
        # Try case insensitive match
        lower_path = normalized_path.lower()
        for repo_file in self.repo_files:
            if repo_file.lower() == lower_path:
                return True
                
        return False
        
    def validate_files(self, file_paths: List[str]) -> Dict[str, bool]:
        """
        Validate multiple file paths
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dictionary mapping file paths to validation results
        """
        results = {}
        for file_path in file_paths:
            results[file_path] = self.validate_file(file_path)
        return results
