
import { GitHubConfig } from '@/types/ticket';
import { isValidGitHubSource, diagnoseGitHubAccessIssues } from '@/utils/developerSourceLogger';

// Store PR number mappings
const prMappings: Record<string, number> = {};

/**
 * Get GitHub configuration from environment variables or API
 */
export const getGitHubConfig = async (): Promise<GitHubConfig | null> => {
  try {
    console.log('Fetching GitHub configuration...');
    // In a real app, this would make an API call to the backend
    // For now, we'll just use environment variables or simulated data
    const config: GitHubConfig = {
      repo_owner: process.env.GITHUB_REPO_OWNER || import.meta.env.VITE_GITHUB_REPO_OWNER as string || 'example-org',
      repo_name: process.env.GITHUB_REPO_NAME || import.meta.env.VITE_GITHUB_REPO_NAME as string || 'example-repo',
      default_branch: process.env.GITHUB_DEFAULT_BRANCH || import.meta.env.VITE_GITHUB_DEFAULT_BRANCH as string || 'main',
      branch: process.env.GITHUB_BRANCH || import.meta.env.VITE_GITHUB_BRANCH as string || 'feature/bugfix',
      patch_mode: (process.env.PATCH_MODE || import.meta.env.VITE_PATCH_MODE as string || 'line-by-line') as 'intelligent' | 'line-by-line' | 'direct'
    };
    
    // Log the config for debugging (without sensitive data)
    console.log(`GitHub config loaded: ${config.repo_owner}/${config.repo_name}`);
    console.log(`Using branch: ${config.branch} (default: ${config.default_branch})`);
    console.log(`Using patch mode: ${config.patch_mode}`);
    
    // Log raw environment variables (redacted) for debugging
    console.log('Environment variables present:', {
      GITHUB_REPO_OWNER: Boolean(process.env.GITHUB_REPO_OWNER),
      VITE_GITHUB_REPO_OWNER: Boolean(import.meta.env.VITE_GITHUB_REPO_OWNER),
      GITHUB_REPO_NAME: Boolean(process.env.GITHUB_REPO_NAME),
      VITE_GITHUB_REPO_NAME: Boolean(import.meta.env.VITE_GITHUB_REPO_NAME)
    });
    
    // Validate the configuration
    const valid = isValidGitHubSource(config);
    if (!valid) {
      console.warn('GitHub configuration is incomplete or invalid');
      const issues = diagnoseGitHubAccessIssues(config);
      console.warn('Potential GitHub access issues:', issues);
    }
    
    return config;
  } catch (error) {
    console.error('Failed to get GitHub configuration:', error);
    return null;
  }
};

/**
 * Generate a patch/diff between original and modified file content
 */
export const generateDiff = (originalContent: string, modifiedContent: string, filename: string): string => {
  console.log(`Generating diff for file: ${filename}`);
  
  // This is a simplified diff generation - in a real app, you'd use a proper diff library
  const originalLines = originalContent.split('\n');
  const modifiedLines = modifiedContent.split('\n');
  
  // Mock diff generation - in reality this would use a proper diff algorithm
  let diff = `--- a/${filename}\n+++ b/${filename}\n`;
  
  // Find some line numbers for the mock diff
  const lineNum = Math.min(originalLines.length, 5);
  diff += `@@ -${lineNum},3 +${lineNum},3 @@\n`;
  
  // Add some context lines
  for (let i = Math.max(0, lineNum - 2); i < lineNum; i++) {
    diff += ` ${originalLines[i] || ''}\n`;
  }
  
  // Add a removed line
  diff += `-${originalLines[lineNum] || ''}\n`;
  
  // Add an added line
  diff += `+${modifiedLines[lineNum] || originalLines[lineNum] + ' // modified'}\n`;
  
  // Add more context
  for (let i = lineNum + 1; i < lineNum + 3 && i < originalLines.length; i++) {
    diff += ` ${originalLines[i] || ''}\n`;
  }
  
  console.log(`Generated ${diff.split('\n').length} lines of diff`);
  return diff;
};

/**
 * Check if a file exists in the repository
 * Note: In this frontend-only implementation, this is a mock function
 */
export const checkFileExists = async (filePath: string): Promise<boolean> => {
  console.log(`Checking if file exists: ${filePath}`);
  try {
    // In a real implementation, this would call the backend
    // For testing, simulate file existence
    const result = true;
    console.log(`File ${filePath} exists: ${result}`);
    return result;
  } catch (error) {
    console.error(`Error checking if file exists [${filePath}]:`, error);
    return false;
  }
};

/**
 * Get file content from repository
 * Note: In this frontend-only implementation, this is a mock function
 */
export const getFileContent = async (filePath: string): Promise<string | null> => {
  console.log(`Attempting to get content for file: ${filePath}`);
  
  try {
    // In a real implementation, this would call the backend API
    // For testing, return mock content based on file type
    let mockContent = `// Mock content for ${filePath}\n// This would be the actual file content in a real implementation\n\n`;
    
    if (filePath.endsWith('.py')) {
      mockContent += `import os\nimport sys\n\ndef main():\n    print("This is mock Python content")\n\nif __name__ == "__main__":\n    main()\n`;
    } else if (filePath.endsWith('.js') || filePath.endsWith('.ts')) {
      mockContent += `function exampleCode() {\n  console.log("This is mock JavaScript content");\n}\n\nexport default exampleCode;\n`;
    } else {
      mockContent += `function exampleCode() {\n  console.log("This is mock content");\n}\n`;
    }
    
    console.log(`Successfully generated mock content for ${filePath} (${mockContent.length} bytes)`);
    return mockContent;
  } catch (error) {
    console.error(`Failed to get content for ${filePath}:`, error);
    return null;
  }
};

/**
 * Detailed debugging function to pinpoint file access issues
 */
export const debugFileAccess = async (repo: string, branch: string, filePath: string): Promise<{
  success: boolean;
  message: string;
  details: Record<string, unknown>;
}> => {
  console.log(`Debugging file access: ${repo} / ${branch} / ${filePath}`);
  
  try {
    // Test if GitHub configuration is available
    const config = await getGitHubConfig();
    if (!config) {
      return {
        success: false,
        message: "GitHub configuration unavailable",
        details: {
          reason: "Missing GitHub configuration",
          environment: {
            repoOwnerPresent: Boolean(process.env.GITHUB_REPO_OWNER || import.meta.env.VITE_GITHUB_REPO_OWNER),
            repoNamePresent: Boolean(process.env.GITHUB_REPO_NAME || import.meta.env.VITE_GITHUB_REPO_NAME)
          }
        }
      };
    }
    
    // Check if file exists
    const exists = await checkFileExists(filePath);
    if (!exists) {
      return {
        success: false,
        message: `File not found: ${filePath}`,
        details: {
          reason: "File not found",
          path: filePath,
          repository: repo,
          branch: branch
        }
      };
    }
    
    // Try to get content
    const content = await getFileContent(filePath);
    if (!content) {
      return {
        success: false,
        message: `Content retrieval failed for: ${filePath}`,
        details: {
          reason: "Content retrieval error",
          path: filePath,
          repository: repo,
          branch: branch
        }
      };
    }
    
    return {
      success: true,
      message: `Successfully accessed file: ${filePath}`,
      details: {
        path: filePath,
        repository: repo,
        branch: branch,
        contentLength: content.length
      }
    };
  } catch (error) {
    return {
      success: false,
      message: `Error debugging file access: ${error}`,
      details: {
        error: String(error),
        path: filePath,
        repository: repo,
        branch: branch
      }
    };
  }
};

/**
 * Store a mapping between a ticket ID and PR number
 * @param ticketId - The JIRA ticket ID
 * @param prNumber - The GitHub PR number
 */
export const storePRMapping = (ticketId: string, prNumber: number): void => {
  console.log(`Storing PR mapping: ${ticketId} -> PR #${prNumber}`);
  prMappings[ticketId] = prNumber;
};

/**
 * Get the PR number for a ticket if a mapping exists
 * @param ticketId - The JIRA ticket ID
 * @returns The PR number if a mapping exists, undefined otherwise
 */
export const getPRNumberForTicket = (ticketId: string): number | undefined => {
  return prMappings[ticketId];
};

/**
 * Safely extract a numeric PR number from various input formats
 * @param prIdentifier - Can be a number, string number, URL, or other identifier
 * @returns A PR number as an integer, or null if not extractable
 */
export const extractPRNumber = (prIdentifier: string | number): number | null => {
  console.log(`Attempting to extract PR number from: ${prIdentifier}`);
  
  // If already a number, return it
  if (typeof prIdentifier === 'number') {
    return prIdentifier;
  }
  
  // If string is just a number, convert it
  if (/^\d+$/.test(prIdentifier)) {
    return parseInt(prIdentifier, 10);
  }
  
  // Check if it's a ticket ID with a known PR mapping
  if (typeof prIdentifier === 'string' && prMappings[prIdentifier]) {
    console.log(`Found PR mapping for ticket ${prIdentifier}: PR #${prMappings[prIdentifier]}`);
    return prMappings[prIdentifier];
  }
  
  // Try to extract PR number from a GitHub URL
  // Format: https://github.com/owner/repo/pull/123
  const urlMatch = /\/pull\/(\d+)/.exec(prIdentifier);
  if (urlMatch && urlMatch[1]) {
    return parseInt(urlMatch[1], 10);
  }
  
  // IMPORTANT: Do NOT extract numbers from JIRA ticket IDs
  // Previously, we would extract digits from SCRUM-2 to get PR #2, which is incorrect
  if (/^[A-Z]+-\d+$/.test(prIdentifier)) {
    console.log(`Not extracting PR number from JIRA ticket ID: ${prIdentifier}`);
    return null;
  }
  
  console.warn(`Could not extract PR number from: ${prIdentifier}`);
  return null;
};

/**
 * Add a comment to a PR, handling various input formats for the PR identifier
 * @param prIdentifier - PR number or URL
 * @param comment - Comment content
 * @returns Success status
 */
export const addPRComment = async (prIdentifier: string | number, comment: string): Promise<boolean> => {
  // Extract numeric PR number if needed
  const prNumber = extractPRNumber(prIdentifier);
  
  // If we couldn't get a PR number, try to find a PR for the ticket if this is a ticket ID
  if (prNumber === null && typeof prIdentifier === 'string' && /^[A-Z]+-\d+$/.test(prIdentifier)) {
    console.log(`Attempting to find PR for ticket ID: ${prIdentifier}`);
    
    // In a real application, this would call an API to find the PR
    // For this implementation, we'll just check our mapping
    if (prMappings[prIdentifier]) {
      console.log(`Found PR #${prMappings[prIdentifier]} for ticket ${prIdentifier}`);
      try {
        console.log(`Would add comment to PR #${prMappings[prIdentifier]}: ${comment.substring(0, 50)}${comment.length > 50 ? '...' : ''}`);
        return true;
      } catch (error) {
        console.error(`Error adding comment to PR #${prMappings[prIdentifier]}:`, error);
        return false;
      }
    }
    
    console.error(`No PR found for ticket ID: ${prIdentifier}`);
    return false;
  }
  
  // If we still don't have a PR number, log error and return false
  if (prNumber === null) {
    console.error(`Failed to extract PR number from: ${prIdentifier}`);
    return false;
  }
  
  console.log(`Adding comment to PR #${prNumber}`);
  
  try {
    // In a real implementation, this would call an API to add the comment
    // For testing, log the comment that would be added
    console.log(`Would add comment to PR #${prNumber}: ${comment.substring(0, 50)}${comment.length > 50 ? '...' : ''}`);
    return true;
  } catch (error) {
    console.error(`Error adding comment to PR #${prNumber}:`, error);
    return false;
  }
};