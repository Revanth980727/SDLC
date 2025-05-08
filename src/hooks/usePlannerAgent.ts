
import { useState } from 'react';
import { PlannerAnalysis } from '../types/ticket';
import { AgentStatus } from './useDashboardState';

export function usePlannerAgent() {
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [analysis, setAnalysis] = useState<PlannerAnalysis | undefined>(undefined);

  const simulateWork = (onComplete: () => void, mockAnalysis: PlannerAnalysis) => {
    setStatus('working');
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStatus('success');
          setAnalysis(mockAnalysis);
          onComplete();
          return 100;
        }
        return Math.min(prev + 1, 100);
      });
    }, 100);
  };

  // Add a function to simulate fallbacks for testing
  const simulateWorkWithFallback = (onComplete: () => void) => {
    setStatus('working');
    
    // Create fallback analysis
    const fallbackAnalysis: PlannerAnalysis = {
      ticket_id: "FALLBACK-123",
      bug_summary: "First sentence of the description. Second sentence of the description.",
      affected_files: [],
      error_type: "Unknown",
      using_fallback: true
    };
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setStatus('success');
          setAnalysis(fallbackAnalysis);
          onComplete();
          return 100;
        }
        return Math.min(prev + 1, 100);
      });
    }, 100);
  };

  // Add function to validate that analysis is complete
  const validateAnalysis = (analysis: PlannerAnalysis): boolean => {
    return !!(
      analysis.ticket_id &&
      analysis.bug_summary &&
      analysis.affected_files &&
      analysis.error_type
    );
  };

  const reset = () => {
    setStatus('idle');
    setProgress(0);
    setAnalysis(undefined);
  };

  return {
    status,
    progress,
    analysis,
    simulateWork,
    simulateWorkWithFallback,
    validateAnalysis,
    reset
  };
}