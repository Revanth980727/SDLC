import logging
import os
from typing import List, Dict, Any, Optional
import httpx
import json
import asyncio
from datetime import datetime

from . import config

# Set up logging
logger = logging.getLogger("jira-service.client")

class JiraClient:
    """Client for interacting with JIRA API"""
    
    def __init__(self):
        """Initialize JIRA client with credentials from config"""
        self.jira_url = config.JIRA_URL
        self.jira_user = config.JIRA_USERNAME
        self.jira_token = config.JIRA_API_TOKEN
        self.auth = (self.jira_user, self.jira_token)
        self.project_key = config.JIRA_PROJECT_KEY
        
        logger.info(f"Initialized JIRA client for project {self.project_key}")
    
    async def fetch_bug_tickets(self) -> List[Dict[str, Any]]:
        """
        Fetch bug tickets from JIRA that are in To Do, Open, or In Progress status
        
        Returns:
            List of ticket dictionaries with fields mapped to standard format
        """
        try:
            logger.info("Fetching bug tickets from JIRA")
            
            # Build JQL query to find bug tickets including In Progress status
            jql = f"issuetype = Bug AND (status = \"To Do\" OR status = Open OR status = \"In Progress\") AND project = {self.project_key}"
            
            # Fields to retrieve
            fields = "summary,description,status,issuetype,created,updated,assignee,reporter,priority"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.jira_url}/rest/api/3/search",
                    params={"jql": jql, "fields": fields},
                    auth=self.auth
                )
                
                # Log the HTTP request for debugging
                logger.info(f"HTTP Request: {response.request.method} {response.request.url} \"{response.http_version} {response.status_code} {response.reason_phrase}\"")
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch bug tickets: {response.status_code} - {response.text}")
                    return []
                
                data = response.json()
                issues = data.get("issues", [])
                
                if not issues:
                    logger.info("No issues found in JIRA response")
                    return []
                
                logger.info(f"Found {len(issues)} bug tickets to process")
                
                # Map JIRA fields to standard ticket format
                tickets = []
                for issue in issues:
                    # Handle description field which might be complex JSON or plain text
                    description = issue["fields"].get("description", "")
                    desc_text = ""
                    
                    # Enhanced error handling for description field
                    try:
                        if description is None:
                            desc_text = ""
                        elif isinstance(description, dict):
                            # Extract text from Atlassian Document Format
                            desc_text = self._extract_text_from_adf(description)
                            # If we couldn't extract text, provide a fallback message
                            if not desc_text.strip():
                                desc_text = "No readable description available"
                        else:
                            desc_text = str(description)
                    except Exception as e:
                        logger.error(f"Error processing description for {issue['key']}: {str(e)}")
                        desc_text = "Error processing description"
                    
                    # Safely extract fields with null checks
                    status_name = "Unknown"
                    if issue["fields"].get("status") and isinstance(issue["fields"]["status"], dict):
                        status_name = issue["fields"]["status"].get("name", "Unknown")
                        
                    reporter_name = "Unknown"
                    if issue["fields"].get("reporter") and isinstance(issue["fields"]["reporter"], dict):
                        reporter_name = issue["fields"]["reporter"].get("displayName", "Unknown")
                        
                    assignee_name = "Unassigned"
                    if issue["fields"].get("assignee") and isinstance(issue["fields"]["assignee"], dict):
                        assignee_name = issue["fields"]["assignee"].get("displayName", "Unassigned")
                        
                    priority_name = "Medium"
                    if issue["fields"].get("priority") and isinstance(issue["fields"]["priority"], dict):
                        priority_name = issue["fields"]["priority"].get("name", "Medium")
                    
                    ticket = {
                        "ticket_id": issue["key"],
                        "title": issue["fields"].get("summary", "No title"),
                        "description": desc_text,
                        "status": status_name,
                        "created": issue["fields"].get("created", ""),
                        "updated": issue["fields"].get("updated", ""),
                        "reporter": reporter_name,
                        "assignee": assignee_name,
                        "priority": priority_name
                    }
                    tickets.append(ticket)
                
                return tickets
                
        except Exception as e:
            logger.error(f"Error fetching bug tickets: {e}")
            return []
    
    def _extract_text_from_adf(self, doc: Dict[str, Any]) -> str:
        """
        Extract plain text from Atlassian Document Format (ADF)
        
        Args:
            doc: The ADF document as a dictionary
            
        Returns:
            Extracted plain text
        """
        if not doc or not isinstance(doc, dict):
            return ""
            
        text_parts = []
        
        # Process content array
        content = doc.get("content", [])
        if content is None:  # Additional null check
            return ""
            
        for item in content:
            if not item or not isinstance(item, dict):
                continue
                
            # Handle paragraph
            if item.get("type") == "paragraph":
                paragraph_text = self._process_content_item(item)
                if paragraph_text:
                    text_parts.append(paragraph_text)
            # Handle other types like headings, lists, etc.
            elif item.get("text"):
                text_parts.append(item["text"])
                
        return "\n".join(text_parts)
    
    def _process_content_item(self, item: Dict[str, Any]) -> str:
        """
        Process a content item from ADF
        
        Args:
            item: The content item
            
        Returns:
            Extracted text from the item
        """
        if not item or not isinstance(item, dict):
            return ""
            
        text_parts = []
        
        # Process content array
        content = item.get("content", [])
        if content is None:  # Additional null check
            return ""
            
        for subitem in content:
            if not subitem or not isinstance(subitem, dict):
                continue
                
            if subitem.get("text"):
                text_parts.append(subitem["text"])
            elif subitem.get("content") and isinstance(subitem.get("content"), list):
                text_parts.append(self._process_content_item(subitem))
                
        return " ".join(text_parts)
    
    async def update_ticket(self, ticket_id: str, status: str, comment: str) -> bool:
        """
        Update a ticket's status and add a comment
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., PROJECT-123)
            status: The new status to set
            comment: Comment to add to the ticket
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First, add a comment
            if comment:
                logger.info(f"Adding comment to ticket {ticket_id}")
                
                comment_data = {
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
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.jira_url}/rest/api/3/issue/{ticket_id}/comment",
                        json=comment_data,
                        auth=self.auth
                    )
                    
                    # Log the HTTP request for debugging
                    logger.info(f"HTTP Request: {response.request.method} {response.request.url} \"{response.http_version} {response.status_code} {response.reason_phrase}\"")
                    
                    if response.status_code not in (201, 200):
                        logger.error(f"Failed to add comment to ticket {ticket_id}: {response.status_code} - {response.text}")
                    else:
                        logger.info(f"Successfully added comment to ticket {ticket_id}")
            
            # Then, update the status
            logger.info(f"Updating ticket {ticket_id} status to '{status}'")
            
            # Get available transitions
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.jira_url}/rest/api/3/issue/{ticket_id}/transitions",
                    auth=self.auth
                )
                
                # Log the HTTP request for debugging
                logger.info(f"HTTP Request: {response.request.method} {response.request.url} \"{response.http_version} {response.status_code} {response.reason_phrase}\"")
                
                if response.status_code != 200:
                    logger.error(f"Failed to get transitions for ticket {ticket_id}: {response.status_code} - {response.text}")
                    return False
                
                transitions = response.json()["transitions"]
                
                # Find the transition ID for the desired status
                transition_id = None
                for transition in transitions:
                    if transition["to"]["name"].lower() == status.lower():
                        transition_id = transition["id"]
                        break
                
                if not transition_id:
                    logger.error(f"No transition found for status '{status}' for ticket {ticket_id}")
                    return False
                
                # Perform the transition
                transition_data = {
                    "transition": {
                        "id": transition_id
                    }
                }
                
                response = await client.post(
                    f"{self.jira_url}/rest/api/3/issue/{ticket_id}/transitions",
                    json=transition_data,
                    auth=self.auth
                )
                
                # Log the HTTP request for debugging
                logger.info(f"HTTP Request: {response.request.method} {response.request.url} \"{response.http_version} {response.status_code} {response.reason_phrase}\"")
                
                if response.status_code not in (204, 200):
                    logger.error(f"Failed to update status for ticket {ticket_id}: {response.status_code} - {response.text}")
                    return False
                
                logger.info(f"Successfully updated ticket {ticket_id} status to '{status}'")
                return True
                
        except Exception as e:
            logger.error(f"Error updating ticket {ticket_id}: {e}")
            return False