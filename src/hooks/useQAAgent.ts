
import { useState } from 'react';
import { TestResult } from '../types/ticket';
import { AgentStatus } from './useDashboardState';

export function useQAAgent() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [testResults, setTestResults] = useState<TestResult[] | undefined>(undefined);

  const simulateWork = (onComplete: () => void, mockResults: TestResult[]) => {
    setStatus('working');
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStatus('success');
          setTestResults(mockResults);
          onComplete();
          return 100;
        }
        return Math.min(prev + 5, 100);
      });
    }, 100);
  };

  const simulateFailure = (onComplete: () => void) => {
    setStatus('working');
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStatus('error');
          
          // Create mock failed tests
          const failedResults: TestResult[] = [
            {
              name: 'Integration test',
              status: 'fail',
              duration: 423,
              errorMessage: 'Expected result to be equal to expected value'
            },
            {
              name: 'Unit test',
              status: 'fail',
              duration: 117,
              errorMessage: 'Cannot read property of undefined'
            }
          ];
          
          setTestResults(failedResults);
          onComplete();
          return 100;
        }
        return Math.min(prev + 5, 100);
      });
    }, 100);
  };

  const reset = () => {
    setStatus('idle');
    setProgress(0);
    setTestResults(undefined);
  };

  return {
    status,
    progress,
    testResults,
    simulateWork,
    simulateFailure,
    reset
  };
}
