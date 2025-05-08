
import os
import time
import openai
from typing import Dict, Any, Optional
from .logger import Logger

class OpenAIClient:
    """
    Client for interacting with OpenAI API.
    Handles authentication, model selection, and error handling.
    """
    
    def __init__(self):
        """Initialize the OpenAI client with API key from environment"""
        self.logger = Logger("openai_client")
        
        # Get API key from environment
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            self.logger.error("Missing OpenAI API key")
            raise EnvironmentError("Missing OPENAI_API_KEY environment variable")
            
        # Get model from environment or use default
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        
        # Initialize OpenAI client
        openai.api_key = self.api_key
        
    def generate_completion(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Send a prompt to OpenAI API and get completion
        
        Args:
            prompt: The prompt to send to the API
            max_retries: Maximum number of retries for API errors
            
        Returns:
            Completion text or None if all retries fail
        """
        self.logger.info(f"Sending prompt to OpenAI API using model {self.model}")
        
        attempt = 0
        while attempt < max_retries:
            try:
                self.logger.info(f"API request attempt {attempt + 1}/{max_retries}")
                
                # Create chat completion
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert software developer fixing bugs."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Use low temperature for deterministic outputs
                    max_tokens=4000
                )
                
                # Extract and return the completion text
                completion = response.choices[0].message.content
                self.logger.info("Successfully received completion from OpenAI API")
                return completion
                
            except openai.RateLimitError:
                attempt += 1
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.warning(f"Rate limit hit. Retrying in {wait_time} seconds.")
                time.sleep(wait_time)
                
            except openai.APIError as e:
                attempt += 1
                self.logger.error(f"API error: {str(e)}. Attempt {attempt}/{max_retries}")
                if attempt >= max_retries:
                    self.logger.error("Maximum retries reached. Giving up.")
                    return None
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return None
                
        return None
