
import { useState, useEffect, useCallback } from 'react';
import { Ticket, PlannerAnalysis, CodeDiff, TestResult, Update, AffectedFile } from '@/types/ticket';
import { api } from '@/services/api';
import { toast } from '@/components/ui/sonner';

export type AgentStatus = 'idle' | 'working' | 'success' | 'error' | 'waiting' | 'escalated';

export interface TicketListItem {
  id: string;
  title: string;
  status: string;
  stage: string;
  priority?: string;
  updatedAt: string;
  escalated?: boolean;
  retryCount?: number;
  maxRetries?: number;
}

export const useDashboardState = () => {
  // Active ticket state
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [activeTicket, setActiveTicket] = useState<Ticket | null>(null);
  
  // Agent statuses
  const [plannerStatus, setPlannerStatus] = useState<AgentStatus>('idle');
  const [developerStatus, setDeveloperStatus] = useState<AgentStatus>('idle');
  const [qaStatus, setQaStatus] = useState<AgentStatus>('idle');
  const [communicatorStatus, setCommunicatorStatus] = useState<AgentStatus>('idle');
  
  // Agent progress (0-100)
  const [plannerProgress, setPlannerProgress] = useState<number>(0);
  const [developerProgress, setDeveloperProgress] = useState<number>(0);
  const [qaProgress, setQaProgress] = useState<number>(0);
  const [communicatorProgress, setCommunicatorProgress] = useState<number>(0);
  
  // Agent outputs
  const [plannerAnalysis, setPlannerAnalysis] = useState<PlannerAnalysis | undefined>(undefined);
  const [diffs, setDiffs] = useState<CodeDiff[] | undefined>(undefined);
  const [testResults, setTestResults] = useState<TestResult[] | undefined>(undefined);
  const [updates, setUpdates] = useState<Update[] | undefined>(undefined);
  
  // Retry information
  const [currentAttempt, setCurrentAttempt] = useState<number>(0);
  const [maxAttempts, setMaxAttempts] = useState<number>(4);
  
  // Escalation state
  const [isEscalated, setIsEscalated] = useState<boolean>(false);
  
  // Tickets list
  const [ticketsList, setTicketsList] = useState<TicketListItem[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState<boolean>(false);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  // Reset all agent states
  const resetAgentStates = useCallback(() => {
    setPlannerStatus('idle');
    setDeveloperStatus('idle');
    setQaStatus('idle');
    setCommunicatorStatus('idle');
    
    setPlannerProgress(0);
    setDeveloperProgress(0);
    setQaProgress(0);
    setCommunicatorProgress(0);
    
    setPlannerAnalysis(undefined);
    setDiffs(undefined);
    setTestResults(undefined);
    setUpdates(undefined);
    
    setCurrentAttempt(0);
    setIsEscalated(false);
  }, []);

  // Fetch ticket details
  const fetchTicketDetails = useCallback(async (ticketId: string) => {
    try {
      const details = await api.getTicketDetails(ticketId);
      if (!details) return;
      
      // Update active ticket info
      setActiveTicket(details.ticket);
      setSelectedTicketId(ticketId);
      
      // Update escalation status
      setIsEscalated(details.escalated || false);
      
      // Update retry counts
      setCurrentAttempt(details.retryCount || 0);
      setMaxAttempts(details.maxRetries || 4);
      
      // Update agent statuses based on current stage
      switch (details.currentStage) {
        case 'planning':
          setPlannerStatus('working');
          setDeveloperStatus('idle');
          setQaStatus('idle');
          setCommunicatorStatus('idle');
          break;
        case 'development':
          setPlannerStatus('success');
          setDeveloperStatus('working');
          setQaStatus('idle');
          setCommunicatorStatus('idle');
          break;
        case 'qa':
          setPlannerStatus('success');
          setDeveloperStatus('success');
          setQaStatus('working');
          setCommunicatorStatus('idle');
          break;
        case 'communicating':
          setPlannerStatus('success');
          setDeveloperStatus('success');
          setQaStatus('success');
          setCommunicatorStatus('working');
          break;
        case 'completed':
          setPlannerStatus('success');
          setDeveloperStatus('success');
          setQaStatus('success');
          setCommunicatorStatus('success');
          break;
        case 'escalated':
          // Set relevant agent to error status
          if (details.agentOutputs.planner) {
            setPlannerStatus('success');
            if (details.agentOutputs.developer) {
              setDeveloperStatus(details.agentOutputs.qa ? 'success' : 'escalated');
              setQaStatus(details.agentOutputs.qa ? 'escalated' : 'idle');
            } else {
              setDeveloperStatus('escalated');
            }
          } else {
            setPlannerStatus('escalated');
          }
          setCommunicatorStatus('escalated');
          break;
      }
      
      // Update agent outputs
      if (details.agentOutputs.planner) {
        const plannerOutput = details.agentOutputs.planner;
        
        // Handle both old and new format for affected files
        let affectedFiles: string[] | AffectedFile[] = [];
        
        // Check if plannerOutput has affected_files or affectedFiles property
        if (plannerOutput && 'affected_files' in plannerOutput && Array.isArray(plannerOutput.affected_files)) {
          // New format
          affectedFiles = plannerOutput.affected_files;
        } else if (plannerOutput && 'affectedFiles' in plannerOutput && Array.isArray(plannerOutput.affectedFiles)) {
          // Old format
          affectedFiles = plannerOutput.affectedFiles;
        }
        
        // Create base planner analysis object
        const plannerAnalysis: PlannerAnalysis = {
          ticket_id: details.ticket.id || '',
          bug_summary: '',  // Will be set below
          affected_files: affectedFiles,
          error_type: 'Unknown',  // Will be updated below if available
          affectedFiles: plannerOutput.affectedFiles || [],
          rootCause: plannerOutput.rootCause || '',
          suggestedApproach: plannerOutput.suggestedApproach || ''
        };
        
        // Set bug_summary from either bug_summary or rootCause
        if ('bug_summary' in plannerOutput) {
          plannerAnalysis.bug_summary = plannerOutput.bug_summary as string;
        } else if (plannerOutput.rootCause) {
          plannerAnalysis.bug_summary = plannerOutput.rootCause;
        }
        
        // Set error_type if available
        if ('error_type' in plannerOutput) {
          plannerAnalysis.error_type = plannerOutput.error_type as string;
        } else if ('errorType' in plannerOutput && typeof plannerOutput.errorType === 'string') {
          plannerAnalysis.error_type = plannerOutput.errorType;
        }
        
        setPlannerAnalysis(plannerAnalysis);
        setPlannerProgress(100);
      }
      
      if (details.agentOutputs.developer) {
        setDiffs(details.agentOutputs.developer.diffs || []);
        setCurrentAttempt(details.agentOutputs.developer.attempt);
        setDeveloperProgress(100);
      }
      
      if (details.agentOutputs.qa) {
        setTestResults(details.agentOutputs.qa.testResults || []);
        setQaProgress(100);
      }
      
      if (details.agentOutputs.communicator) {
        setUpdates(details.agentOutputs.communicator.updates || []);
        setCommunicatorProgress(100);
      }
      
    } catch (error) {
      console.error('Error fetching ticket details:', error);
    }
  }, []);

  // Fetch list of tickets
  const fetchTickets = useCallback(async () => {
    if (isLoadingTickets) return;
    
    try {
      setIsLoadingTickets(true);
      const tickets = await api.getTickets();
      
      // Transform tickets to TicketListItem format
      const ticketItems: TicketListItem[] = tickets.map(ticket => ({
        id: ticket.id,
        title: ticket.title,
        status: ticket.status,
        stage: getStageFromStatus(ticket.status),
        priority: ticket.priority,
        updatedAt: ticket.updated || '',
        escalated: ticket.escalated || false,
        retryCount: ticket.current_attempt || 0,
        maxRetries: ticket.max_attempts || 4
      }));
      
      setTicketsList(ticketItems);
      
      // If we have a selected ticket, refresh its details
      if (selectedTicketId) {
        fetchTicketDetails(selectedTicketId);
      }
      
      setIsLoadingTickets(false);
      console.info('Polling for ticket updates...');
    } catch (error) {
      setIsLoadingTickets(false);
      console.error('Error fetching tickets:', error);
    }
  }, [isLoadingTickets, selectedTicketId, fetchTicketDetails]);

  // Handle ticket selection
  const selectTicket = useCallback((ticketId: string) => {
    setSelectedTicketId(ticketId);
    fetchTicketDetails(ticketId);
  }, [fetchTicketDetails]);

  // Handle ticket submission
  const handleTicketSubmit = useCallback(async (ticketId: string) => {
    try {
      setIsProcessing(true);
      resetAgentStates();
      
      const response = await api.startFix(ticketId);
      if (!response) {
        toast.error('Failed to start bug fix process');
        setIsProcessing(false);
        return;
      }
      
      toast.success(`Started bug fix for ${ticketId}`);
      
      // Now fetch the details
      fetchTicketDetails(ticketId);
      
      // Also refresh the ticket list
      fetchTickets();
      
      setIsProcessing(false);
    } catch (error) {
      setIsProcessing(false);
      toast.error(`Error starting fix: ${(error as Error).message}`);
    }
  }, [resetAgentStates, fetchTicketDetails, fetchTickets]);

  // Poll for updates every 10 seconds
  useEffect(() => {
    fetchTickets();
    
    const intervalId = setInterval(() => {
      fetchTickets();
    }, 10000);
    
    return () => clearInterval(intervalId);
  }, [fetchTickets]);

  return {
    isProcessing,
    activeTicket,
    plannerStatus,
    developerStatus,
    qaStatus,
    communicatorStatus,
    plannerProgress,
    developerProgress,
    qaProgress,
    communicatorProgress,
    plannerAnalysis,
    diffs,
    testResults,
    updates,
    handleTicketSubmit,
    ticketsList,
    fetchTickets,
    selectTicket,
    isLoadingTickets,
    selectedTicketId,
    currentAttempt,
    maxAttempts,
    isEscalated
  };
};

// Helper function to map ticket status to stage
function getStageFromStatus(status: string): string {
  const lowerStatus = status.toLowerCase();
  
  if (lowerStatus.includes('planning') || lowerStatus === 'open') {
    return 'planning';
  } else if (lowerStatus.includes('develop')) {
    return 'development';
  } else if (lowerStatus.includes('test') || lowerStatus.includes('qa')) {
    return 'qa';
  } else if (lowerStatus.includes('review') || lowerStatus.includes('pr')) {
    return 'communicating';
  } else if (lowerStatus.includes('done') || lowerStatus.includes('complete')) {
    return 'completed';
  } else if (lowerStatus.includes('escalat')) {
    return 'escalated';
  }
  
  return 'planning'; // Default
}
