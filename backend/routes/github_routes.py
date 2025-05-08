
import os
import json
import difflib
import logging
from flask import Blueprint, request, jsonify
from ..github_utils import get_file_content, generate_diff, commit_using_patch
from ..github_service.github_service import GitHubService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github-routes")

# Create blueprint for GitHub routes
github_bp = Blueprint('github', __name__, url_prefix='/api/github')

@github_bp.route('/config', methods=['GET'])
def get_github_config():
    """Get GitHub configuration from environment variables"""
    try:
        # Get GitHub configuration
        config = {
            'repo_owner': os.environ.get('GITHUB_REPO_OWNER', ''),
            'repo_name': os.environ.get('GITHUB_REPO_NAME', ''),
            'default_branch': os.environ.get('GITHUB_DEFAULT_BRANCH', 'main'),
            'branch': os.environ.get('GITHUB_BRANCH', ''),
            'patch_mode': os.environ.get('PATCH_MODE', 'line-by-line')
        }
        
        return jsonify({
            'success': True,
            'config': config
        }), 200
    except Exception as e:
        logger.error(f"Error getting GitHub config: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Failed to get GitHub config: {str(e)}"
        }), 500

@github_bp.route('/patch', methods=['POST'])
def create_patch():
    """Generate a patch for file changes"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
            
        # Extract required data
        repo_name = data.get('repo_name')
        branch = data.get('branch')
        file_path = data.get('file_path')
        modified_content = data.get('modified_content')
        
        if not all([repo_name, file_path, modified_content]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
            
        # Get the original file content
        original_content = get_file_content(repo_name, file_path, branch)
        if original_content is None:
            return jsonify({
                'success': False,
                'error': f'File {file_path} not found'
            }), 404
            
        # Generate a diff between the original and modified content
        diff = generate_diff(original_content, modified_content, file_path)
        
        return jsonify({
            'success': True,
            'diff': diff,
            'filename': file_path,
            'linesAdded': diff.count('\n+') - 1,  # -1 to account for the +++ line
            'linesRemoved': diff.count('\n-') - 1  # -1 to account for the --- line
        }), 200
    except Exception as e:
        logger.error(f"Error generating patch: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Failed to generate patch: {str(e)}"
        }), 500

@github_bp.route('/commit', methods=['POST'])
def commit_changes():
    """Commit changes to GitHub using patch-based updates"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
            
        # Extract required data
        repo_name = data.get('repo_name')
        branch = data.get('branch')
        file_changes = data.get('file_changes', [])
        commit_message = data.get('commit_message', 'Update files')
        
        if not all([repo_name, branch, file_changes]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
            
        # Extract file paths and contents
        file_paths = []
        modified_contents = []
        
        for change in file_changes:
            if not change.get('filename') or not change.get('content'):
                continue
            
            file_paths.append(change.get('filename'))
            modified_contents.append(change.get('content'))
            
        # Commit the changes using the patch method
        result = commit_using_patch(repo_name, branch, file_paths, modified_contents, commit_message)
        
        if result:
            return jsonify({
                'success': True,
                'message': f"Changes committed to branch {branch}",
                'branch': branch,
                'files_changed': len(file_paths)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to commit changes'
            }), 500
    except Exception as e:
        logger.error(f"Error committing changes: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Failed to commit changes: {str(e)}"
        }), 500

@github_bp.route('/file', methods=['GET'])
def get_file():
    """Get the content of a file from GitHub"""
    try:
        repo_name = request.args.get('repo')
        file_path = request.args.get('path')
        branch = request.args.get('branch')
        
        if not all([repo_name, file_path]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
            
        # Get the file content
        content = get_file_content(repo_name, file_path, branch)
        if content is None:
            return jsonify({
                'success': False,
                'error': f'File {file_path} not found'
            }), 404
            
        return jsonify({
            'success': True,
            'content': content,
            'file_path': file_path
        }), 200
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Failed to get file content: {str(e)}"
        }), 500