
import React, { ReactNode } from 'react';
import { AgentStatus } from './AgentStatus';
import { cn } from '@/lib/utils';
import { AgentStatus as AgentStatusType } from '@/hooks/useDashboardState';

type AgentType = 'planner' | 'developer' | 'qa' | 'communicator';

interface AgentCardProps {
  title: string;
  type: AgentType;
  status: AgentStatusType;
  progress?: number;
  children: ReactNode;
}

export function AgentCard({ title, type, status, progress, children }: AgentCardProps) {
  const borderColorClasses = {
    planner: 'border-agent-planner',
    developer: 'border-agent-developer',
    qa: 'border-agent-qa',
    communicator: 'border-agent-communicator',
  };

  return (
    <div className={cn(
      "rounded-md border border-border overflow-hidden transition-all duration-200",
      status === 'working' && `border-t-2 ${borderColorClasses[type]}`
    )}>
      <div className="bg-card p-4 border-b border-border flex justify-between items-center">
        <h3 className="font-semibold">{title} Agent</h3>
        <AgentStatus type={type} status={status} progress={progress} />
      </div>
      <div className="p-4 bg-background">
        {children}
      </div>
    </div>
  );
}
