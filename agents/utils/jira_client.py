
import os
import json
import requests
import time
from typing import Dict, Any, List, Optional, Union
from .logger import Logger

class JiraClient:
    """Client for interacting with JIRA REST API"""
    
    def __init__(self):
        """Initialize JIRA client with environment variables"""
        self.logger = Logger("jira_client")
        
        # Get credentials from environment variables
        self.jira_url = os.environ.get("JIRA_URL")
        self.jira_user = os.environ.get("JIRA_USERNAME") or os.environ.get("JIRA_USER")
        self.jira_token = os.environ.get("JIRA_API_TOKEN") or os.environ.get("JIRA_TOKEN")
        self.project_key = os.environ.get("JIRA_PROJECT_KEY", "")
        
        self.logger.info(f"Initializing JIRA client with URL: {self.jira_url}, User: {self.jira_user}, Project: {self.project_key}")
        
        if not all([self.jira_url, self.jira_user, self.jira_token]):
            self.logger.error(f"Missing required JIRA environment variables - URL: {bool(self.jira_url)}, User: {bool(self.jira_user)}, Token: {bool(self.jira_token)}")
            raise EnvironmentError(
                "Missing JIRA credentials. Please set JIRA_URL, JIRA_USER/JIRA_USERNAME, and JIRA_TOKEN/JIRA_API_TOKEN environment variables."
            )
            
        # Set up auth and headers
        self.auth = (self.jira_user, self.jira_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.logger.info(f"JIRA client initialized for {self.jira_url}")
        
    def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch a JIRA ticket by ID
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            
        Returns:
            Dictionary containing ticket data
        """
        url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}"
        
        self.logger.info(f"Fetching ticket {ticket_id}")
        start_time = time.time()
        response = requests.get(
            url, 
            auth=self.auth, 
            headers=self.headers
        )
        end_time = time.time()
        
        self.logger.info(f"GET {url} - Status: {response.status_code} - Time: {end_time - start_time:.2f}s")
        
        if response.status_code != 200:
            self.logger.error(f"Failed to fetch ticket {ticket_id}: {response.status_code}, {response.text}")
            response.raise_for_status()
            
        # Debug full response
        self.logger.debug(f"Full response for ticket {ticket_id}: {response.json()}")
        
        return response.json()
    
    def get_open_bugs(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch open bug tickets from JIRA
        
        Args:
            max_results: Maximum number of tickets to return
            
        Returns:
            List of ticket dictionaries
        """
        url = f"{self.jira_url}/rest/api/3/search"
        
        # Build JQL query for open bugs
        project_clause = f"project = {self.project_key}" if self.project_key else ""
        jql = f"issuetype = Bug AND (status = \"To Do\" OR status = Open)"
        if project_clause:
            jql += f" AND {project_clause}"
        
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,description,status,issuetype,created,updated,assignee,reporter,priority"
        }
        
        self.logger.info(f"Fetching open bugs with JQL: {jql}")
        self.logger.debug(f"GET {url} with params: {params}")
        
        start_time = time.time()
        response = requests.get(
            url,
            params=params,
            auth=self.auth,
            headers=self.headers
        )
        end_time = time.time()
        
        self.logger.info(f"GET {url} - Status: {response.status_code} - Time: {end_time - start_time:.2f}s")
        
        if response.status_code != 200:
            self.logger.error(f"Failed to fetch open bugs: {response.status_code}, {response.text}")
            response.raise_for_status()
        
        data = response.json()
        tickets = []
        
        # Debug full response
        self.logger.debug(f"JIRA API response: {json.dumps(data)[:500]}...")
        
        issues = data.get("issues", [])
        if not issues:
            self.logger.info("No open bug tickets found")
            return []
            
        for issue in issues:
            ticket_id = issue["key"]
            fields = issue["fields"]
            
            # Safely extract fields
            assignee = "Unassigned"
            if fields.get("assignee"):
                assignee = fields["assignee"].get("displayName", "Unassigned")
                
            # Extract description text from Atlassian Document Format if available
            description = fields.get("description", "")
            if isinstance(description, dict) and "content" in description:
                description_text = self._extract_text_from_adf(description)
                self.logger.debug(f"Extracted description text from ADF: {description_text[:100]}...")
            else:
                description_text = str(description)
                
            ticket = {
                "ticket_id": ticket_id,
                "title": fields.get("summary", "No title"),
                "description": description_text,
                "status": fields.get("status", {}).get("name", "Unknown") if fields.get("status") else "Unknown",
                "created": fields.get("created", ""),
                "updated": fields.get("updated", ""),
                "assignee": assignee,
                "reporter": fields.get("reporter", {}).get("displayName", "Unknown") if fields.get("reporter") else "Unknown",
                "priority": fields.get("priority", {}).get("name", "Normal") if fields.get("priority") else "Normal"
            }
            
            self.logger.debug(f"Processed ticket {ticket_id}: {json.dumps(ticket)[:500]}...")
            tickets.append(ticket)
            
        self.logger.info(f"Found {len(tickets)} open bug tickets to process")
        return tickets
    
    def _extract_text_from_adf(self, adf_doc: Dict[str, Any]) -> str:
        """
        Extract plain text from Atlassian Document Format (ADF)
        
        Args:
            adf_doc: ADF document object
            
        Returns:
            Plain text representation of the document
        """
        text_parts = []
        
        def _process_content(content):
            if not content:
                return
                
            for item in content:
                if item.get("type") == "text" and "text" in item:
                    text_parts.append(item["text"])
                    
                if "content" in item:
                    _process_content(item["content"])
        
        _process_content(adf_doc.get("content", []))
        return " ".join(text_parts)
    
    def add_comment(self, ticket_id: str, comment: str) -> bool:
        """
        Add a comment to a JIRA ticket
        
        Args:
            ticket_id: The JIRA ticket ID
            comment: Comment text (can contain JIRA markdown)
            
        Returns:
            Success status (True/False)
        """
        url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}/comment"
        
        # Format for JIRA API
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }
        
        self.logger.info(f"Adding comment to ticket {ticket_id}")
        self.logger.debug(f"POST {url} with payload: {json.dumps(payload)}")
        
        try:
            start_time = time.time()
            response = requests.post(
                url,
                json=payload,
                auth=self.auth,
                headers=self.headers
            )
            end_time = time.time()
            
            self.logger.info(f"POST {url} - Status: {response.status_code} - Time: {end_time - start_time:.2f}s")
            
            if response.status_code not in (201, 200):
                self.logger.error(f"Failed to add comment to {ticket_id}: {response.status_code}, {response.text}")
                return False
                
            self.logger.info(f"Successfully added comment to {ticket_id}")
            return True
        except Exception as e:
            self.logger.error(f"Exception adding comment to {ticket_id}: {str(e)}")
            return False
    
    def update_ticket(self, ticket_id: str, status: str, comment: Optional[str] = None) -> bool:
        """
        Update a JIRA ticket status and optionally add a comment
        
        Args:
            ticket_id: The JIRA ticket ID
            status: The new status to set
            comment: Optional comment to add
            
        Returns:
            Success status (True/False)
        """
        self.logger.info(f"Updating ticket {ticket_id} status to '{status}' with comment: {comment}")
        
        # First add comment if provided
        if comment:
            comment_result = self.add_comment(ticket_id, comment)
            if not comment_result:
                self.logger.warning(f"Failed to add comment to {ticket_id}")
                # Continue anyway to try status update

        # Only proceed with status update if status is provided
        if status:
            # Get the list of available transitions
            transitions_url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}/transitions"
            
            try:
                self.logger.info(f"Fetching available transitions for {ticket_id}")
                start_time = time.time()
                transitions_response = requests.get(
                    transitions_url,
                    auth=self.auth,
                    headers=self.headers
                )
                end_time = time.time()
                
                self.logger.info(f"GET {transitions_url} - Status: {transitions_response.status_code} - Time: {end_time - start_time:.2f}s")
                
                if transitions_response.status_code != 200:
                    self.logger.error(f"Failed to get transitions for {ticket_id}: {transitions_response.status_code}")
                    return False
                    
                transitions = transitions_response.json().get("transitions", [])
                if not transitions:
                    self.logger.warning(f"No transitions available for ticket {ticket_id}")
                    return False
                    
                # Debug available transitions
                self.logger.debug(f"Available transitions for {ticket_id}: {json.dumps(transitions)}")
                
                transition_id = None
                
                # Find the transition that matches our target status
                for transition in transitions:
                    self.logger.debug(f"Checking transition: {transition['to']['name']} (ID: {transition['id']}) against target '{status}'")
                    if transition["to"]["name"].lower() == status.lower():
                        transition_id = transition["id"]
                        break
                        
                if not transition_id:
                    self.logger.error(f"No transition found for status '{status}' on ticket {ticket_id}")
                    return False
                    
                # Perform the transition
                transition_payload = {
                    "transition": {
                        "id": transition_id
                    }
                }
                
                self.logger.info(f"Updating ticket {ticket_id} to status '{status}' using transition ID {transition_id}")
                
                start_time = time.time()
                transition_result = requests.post(
                    transitions_url,
                    json=transition_payload,
                    auth=self.auth,
                    headers=self.headers
                )
                end_time = time.time()
                
                self.logger.info(f"POST {transitions_url} - Status: {transition_result.status_code} - Time: {end_time - start_time:.2f}s")
                
                if transition_result.status_code not in (204, 200):
                    self.logger.error(f"Failed to update status for {ticket_id}: {transition_result.status_code}, {transition_result.text}")
                    return False
                
                self.logger.info(f"Successfully updated ticket {ticket_id} status to '{status}'")
                return True
            except Exception as e:
                self.logger.error(f"Exception updating ticket {ticket_id}: {str(e)}")
                return False
        
        # If we only had a comment and no status update, return comment result
        return True if not status else False

    async def fetch_bug_tickets(self) -> List[Dict[str, Any]]:
        """
        Asynchronous wrapper for get_open_bugs
        
        Returns:
            List of ticket dictionaries
        """
        self.logger.info("Fetching bug tickets from JIRA")
        try:
            # Call the synchronous method - in real async code, this would be awaitable
            tickets = self.get_open_bugs()
            self.logger.info(f"Found {len(tickets)} bug tickets to process")
            return tickets
        except Exception as e:
            self.logger.error(f"Error fetching bug tickets: {str(e)}")
            return []