
import logging
import os
from datetime import datetime
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from env import JIRA_TOKEN, JIRA_USER, JIRA_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jira-utils")

async def update_jira_ticket(ticket_id: str, status: str, comment: str, pr_url: Optional[str] = None) -> bool:
    """Update JIRA ticket status and add a comment"""
    try:
        if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN]):
            logger.error("Missing JIRA credentials in environment variables")
            return False
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth = (JIRA_USER, JIRA_TOKEN)
            
            # Add comment
            comment_data = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "type": "text",
                            "text": comment
                        }]
                    }]
                }
            }
            
            comment_response = await client.post(
                f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/comment",
                json=comment_data,
                auth=auth
            )
            
            if comment_response.status_code not in [200, 201]:
                logger.error(f"Failed to add comment to JIRA ticket {ticket_id}: {comment_response.status_code}")
                return False
            
            if status:
                transitions_response = await client.get(
                    f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/transitions",
                    auth=auth
                )
                
                if transitions_response.status_code != 200:
                    logger.error(f"Failed to get transitions for JIRA ticket {ticket_id}")
                    return False
                
                transitions = transitions_response.json().get("transitions", [])
                transition_id = None
                
                for t in transitions:
                    if status.lower() in t['name'].lower():
                        transition_id = t['id']
                        break
                
                if transition_id:
                    transition_data = {
                        "transition": {
                            "id": transition_id
                        }
                    }
                    
                    transition_response = await client.post(
                        f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/transitions",
                        json=transition_data,
                        auth=auth
                    )
                    
                    if transition_response.status_code not in [200, 204]:
                        logger.error(f"Failed to transition JIRA ticket {ticket_id}")
                        return False
                else:
                    logger.warning(f"No transition found for status '{status}' for ticket {ticket_id}")
            
            # If PR URL is provided, update the ticket with PR link
            if pr_url:
                # Try to find the PR URL field - this might need customization based on your JIRA instance
                try:
                    # First fetch available fields to find the PR URL field
                    fields_response = await client.get(
                        f"{JIRA_URL}/rest/api/3/field",
                        auth=auth
                    )
                    
                    pr_field_id = None
                    if fields_response.status_code == 200:
                        fields = fields_response.json()
                        for field in fields:
                            if "PR" in field.get("name", "") or "Pull Request" in field.get("name", ""):
                                pr_field_id = field["id"]
                                break
                    
                    if pr_field_id:
                        fields_update = {
                            "fields": {
                                pr_field_id: pr_url
                            }
                        }
                        
                        update_response = await client.put(
                            f"{JIRA_URL}/rest/api/3/issue/{ticket_id}",
                            json=fields_update,
                            auth=auth
                        )
                        
                        if update_response.status_code not in [200, 204]:
                            logger.error(f"Failed to update PR URL for JIRA ticket {ticket_id}")
                    else:
                        # Fall back to adding PR URL to comment
                        pr_comment = f"Pull Request created: {pr_url}"
                        await client.post(
                            f"{JIRA_URL}/rest/api/3/issue/{ticket_id}/comment",
                            json={
                                "body": {
                                    "type": "doc",
                                    "version": 1,
                                    "content": [{
                                        "type": "paragraph",
                                        "content": [{
                                            "type": "text",
                                            "text": pr_comment
                                        }]
                                    }]
                                }
                            },
                            auth=auth
                        )
                except Exception as e:
                    logger.error(f"Error updating PR URL field: {str(e)}")
                    # Continue anyway, this is not critical
            
            logger.info(f"Successfully updated JIRA ticket {ticket_id}")
            return True
    
    except Exception as e:
        logger.error(f"Error updating JIRA ticket {ticket_id}: {str(e)}")
        return False

async def fetch_jira_tickets() -> List[Dict[str, Any]]:
    """Poll the JIRA API for new tickets labeled as Bug"""
    try:
        if not all([JIRA_URL, JIRA_USER, JIRA_TOKEN]):
            logger.error("Missing JIRA credentials in environment variables")
            return []
            
        logger.info("Fetching new bug tickets from JIRA")
        auth = (JIRA_USER, JIRA_TOKEN)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Include In Progress tickets as well to ensure workflow continuation
            jql_query = 'labels = Bug AND (status = "To Do" OR status = "In Progress" OR status = "Open")'
            
            response = await client.get(
                f"{JIRA_URL}/rest/api/3/search",
                params={"jql": jql_query, "fields": "summary,description,created,assignee,acceptanceCriteria,attachments,status,priority,reporter"},
                auth=auth
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch JIRA tickets: {response.status_code}")
                return []
                
            data = response.json()
            issues = data.get("issues", [])
            
            if not issues:
                logger.info("No new bug tickets found in JIRA")
                return []
                
            new_tickets = []
            
            for issue in issues:
                if not issue:
                    continue
                    
                ticket_id = issue.get("key")
                if not ticket_id:
                    continue
                    
                fields = issue.get("fields", {})
                if not fields:
                    logger.warning(f"No fields found in ticket {ticket_id}, skipping")
                    continue
                
                # Safely extract fields with proper error handling
                acceptance_criteria = fields.get("acceptanceCriteria", "")
                
                attachments = []
                for attachment in fields.get("attachments", []):
                    if not attachment:
                        continue
                    attachments.append({
                        "filename": attachment.get("filename", "unknown"),
                        "content_url": attachment.get("content", ""),
                        "mime_type": attachment.get("mimeType", "application/octet-stream")
                    })
                
                # Safely get assignee
                assignee = "Unassigned"
                if fields.get("assignee"):
                    assignee = fields["assignee"].get("displayName", "Unassigned")
                
                # Safely get reporter
                reporter = "Unknown"
                if fields.get("reporter"):
                    reporter = fields["reporter"].get("displayName", "Unknown")
                
                # Safely get priority
                priority = "Normal"
                if fields.get("priority"):
                    priority = fields["priority"].get("name", "Normal")
                
                # Safe extraction of status
                status = "Unknown"
                if fields.get("status") and isinstance(fields["status"], dict):
                    status = fields["status"].get("name", "Unknown")
                
                # Handle description which might be in Atlassian Document Format
                description = ""
                if fields.get("description"):
                    # Add additional null check and ensure we're not trying to access None values
                    desc_field = fields["description"]
                    if isinstance(desc_field, dict):
                        # Try to extract text from ADF with enhanced error handling
                        try:
                            desc_content = desc_field.get("content", [])
                            if desc_content is None:  # Additional null check
                                desc_content = []
                                
                            desc_parts = []
                            for content in desc_content:
                                if not content or not isinstance(content, dict):
                                    continue
                                    
                                if content.get("type") == "paragraph":
                                    paragraph_content = content.get("content", [])
                                    if paragraph_content is None:
                                        continue
                                        
                                    for text in paragraph_content:
                                        if not text or not isinstance(text, dict):
                                            continue
                                            
                                        text_value = text.get("text")
                                        if text_value:
                                            desc_parts.append(text_value)
                                        
                            description = "\n".join(desc_parts)
                            
                            # If we couldn't extract any text, provide a fallback
                            if not description:
                                logger.warning(f"Failed to extract description text for {ticket_id} - using fallback")
                                description = "No readable description available"
                                
                        except Exception as e:
                            logger.warning(f"Failed to parse description for {ticket_id}: {e}")
                            description = "Error extracting description"
                    elif desc_field is None:
                        description = ""
                    else:
                        description = str(desc_field)
                
                new_tickets.append({
                    "ticket_id": ticket_id,
                    "title": fields.get("summary", "No title"),
                    "description": description,
                    "created": fields.get("created", ""),
                    "acceptance_criteria": acceptance_criteria,
                    "attachments": attachments,
                    "status": status,
                    "priority": priority,
                    "reporter": reporter,
                    "assignee": assignee
                })
            
            logger.info(f"Found {len(new_tickets)} bug tickets")
            return new_tickets
    except Exception as e:
        logger.error(f"Error fetching JIRA tickets: {str(e)}")
        return []