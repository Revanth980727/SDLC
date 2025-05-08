import React from 'react';
import { AgentCard } from './AgentCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentStatus } from '@/hooks/useDashboardState';
import { TestResult } from '@/types/ticket';

interface QAAgentProps {
  status: AgentStatus;
  progress?: number;
  testResults?: TestResult[];
  summary?: {
    total: number;
    passed: number;
    failed: number;
    duration: number;
  };
}

export function QAAgent({ status, progress, testResults, summary }: QAAgentProps) {
  return (
    <AgentCard title="QA" type="qa" status={status} progress={progress}>
      {status === 'idle' && (
        <div className="text-muted-foreground">
          Waiting for developer to provide a fix...
        </div>
      )}
      
      {status === 'working' && !testResults && (
        <div className="space-y-2">
          <p>Running tests to validate the fix...</p>
          <div className="h-4 w-full bg-muted overflow-hidden rounded">
            <div 
              className="h-full bg-agent-qa transition-all duration-300" 
              style={{ width: `${progress || 0}%` }} 
            />
          </div>
        </div>
      )}
      
      {testResults && testResults.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            {summary && (
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                  <span>{summary.passed} passed</span>
                </div>
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-red-500 rounded-full mr-1"></div>
                  <span>{summary.failed} failed</span>
                </div>
                <div className="text-muted-foreground">
                  {summary.duration}ms
                </div>
              </div>
            )}
            <div className={cn(
              "text-sm font-medium",
              status === 'success' ? "text-green-500" : "text-red-500"
            )}>
              {status === 'success' ? 'All tests passed' : 'Tests failing'}
            </div>
          </div>
          
          <ScrollArea className="h-[200px]">
            <div className="space-y-2">
              {testResults.map((test, index) => (
                <div 
                  key={index} 
                  className={cn(
                    "p-2 rounded-md text-sm flex items-start gap-2",
                    test.status === 'pass' ? "bg-green-500/10" : "bg-red-500/10"
                  )}
                >
                  {test.status === 'pass' ? (
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="flex justify-between">
                      <span className="font-medium">{test.name}</span>
                      <span className="text-muted-foreground text-xs">{test.duration}ms</span>
                    </div>
                    {test.errorMessage && (
                      <pre className="mt-1 text-xs bg-muted p-2 rounded-sm overflow-x-auto text-red-400">
                        {test.errorMessage}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}
    </AgentCard>
  );
}
