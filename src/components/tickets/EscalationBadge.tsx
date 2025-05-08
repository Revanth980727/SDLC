
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, BarChartIcon } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';

interface EscalationBadgeProps {
  className?: string;
  reason?: string;
  retryCount?: number;
  maxRetries?: number;
  isEarly?: boolean;
  confidenceScore?: number;
}

export function EscalationBadge({ 
  className = '', 
  reason, 
  retryCount, 
  maxRetries, 
  isEarly = false,
  confidenceScore
}: EscalationBadgeProps) {
  // Helper function to get confidence level text
  const getConfidenceText = (score?: number) => {
    if (score === undefined) return "";
    if (score >= 80) return "High confidence";
    if (score >= 60) return "Medium confidence";
    return "Low confidence";
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge 
            variant="destructive" 
            className={`flex items-center gap-1 ${className} ${isEarly ? "animate-pulse" : ""}`}
          >
            <AlertTriangle className="h-3 w-3" />
            <span>{isEarly ? "Early Escalation" : "Escalated"}</span>
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="w-80 p-4">
          <div className="space-y-3">
            <p className="font-semibold text-lg">Ticket Escalated</p>
            
            {isEarly ? (
              <div className="bg-red-50 dark:bg-red-900/10 p-2 rounded-md border border-red-200 dark:border-red-900">
                <p className="text-sm font-medium text-red-600 dark:text-red-400">
                  Early escalation triggered
                </p>
              </div>
            ) : null}
            
            <p className="text-sm">
              {reason || 
                (isEarly 
                  ? "This ticket was escalated early for human review due to complexity or risk factors."
                  : "This ticket has been escalated for human review after multiple fix attempts failed."
                )
              }
            </p>
            
            {retryCount !== undefined && maxRetries !== undefined && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span>Attempts:</span>
                  <span>{retryCount}/{maxRetries}</span>
                </div>
                <Progress value={(retryCount / maxRetries) * 100} className="h-1" />
              </div>
            )}
            
            {confidenceScore !== undefined && (
              <div className="space-y-1 mt-2">
                <div className="flex justify-between text-xs items-center">
                  <div className="flex items-center gap-1">
                    <BarChartIcon className="h-3 w-3" />
                    <span>Confidence Score:</span>
                  </div>
                  <span className={
                    confidenceScore < 60 ? "text-red-500 font-medium" : 
                    (confidenceScore >= 80 ? "text-green-500 font-medium" : "text-yellow-500 font-medium")
                  }>
                    {confidenceScore}% ({getConfidenceText(confidenceScore)})
                  </span>
                </div>
                <Progress 
                  value={confidenceScore} 
                  className={`h-1 ${
                    confidenceScore < 60 ? "bg-red-500" : 
                    (confidenceScore >= 80 ? "bg-green-500" : "bg-yellow-500")
                  }`}
                />
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
