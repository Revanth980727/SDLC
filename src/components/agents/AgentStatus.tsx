
import React from 'react';
import { cn } from '@/lib/utils';
import { AgentStatus as AgentStatusType } from '@/hooks/useDashboardState';

type AgentType = 'planner' | 'developer' | 'qa' | 'communicator';

interface AgentStatusProps {
  type: AgentType;
  status: AgentStatusType;
  progress?: number;
}

export function AgentStatus({ type, status, progress = 0 }: AgentStatusProps) {
  const agentColors = {
    planner: 'bg-agent-planner',
    developer: 'bg-agent-developer',
    qa: 'bg-agent-qa',
    communicator: 'bg-agent-communicator',
  };

  const statusClasses = {
    idle: 'bg-muted',
    working: cn(agentColors[type], 'animate-pulse-opacity'),
    success: 'bg-green-600',
    error: 'bg-red-600',
    waiting: 'bg-yellow-600',
    escalated: 'bg-purple-600',
  };

  const statusText = {
    idle: 'Idle',
    working: 'Working',
    success: 'Success',
    error: 'Error',
    waiting: 'Waiting',
    escalated: 'Escalated',
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <div className={cn("h-3 w-3 rounded-full", statusClasses[status])} />
      <span>{statusText[status]}</span>
      {status === 'working' && progress > 0 && (
        <span className="text-xs text-muted-foreground">({progress}%)</span>
      )}
    </div>
  );
}
