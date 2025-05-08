
import React from 'react';
import { AgentCard } from './AgentCard';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { GitPullRequest, MessageSquare, Github, AlertTriangle, Info, RefreshCcw, CheckCircle, XCircle } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { AgentStatus } from '@/hooks/useDashboardState';
import { Update } from '@/types/ticket';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface ValidationMetrics {
  totalPatches?: number;
  validPatches?: number;
  rejectedPatches?: number;
  rejectionReasons?: Record<string, number>;
}

interface CommunicatorAgentProps {
  status: AgentStatus;
  progress?: number;
  updates?: Update[];
  prUrl?: string;
  jiraUrl?: string;
  earlyEscalation?: boolean;
  escalationReason?: string;
  confidenceScore?: number;
  retryCount?: number;
  maxRetries?: number;
  patchValidationResults?: {
    isValid: boolean;
    rejectionReason?: string;
    validationMetrics?: ValidationMetrics;
  };
}

export function CommunicatorAgent({ 
  status, 
  progress, 
  updates, 
  prUrl, 
  jiraUrl,
  earlyEscalation,
  escalationReason,
  confidenceScore,
  retryCount = 0,
  maxRetries = 4,
  patchValidationResults
}: CommunicatorAgentProps) {
  const { toast } = useToast();
  
  const handleButtonClick = (url: string, type: string) => {
    if (url) {
      window.open(url, '_blank');
    } else {
      toast({
        title: `No ${type} URL available`,
        description: `The ${type} URL is not available for this ticket.`,
        variant: "destructive",
      });
    }
  };

  const isEscalated = earlyEscalation || (retryCount >= maxRetries);
  
  // Helper function to determine confidence badge color
  const getConfidenceBadgeVariant = (score?: number) => {
    if (score === undefined) return "outline";
    if (score >= 80) return "success";
    if (score >= 60) return "default";
    return "destructive";
  };
  
  // Helper function to get a descriptive label for the confidence score
  const getConfidenceLabel = (score?: number) => {
    if (score === undefined) return "Unknown";
    if (score >= 80) return "High";
    if (score >= 60) return "Medium";
    return "Low";
  };

  return (
    <AgentCard title="Communicator" type="communicator" status={status} progress={progress}>
      {retryCount > 0 && maxRetries > 0 && (
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RefreshCcw className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Attempt {retryCount}/{maxRetries}</span>
          </div>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Progress 
                  value={(retryCount / maxRetries) * 100} 
                  className={`h-2 w-24 ${retryCount >= maxRetries ? "bg-red-200" : ""}`}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p>Retry progress: {retryCount} of {maxRetries} attempts used</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}
      
      {confidenceScore !== undefined && (
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Confidence:</span>
          <Badge variant={getConfidenceBadgeVariant(confidenceScore)}>
            {getConfidenceLabel(confidenceScore)} ({confidenceScore}%)
          </Badge>
        </div>
      )}
      
      {patchValidationResults && (
        <div className={`mb-3 p-2 border ${patchValidationResults.isValid ? 'border-green-200 bg-green-50 dark:bg-green-950/30 dark:border-green-900' : 'border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900'} rounded-md flex items-start gap-2`}>
          {patchValidationResults.isValid ? (
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
          ) : (
            <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
          )}
          <div className="text-sm">
            <p className={`font-medium ${patchValidationResults.isValid ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}`}>
              {patchValidationResults.isValid ? 'Patch Validation Passed' : 'Patch Validation Failed'}
            </p>
            {!patchValidationResults.isValid && patchValidationResults.rejectionReason && (
              <p className="text-red-700 dark:text-red-400">
                {patchValidationResults.rejectionReason}
              </p>
            )}
            {patchValidationResults.validationMetrics && (
              <p className="text-xs mt-1">
                {patchValidationResults.validationMetrics.validPatches || 0}/{patchValidationResults.validationMetrics.totalPatches || 0} patches valid
              </p>
            )}
          </div>
        </div>
      )}
      
      {status === 'idle' && !updates && (
        <div className="text-muted-foreground">
          Waiting for QA results...
        </div>
      )}
      
      {status === 'working' && !updates && (
        <div className="space-y-2">
          <p>Updating JIRA and creating PR...</p>
          <div className="h-4 w-full bg-muted overflow-hidden rounded">
            <div 
              className="h-full bg-agent-communicator transition-all duration-300" 
              style={{ width: `${progress || 0}%` }} 
            />
          </div>
        </div>
      )}
      
      {isEscalated && (
        <div className="mb-3 p-2 border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 rounded-md flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-amber-800 dark:text-amber-300">
              {earlyEscalation ? "Early Escalation" : "Escalated after max retries"}
            </p>
            <p className="text-amber-700 dark:text-amber-400">
              {escalationReason || 
               (earlyEscalation ? "Ticket has been escalated early" : 
                `Maximum retry attempts (${maxRetries}) reached`)}
            </p>
            {confidenceScore !== undefined && confidenceScore < 60 && (
              <p className="text-xs mt-1">Confidence score: {confidenceScore}%</p>
            )}
          </div>
        </div>
      )}
      
      {updates && updates.length > 0 && (
        <div className="space-y-4">
          {(prUrl || jiraUrl) && (
            <div className="flex gap-2">
              {prUrl && (
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="flex items-center gap-1"
                  onClick={() => handleButtonClick(prUrl, 'PR')}
                >
                  <GitPullRequest className="h-4 w-4" />
                  View PR
                </Button>
              )}
              {jiraUrl && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="flex items-center gap-1"
                  onClick={() => handleButtonClick(jiraUrl, 'JIRA')}
                >
                  <MessageSquare className="h-4 w-4" />
                  JIRA Ticket
                </Button>
              )}
            </div>
          )}
          
          <Separator />
          
          <ScrollArea className="h-[150px]">
            {updates.map((update, index) => {
              const iconColor = 
                update.type === 'jira' ? 'text-blue-400' : 
                update.type === 'github' ? 'text-purple-400' : 
                update.type === 'system' ? 'text-amber-400' :
                'text-gray-400';
              
              const icon = 
                update.type === 'jira' ? <MessageSquare className="h-4 w-4" /> : 
                update.type === 'github' ? <Github className="h-4 w-4" /> : 
                update.type === 'system' ? <Info className="h-4 w-4" /> :
                '💬';
              
              // Check if message contains certain keywords
              const isEscalationMessage = update.message.includes('escalat') || 
                                         update.message.includes('human review');
                                         
              const isValidationMessage = update.message.includes('Patch validation');
              
              // Determine message style
              let textStyle = "";
              if (isEscalationMessage) {
                textStyle = "text-amber-600 dark:text-amber-400";
              } else if (isValidationMessage && update.message.includes('failed')) {
                textStyle = "text-red-600 dark:text-red-400";
              } else if (isValidationMessage && update.message.includes('passed')) {
                textStyle = "text-green-600 dark:text-green-400";
              }
                                         
              return (
                <div key={index} className="flex gap-2 mb-2 text-sm">
                  <div className="text-muted-foreground text-xs whitespace-nowrap">
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </div>
                  <div className={`${iconColor} w-4 flex-shrink-0`}>
                    {icon}
                  </div>
                  <div className="flex-1">
                    <div className={textStyle}>
                      {update.message}
                      
                      {update.confidenceScore !== undefined && (
                        <Badge 
                          variant={getConfidenceBadgeVariant(update.confidenceScore)} 
                          className="ml-1 text-xs"
                        >
                          {update.confidenceScore}%
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </ScrollArea>
        </div>
      )}
      
      {status === 'success' && (
        <div className="text-green-500 text-sm pt-2">
          All updates completed successfully.
        </div>
      )}
      
      {status === 'error' && (
        <div className="text-red-500 text-sm pt-2">
          Failed to complete some updates. Check logs for details.
        </div>
      )}
    </AgentCard>
  );
}