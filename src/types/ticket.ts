
export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  reporter: string;
  assignee: string | null;
  created: string;
  updated: string;
  escalated?: boolean;
  current_attempt?: number;
  max_attempts?: number;
  escalation_reason?: string;
  confidence_score?: number;
  retry_history?: Array<{
    result: 'success' | 'failure';
    qa_message?: string;
  }>;
  early_escalation?: boolean;
  code_context?: { [filePath: string]: string }; // Added code_context property
  github_source?: {
    repo_owner?: string;
    repo_name?: string;
    branch?: string;
    default_branch?: string;
    patch_mode?: string;
  };
}

export interface AffectedFile {
  file: string;
  valid: boolean;
  reason?: string;
  content?: string;  // Added content property
}

export interface PlannerAnalysis {
  ticket_id: string;
  bug_summary: string;
  affected_files: string[] | AffectedFile[];
  error_type: string;
  using_fallback?: boolean;
  affectedFiles?: string[];  // For backward compatibility
  rootCause?: string;        // For backward compatibility
  suggestedApproach?: string; // For backward compatibility
  code_context?: { [filePath: string]: string }; // Added code_context property
}

export interface CodeDiff {
  filename: string;
  diff: string;
  linesAdded: number;
  linesRemoved: number;
  // Removed oldPath and newPath properties and replaced with filename
  // Removed content property and replaced with diff
}

export type TestStatus = 'pass' | 'fail';

export interface TestResult {
  name: string;
  status: TestStatus;
  duration: number;
  errorMessage?: string;
  output?: string;
}

export type UpdateType = 'jira' | 'github' | 'system';

export interface Update {
  timestamp: string;
  message: string;
  type: UpdateType;
  confidenceScore?: number;
  metadata?: unknown; // Added metadata property to support validation results and other additional data
  github_source?: {
    repo_owner?: string;
    repo_name?: string;
    branch?: string;
    patch_mode?: string;
  };
}

export interface GitHubConfig {
  repo_owner: string;
  repo_name: string;
  default_branch: string;
  branch: string;
  patch_mode: 'intelligent' | 'line-by-line' | 'direct';
}