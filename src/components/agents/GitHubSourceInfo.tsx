
import React, { useState } from 'react';
import { GitHubSource, diagnoseGitHubAccessIssues } from '@/utils/developerSourceLogger';
import { Github, AlertCircle, ChevronDown, ChevronRight, Check, FileWarning } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { debugFileAccess } from '@/services/githubService';

interface GitHubSourceInfoProps {
  source: GitHubSource | null;
  fileErrors?: Record<string, string>;
}

const GitHubSourceInfo: React.FC<GitHubSourceInfoProps> = ({ source, fileErrors = {} }) => {
  const [showDetails, setShowDetails] = useState(false);
  const [testingFile, setTestingFile] = useState(false);
  const [testFileResult, setTestFileResult] = useState<null | {success: boolean; message: string}>(null);
  const [testFileName, setTestFileName] = useState('');

  if (!source || (!source.repo_owner && !source.repo_name)) {
    const possibleIssues = diagnoseGitHubAccessIssues(source);
    
    return (
      <Alert className="mb-4 bg-red-50 border-red-300">
        <div className="flex items-center gap-2">
          <AlertCircle size={16} className="text-red-500" />
          <AlertTitle className="text-red-700">Missing GitHub Source</AlertTitle>
        </div>
        <AlertDescription className="mt-2 text-xs text-red-700">
          <div>No GitHub repository information available. This will prevent file access.</div>
          
          {possibleIssues.length > 0 && (
            <div className="mt-2">
              <div className="font-medium mb-1">Possible issues:</div>
              <ul className="list-disc pl-4 space-y-0.5">
                {possibleIssues.map((issue, index) => (
                  <li key={index}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  const repoUrl = source.repo_owner && source.repo_name 
    ? `https://github.com/${source.repo_owner}/${source.repo_name}` 
    : null;
  
  const branchUrl = repoUrl && source.branch 
    ? `${repoUrl}/tree/${source.branch}` 
    : null;

  // Ensure we have a branch to display, using fallbacks
  const displayBranch = source.branch || source.default_branch || 'main';
  // Ensure we have a patch_mode to display, using fallback
  const displayPatchMode = source.patch_mode || 'line-by-line';
  
  // Check for file errors
  const hasFileErrors = Object.keys(fileErrors).length > 0;

  const handleTestFileAccess = async () => {
    if (!testFileName || !source.repo_owner || !source.repo_name) return;
    
    setTestingFile(true);
    setTestFileResult(null);
    
    try {
      const result = await debugFileAccess(
        `${source.repo_owner}/${source.repo_name}`,
        displayBranch,
        testFileName
      );
      
      setTestFileResult({
        success: result.success,
        message: result.message
      });
    } catch (error) {
      setTestFileResult({
        success: false,
        message: `Error: ${error}`
      });
    } finally {
      setTestingFile(false);
    }
  };

  return (
    <Alert className={`mb-4 ${hasFileErrors ? 'bg-amber-50 border-amber-300' : 'bg-muted/50'}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Github size={16} />
          <AlertTitle>GitHub Source</AlertTitle>
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          className="h-6 w-6 p-0" 
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </Button>
      </div>
      
      <AlertDescription className="mt-2 text-xs">
        {showDetails ? (
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="font-medium">Repository:</span>
              {repoUrl ? (
                <a 
                  href={repoUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline dark:text-blue-400"
                >
                  {source.repo_owner}/{source.repo_name}
                </a>
              ) : (
                <span>{source.repo_owner}/{source.repo_name}</span>
              )}
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Branch:</span>
              {branchUrl ? (
                <a 
                  href={branchUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline dark:text-blue-400"
                >
                  {displayBranch}
                </a>
              ) : (
                <span>{displayBranch}</span>
              )}
            </div>
            <div className="flex justify-between">
              <span className="font-medium">Patch Mode:</span>
              <span>{displayPatchMode}</span>
            </div>
            
            {hasFileErrors && (
              <div className="mt-2 pt-2 border-t border-amber-200">
                <div className="font-medium text-amber-700 mb-1">File Access Issues:</div>
                <Badge variant="outline" className="bg-amber-100 text-amber-800 mb-1">
                  {Object.keys(fileErrors).length} files with errors
                </Badge>
                <div className="text-xs text-amber-700">
                  The system is having trouble accessing files from this repository.
                  This may cause generic responses from the LLM.
                </div>
              </div>
            )}
            
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="font-medium mb-1">Test File Access:</div>
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  value={testFileName}
                  onChange={(e) => setTestFileName(e.target.value)}
                  placeholder="Enter file path (e.g., GraphRAG.py)"
                  className="flex-1 px-2 py-1 text-xs border rounded"
                />
                <Button 
                  size="sm" 
                  className="h-7 text-xs" 
                  onClick={handleTestFileAccess}
                  disabled={testingFile || !testFileName}
                >
                  {testingFile ? 'Testing...' : 'Test'}
                </Button>
              </div>
              
              {testFileResult && (
                <div className={`mt-2 p-2 rounded text-xs ${testFileResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                  <div className="flex items-center gap-1">
                    {testFileResult.success ? 
                      <Check size={12} className="text-green-500" /> : 
                      <FileWarning size={12} className="text-red-500" />
                    }
                    <span>{testFileResult.message}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <span>
              {source.repo_owner}/{source.repo_name} ({displayBranch})
            </span>
            {hasFileErrors && (
              <Badge variant="outline" className="bg-amber-100 text-amber-800">
                {Object.keys(fileErrors).length} file errors
              </Badge>
            )}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
};

export default GitHubSourceInfo;