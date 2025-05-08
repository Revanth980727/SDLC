
import React from 'react';
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Ticket } from "@/types/ticket";
import { CalendarClock, AlertTriangle, BarChart } from 'lucide-react';
import { format } from 'date-fns';
import { EscalationBadge } from './EscalationBadge';
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Progress } from "@/components/ui/progress";

interface TicketInfoProps {
  ticket: Ticket | null;
  className?: string;
}

const getPriorityColor = (priority: string): string => {
  switch (priority.toLowerCase()) {
    case "high":
      return "bg-red-500";
    case "medium":
      return "bg-yellow-500";
    case "low":
      return "bg-green-500";
    default:
      return "bg-blue-500";
  }
};

const getStatusColor = (status: string): string => {
  const statusLower = status.toLowerCase();
  if (statusLower.includes("completed") || statusLower.includes("done")) {
    return "bg-green-500 hover:bg-green-600";
  }
  if (statusLower.includes("error") || statusLower.includes("fail")) {
    return "bg-red-500 hover:bg-red-600";
  }
  if (statusLower.includes("progress") || statusLower.includes("processing")) {
    return "bg-blue-500 hover:bg-blue-600";
  }
  if (statusLower.includes("escalated") || statusLower.includes("review")) {
    return "bg-amber-500 hover:bg-amber-600";
  }
  return "bg-gray-500 hover:bg-gray-600";
};

const getConfidenceColor = (score: number | undefined): string => {
  if (score === undefined) return "";
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  return "text-red-500";
};

export function TicketInfo({ ticket, className = "" }: TicketInfoProps) {
  // If no ticket data is available, show empty card with a message
  if (!ticket) {
    return (
      <Card className={`${className}`}>
        <CardContent className="p-4">
          <div className="text-center py-4 text-muted-foreground">
            <p>No ticket selected</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const statusColor = getStatusColor(ticket.status);
  const priorityColor = getPriorityColor(ticket.priority);
  const isEscalated = ticket.escalated || ticket.status?.toLowerCase()?.includes('escalated');
  const isEarlyEscalation = isEscalated && (ticket.current_attempt || 0) < (ticket.max_attempts || 4);
  
  const formattedDate = ticket.updated ? format(new Date(ticket.updated), 'MMM d, yyyy h:mm a') : '';

  const retryPercentage = ticket.max_attempts 
    ? Math.min((ticket.current_attempt || 0) / ticket.max_attempts * 100, 100) 
    : 0;

  return (
    <Card className={`${className}`}>
      <CardContent className="p-4">
        {isEscalated && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {isEarlyEscalation 
                ? `This ticket has been escalated early ${ticket.escalation_reason ? 
                    `due to: ${ticket.escalation_reason}` : 
                    "for human review due to complexity factors"}`
                : "This ticket has been escalated for human review after multiple fix attempts failed"}
            </AlertDescription>
          </Alert>
        )}
        
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <div>
            <h2 className="text-xl font-semibold">{ticket.title || ticket.id}</h2>
            <div className="flex items-center text-xs text-muted-foreground gap-1 mt-1">
              <CalendarClock className="h-3 w-3" />
              <span>{formattedDate}</span>
            </div>
          </div>
          
          <div className="flex flex-wrap gap-2">
            {isEscalated && (
              <EscalationBadge 
                isEarly={isEarlyEscalation} 
                retryCount={ticket.current_attempt} 
                maxRetries={ticket.max_attempts}
                reason={ticket.escalation_reason}
                confidenceScore={ticket.confidence_score}
              />
            )}
            
            {/* Show confidence score if available */}
            {!isEscalated && ticket.confidence_score !== undefined && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge 
                      variant="outline" 
                      className={`flex items-center space-x-1 ${getConfidenceColor(ticket.confidence_score)}`}
                    >
                      <BarChart className="h-3 w-3 mr-1" />
                      <span>Confidence: {ticket.confidence_score}%</span>
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <div className="space-y-1 w-40">
                      <p className="text-xs">
                        {ticket.confidence_score >= 80 
                          ? "High confidence in this fix" 
                          : (ticket.confidence_score >= 60 
                              ? "Medium confidence in this fix" 
                              : "Low confidence in this fix")}
                      </p>
                      <Progress 
                        value={ticket.confidence_score} 
                        className="h-1" 
                      />
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge 
                    variant={isEscalated ? "destructive" : "outline"} 
                    className="flex items-center space-x-1"
                  >
                    <span>Attempt:</span>
                    <span>{ticket.current_attempt || 0}/{ticket.max_attempts || 4}</span>
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="space-y-1 w-48">
                    <p className="text-xs">
                      Retry progress: {ticket.current_attempt || 0} of {ticket.max_attempts || 4} attempts used
                    </p>
                    <Progress value={retryPercentage} className="h-1" />
                    {ticket.retry_history && ticket.retry_history.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <p className="text-xs font-medium">Attempt history:</p>
                        <ul className="text-xs space-y-1">
                          {ticket.retry_history.map((entry, idx) => (
                            <li key={idx} className="text-xs">
                              #{idx+1}: {entry.result === 'success' ? '✅' : '❌'} 
                              {entry.qa_message ? ` - ${entry.qa_message.substring(0, 30)}...` : ''}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            {ticket.priority && (
              <Badge className={`${priorityColor} text-white`}>
                {ticket.priority}
              </Badge>
            )}
            
            <Badge className={`${statusColor} text-white`}>
              {ticket.status}
            </Badge>
          </div>
        </div>
        
        {ticket.description && (
          <div className="mt-4 text-sm text-muted-foreground">
            <p>{ticket.description}</p>
          </div>
        )}
        
        {/* Show confidence visualization when available */}
        {ticket.confidence_score !== undefined && (
          <div className="mt-4 border-t pt-3">
            <div className="flex justify-between items-center mb-1 text-xs">
              <span className="text-muted-foreground flex items-center">
                <BarChart className="h-3 w-3 mr-1" />
                Developer confidence score:
              </span>
              <span className={getConfidenceColor(ticket.confidence_score)}>
                {ticket.confidence_score}%
              </span>
            </div>
            <Progress 
              value={ticket.confidence_score} 
              className={`h-1 ${
                ticket.confidence_score < 60 ? "bg-red-500" : 
                (ticket.confidence_score >= 80 ? "bg-green-500" : "bg-yellow-500")
              }`}
            />
            {ticket.confidence_score < 60 && ticket.current_attempt === 1 && (
              <p className="text-xs text-red-500 mt-1">
                Low confidence scores may trigger early escalation.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
