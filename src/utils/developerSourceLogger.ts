
/**
 * Utility to extract and log GitHub source information
 */

export interface GitHubSource {
  repo_owner?: string;
  repo_name?: string;
  branch?: string;
  default_branch?: string;
  patch_mode?: string;
  commit_sha?: string;
}

/**
 * Extract GitHub source information from environment variables
 */
export function extractGitHubSourceFromEnv(): GitHubSource {
  console.log('Extracting GitHub source information from environment variables...');
  
  // Log available environment variables without exposing sensitive values
  console.log('Available GitHub env variables:', {
    GITHUB_REPO_OWNER: Boolean(process.env.GITHUB_REPO_OWNER || import.meta.env.VITE_GITHUB_REPO_OWNER),
    GITHUB_REPO_NAME: Boolean(process.env.GITHUB_REPO_NAME || import.meta.env.VITE_GITHUB_REPO_NAME),
    GITHUB_BRANCH: Boolean(process.env.GITHUB_BRANCH || import.meta.env.VITE_GITHUB_BRANCH),
    GITHUB_DEFAULT_BRANCH: Boolean(process.env.GITHUB_DEFAULT_BRANCH || import.meta.env.VITE_GITHUB_DEFAULT_BRANCH),
    PATCH_MODE: Boolean(process.env.PATCH_MODE || import.meta.env.VITE_PATCH_MODE),
    GITHUB_COMMIT_SHA: Boolean(process.env.GITHUB_COMMIT_SHA || import.meta.env.VITE_GITHUB_COMMIT_SHA),
  });
  
  const source = {
    repo_owner: process.env.GITHUB_REPO_OWNER || import.meta.env.VITE_GITHUB_REPO_OWNER as string,
    repo_name: process.env.GITHUB_REPO_NAME || import.meta.env.VITE_GITHUB_REPO_NAME as string,
    branch: process.env.GITHUB_BRANCH || import.meta.env.VITE_GITHUB_BRANCH as string,
    default_branch: process.env.GITHUB_DEFAULT_BRANCH || import.meta.env.VITE_GITHUB_DEFAULT_BRANCH as string || 'main',
    patch_mode: process.env.PATCH_MODE || import.meta.env.VITE_PATCH_MODE as string || 'line-by-line',
    commit_sha: process.env.GITHUB_COMMIT_SHA || import.meta.env.VITE_GITHUB_COMMIT_SHA as string
  };
  
  // Log the actual values for debugging
  const repoInfo = `${source.repo_owner || 'unknown'}/${source.repo_name || 'unknown'}`;
  console.log(`Extracted repository: ${repoInfo}`);
  console.log(`Extracted branch: ${source.branch || source.default_branch || 'main'}`);
  console.log(`Extracted patch mode: ${source.patch_mode || 'line-by-line'}`);
  
  // Log the actual values - helpful for debugging
  console.log('Actual source values:', {
    repo_owner: source.repo_owner || 'undefined',
    repo_name: source.repo_name || 'undefined',
    branch: source.branch || 'undefined',
    default_branch: source.default_branch || 'undefined',
    patch_mode: source.patch_mode || 'undefined',
    commit_sha: source.commit_sha || 'undefined'
  });
  
  return source;
}

/**
 * Check if GitHub source information is valid and complete
 */
export function isValidGitHubSource(source: GitHubSource | null): boolean {
  if (!source) {
    console.log('GitHub source validation: Invalid (source is null)');
    return false;
  }
  
  const hasOwner = Boolean(source.repo_owner);
  const hasRepo = Boolean(source.repo_name);
  const hasBranch = Boolean(source.branch || source.default_branch);
  
  const isValid = hasOwner && hasRepo && hasBranch;
  console.log(`GitHub source validation: ${isValid ? 'Valid' : 'Invalid'} (Owner: ${hasOwner}, Repo: ${hasRepo}, Branch: ${hasBranch})`);
  
  // Additional info for debugging if invalid
  if (!isValid) {
    console.log('Missing GitHub source components:', {
      repo_owner: !hasOwner ? 'missing' : 'present',
      repo_name: !hasRepo ? 'missing' : 'present',
      branch: !hasBranch ? 'missing' : 'present',
    });
  }
  
  return isValid;
}

/**
 * Log GitHub source information to console
 */
export function logGitHubSource(source: GitHubSource | null): void {
  if (!source) {
    console.log('No GitHub source information available');
    return;
  }
  
  console.log('GitHub Source Information:');
  console.log(`Repository: ${source.repo_owner}/${source.repo_name}`);
  console.log(`Branch: ${source.branch || source.default_branch || 'main'}`);
  console.log(`Patch Mode: ${source.patch_mode || 'line-by-line'}`);
  
  if (source.commit_sha) {
    console.log(`Commit SHA: ${source.commit_sha}`);
  }
}

/**
 * Diagnoses possible reasons for GitHub file access issues
 */
export function diagnoseGitHubAccessIssues(source: GitHubSource | null): string[] {
  const issues: string[] = [];
  
  if (!source) {
    issues.push('No GitHub repository information available');
    return issues;
  }
  
  if (!source.repo_owner) {
    issues.push('Missing GitHub repository owner');
  }
  
  if (!source.repo_name) {
    issues.push('Missing GitHub repository name');
  }
  
  if (!source.branch && !source.default_branch) {
    issues.push('Missing GitHub branch information');
  }
  
  // If we have all required fields but still having issues
  if (issues.length === 0) {
    issues.push('Possible authorization/authentication issues with GitHub');
    issues.push('Repository might be private and requires proper access token');
    issues.push('Repository path might be incorrect');
  }
  
  return issues;
}