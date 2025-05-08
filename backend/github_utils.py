
import logging
import os
import base64
import difflib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from github import Github, GithubException, InputGitTreeElement

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-utils")

def authenticate_github():
    """Authenticate with GitHub using the personal access token"""
    # Get the GitHub token from environment variables first
    github_token = os.environ.get("GITHUB_TOKEN")
    
    # If not found in environment, try importing from env.py if it exists
    if not github_token:
        try:
            from env import GITHUB_TOKEN
            github_token = GITHUB_TOKEN
        except ImportError:
            logger.error("GitHub token not found. Please set GITHUB_TOKEN environment variable.")
            return None
        
    if not github_token:
        logger.error("GitHub token not found. Please set GITHUB_TOKEN environment variable.")
        return None
        
    try:
        github_client = Github(github_token)
        # Test the connection
        user = github_client.get_user()
        logger.info(f"Authenticated as GitHub user: {user.login}")
        return github_client
    except GithubException as e:
        logger.error(f"GitHub authentication error: {str(e)}")
        return None

def get_repo(repo_name: str = None):
    """Get a repository by name or from environment variables"""
    github_client = authenticate_github()
    if not github_client:
        return None
    
    # If repo_name is provided, use it directly
    if repo_name:
        try:
            return github_client.get_repo(repo_name)
        except GithubException as e:
            logger.error(f"Error accessing repository {repo_name}: {str(e)}")
            return None
    
    # Otherwise try to construct from environment variables
    owner = os.environ.get("GITHUB_REPO_OWNER")
    name = os.environ.get("GITHUB_REPO_NAME")
    
    if not owner or not name:
        logger.error("GITHUB_REPO_OWNER and GITHUB_REPO_NAME environment variables are required")
        return None
    
    try:
        full_name = f"{owner}/{name}"
        return github_client.get_repo(full_name)
    except GithubException as e:
        logger.error(f"Error accessing repository {full_name}: {str(e)}")
        return None

def create_branch(repo_name: str, ticket_id: str, base_branch: str = None) -> Optional[str]:
    """Create a new branch for the bugfix"""
    try:
        # Use default branch from environment if not specified
        if not base_branch:
            base_branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")
            
        # Get repository
        repo = get_repo(repo_name)
        if not repo:
            return None
            
        # Get the base branch to branch off from
        try:
            base_ref = repo.get_branch(base_branch)
        except GithubException as e:
            logger.error(f"Base branch '{base_branch}' not found: {str(e)}")
            return None
            
        # Create branch name using convention bugfix/{ticket-id}
        branch_name = f"bugfix/{ticket_id}"
        
        # Check if branch already exists
        try:
            repo.get_branch(branch_name)
            logger.info(f"Branch {branch_name} already exists, reusing it")
            return branch_name
        except GithubException:
            # Branch doesn't exist, create it
            try:
                repo.create_git_ref(f"refs/heads/{branch_name}", base_ref.commit.sha)
                logger.info(f"Created branch {branch_name} from {base_branch}")
                return branch_name
            except GithubException as e:
                logger.error(f"Failed to create branch {branch_name}: {str(e)}")
                return None
    except Exception as e:
        logger.error(f"Error creating branch: {str(e)}")
        return None

def commit_changes(repo_name: str, branch_name: str, file_changes: List[Dict[str, Any]], 
                commit_message: str) -> bool:
    """Commit file changes to the branch"""
    try:
        github_client = authenticate_github()
        if not github_client:
            return False
            
        # Get the repository and branch reference
        repo = get_repo(repo_name)
        if not repo:
            return False
        
        # First attempt: Try updating files one by one
        all_success = True
        for file_change in file_changes:
            filename = file_change.get('filename')
            content = file_change.get('content')
            
            if not filename or not content:
                logger.warning(f"Skipping invalid file change: {file_change}")
                all_success = False
                continue
                
            try:
                # Check if file exists
                try:
                    file_content = repo.get_contents(filename, ref=branch_name)
                    # Update existing file
                    repo.update_file(
                        path=filename,
                        message=f"Update {filename} - {commit_message}",
                        content=content,
                        sha=file_content.sha,
                        branch=branch_name
                    )
                    logger.info(f"Updated file {filename} in {branch_name}")
                except GithubException:
                    # File doesn't exist, create it
                    repo.create_file(
                        path=filename,
                        message=f"Create {filename} - {commit_message}",
                        content=content,
                        branch=branch_name
                    )
                    logger.info(f"Created file {filename} in {branch_name}")
            except GithubException as e:
                logger.error(f"Failed to update/create file {filename}: {str(e)}")
                all_success = False
                
        return all_success
    except Exception as e:
        logger.error(f"Error committing changes: {str(e)}")
        return False

def create_pull_request(repo_name: str, branch_name: str, ticket_id: str, title: str, 
                      description: str, base_branch: str = None) -> Optional[str]:
    """Create a pull request from the bugfix branch to the base branch"""
    try:
        # Use default branch from environment if not specified
        if not base_branch:
            base_branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")
            
        # Get repository
        repo = get_repo(repo_name)
        if not repo:
            return None
        
        # Check if PR already exists
        existing_prs = repo.get_pulls(state='open', head=branch_name, base=base_branch)
        for pr in existing_prs:
            logger.info(f"Pull request already exists for branch {branch_name}: {pr.html_url}")
            return pr.html_url
        
        # Create PR title
        pr_title = f"Fix for {ticket_id}: {title}"
        
        # Create PR body with ticket link and summary
        jira_url = os.getenv('JIRA_URL', '')
        ticket_link = f"{jira_url}/browse/{ticket_id}" if jira_url else ticket_id
        
        pr_body = f"""
## Bug Fix: {ticket_id}

**JIRA Ticket:** [{ticket_id}]({ticket_link})

### Summary of Changes
{description}

### Automated PR
This PR was automatically generated by BugFix AI.
        """
        
        # Create the PR with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                pull = repo.create_pull(
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base=base_branch
                )
                
                # Add labels
                pull.add_to_labels("autofix", "bug")
                
                logger.info(f"Created PR #{pull.number} for {ticket_id}")
                return pull.html_url
            except GithubException as e:
                if e.status == 422:  # PR already exists or other validation errors
                    logger.error(f"Cannot create PR: {str(e)}")
                    return None
                elif attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Retrying PR creation in {wait_time} seconds: {str(e)}")
                    import time
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to create PR after {max_retries} attempts: {str(e)}")
                    return None
    except Exception as e:
        logger.error(f"Error creating PR: {str(e)}")
        return None

def commit_multiple_changes_as_tree(repo_name: str, branch_name: str, 
                                  file_changes: List[Dict[str, Any]], commit_message: str) -> bool:
    """
    Commit multiple file changes at once using Git trees for better performance
    and atomic commits across multiple files.
    """
    try:
        github_client = authenticate_github()
        if not github_client:
            return False
            
        # Get the repository
        repo = get_repo(repo_name)
        if not repo:
            return False
        
        try:
            # Get the latest commit on the branch
            ref = repo.get_git_ref(f"heads/{branch_name}")
            latest_commit = repo.get_git_commit(ref.object.sha)
            base_tree = latest_commit.tree
            
            # Create tree elements for new files
            tree_elements = []
            for file_change in file_changes:
                filename = file_change.get('filename')
                content = file_change.get('content')
                
                if not filename or content is None:
                    logger.warning(f"Skipping invalid file change: {file_change}")
                    continue
                    
                # Convert content to string if it's not already
                if not isinstance(content, str):
                    content = str(content)
                
                element = InputGitTreeElement(
                    path=filename,
                    mode='100644',  # Regular file mode
                    type='blob',
                    content=content
                )
                tree_elements.append(element)
            
            # Create a tree with the new files
            new_tree = repo.create_git_tree(tree_elements, base_tree)
            
            # Create a commit with the new tree
            new_commit = repo.create_git_commit(
                message=commit_message,
                tree=new_tree,
                parents=[latest_commit]
            )
            
            # Update the reference to point to the new commit
            ref.edit(new_commit.sha)
            
            logger.info(f"Committed {len(tree_elements)} files to {branch_name}")
            return True
        except GithubException as e:
            logger.error(f"Failed to commit files as tree: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error in commit_multiple_changes_as_tree: {str(e)}")
        return False

def push_branch(repo_name: str, branch_name: str) -> bool:
    """
    Push a branch to remote. Note: With PyGithub this is usually not necessary
    as commits are automatically pushed to remote when using create_file, update_file,
    or commit_multiple_changes_as_tree.
    """
    # PyGithub automatically pushes when committing, so this is just here for completeness
    # and in case we need to add additional logic
    logger.info(f"Branch {branch_name} automatically pushed during commit")
    return True

def get_branch_commit_history(repo_name: str, branch_name: str, max_commits: int = 10) -> List[Dict]:
    """Get the commit history for a branch"""
    try:
        repo = get_repo(repo_name)
        if not repo:
            return []
        
        # Get commits on the branch
        commits = []
        try:
            branch = repo.get_branch(branch_name)
            commit_iter = repo.get_commits(sha=branch.commit.sha, max_count=max_commits)
            
            for commit in commit_iter:
                commits.append({
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date.isoformat(),
                    'url': commit.html_url
                })
            
            return commits
        except GithubException as e:
            logger.error(f"Failed to get commit history for branch {branch_name}: {str(e)}")
            return []
    except Exception as e:
        logger.error(f"Error getting branch commit history: {str(e)}")
        return []

def get_file_content(repo_name: str, file_path: str, branch: str = None) -> Optional[str]:
    """Get the content of a file from GitHub"""
    try:
        repo = get_repo(repo_name)
        if not repo:
            return None
            
        if not branch:
            branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")
            
        try:
            file_content = repo.get_contents(file_path, ref=branch)
            if file_content.encoding == "base64":
                return base64.b64decode(file_content.content).decode('utf-8')
            else:
                return file_content.decoded_content.decode('utf-8')
        except GithubException as e:
            logger.error(f"Failed to get file content for {file_path}: {str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return None

def generate_diff(original_content: str, modified_content: str, file_path: str) -> str:
    """Generate unified diff between two versions of a file"""
    try:
        # Create a unified diff
        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3  # Context lines
        )
        
        return "".join(diff)
    except Exception as e:
        logger.error(f"Error generating diff: {str(e)}")
        return ""

def commit_using_patch(repo_name: str, branch_name: str, file_paths: List[str], 
                      modified_contents: List[str], commit_message: str) -> bool:
    """
    Commit changes by generating and applying diffs rather than replacing entire files
    
    Args:
        repo_name: Repository name or full path
        branch_name: Branch to commit to
        file_paths: List of file paths to update
        modified_contents: List of modified content for each file path
        commit_message: Commit message
        
    Returns:
        Success status (True/False)
    """
    try:
        # Make sure we have matching lists
        if len(file_paths) != len(modified_contents):
            logger.error("File paths and modified contents must have the same length")
            return False
            
        repo = get_repo(repo_name)
        if not repo:
            return False
            
        # Process one file at a time
        diffs = []
        file_changes = []
        
        for i, file_path in enumerate(file_paths):
            # Get the original content
            original_content = get_file_content(repo_name, file_path, branch_name)
            if original_content is None:
                # File doesn't exist, so we'll create it
                logger.info(f"File {file_path} doesn't exist, will create it")
                file_changes.append({
                    'filename': file_path,
                    'content': modified_contents[i],
                    'action': 'create'
                })
                continue
                
            # Skip if no changes
            if original_content == modified_contents[i]:
                logger.info(f"No changes detected for {file_path}, skipping")
                continue
                
            # Generate a diff
            diff = generate_diff(original_content, modified_contents[i], file_path)
            diffs.append({
                'file_path': file_path,
                'diff': diff
            })
            
            # Also prepare the complete file for the commit
            file_changes.append({
                'filename': file_path,
                'content': modified_contents[i],
                'action': 'update'
            })
            
        # Log the diffs for debugging
        for diff_info in diffs:
            logger.info(f"Diff for {diff_info['file_path']}:")
            logger.info(diff_info['diff'][:200] + "..." if len(diff_info['diff']) > 200 else diff_info['diff'])
            
        # Commit the changes using the tree API for efficiency
        if file_changes:
            return commit_multiple_changes_as_tree(repo_name, branch_name, file_changes, commit_message)
        else:
            logger.info("No changes to commit")
            return True
    except Exception as e:
        logger.error(f"Error committing using patch: {str(e)}")
        return False