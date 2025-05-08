import React, { useState } from 'react';
import { TicketForm } from '../tickets/TicketForm';
import { TicketInfo } from '../tickets/TicketInfo';
import { PlannerAgent } from '../agents/PlannerAgent';
import DeveloperAgent from '../agents/DeveloperAgent';
import { QAAgent } from '../agents/QAAgent';
import { CommunicatorAgent } from '../agents/CommunicatorAgent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useDashboardState } from '@/hooks/useDashboardState';
import { TicketsList } from '../tickets/TicketsList';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Filter } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { toast } from '@/components/ui/sonner';
import { Loading } from '@/components/ui/loading';

export function Dashboard() {
  const [view, setView] = useState<'current' | 'list'>('current');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  
  const { resolvedTheme, setTheme } = useTheme();
  
  const {
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
  } = useDashboardState();

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Tabs value={view} onValueChange={(v) => setView(v as 'current' | 'list')} className="w-[400px]">
          <TabsList>
            <TabsTrigger value="current">Current Ticket</TabsTrigger>
            <TabsTrigger value="list">Tickets List</TabsTrigger>
          </TabsList>
        </Tabs>
        
        <div className="flex items-center space-x-2">
          <Switch 
            id="theme-mode" 
            checked={resolvedTheme === 'dark'} 
            onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
          />
          <Label htmlFor="theme-mode">Dark Mode</Label>
        </div>
      </div>
      
      <Tabs value={view} onValueChange={(v) => setView(v as 'current' | 'list')} className="mt-0">
        <TabsContent value="current">
          <div className="grid gap-6 md:grid-cols-2">
            <TicketForm onSubmit={handleTicketSubmit} isProcessing={isProcessing} />
            <TicketInfo ticket={activeTicket} />
          </div>
          
          <Separator className="my-6" />
          
          {/* We'll adjust this to handle null activeTicket properly */}
          {!activeTicket ? (
            <div className="text-center py-10 text-muted-foreground">
              <p>Enter a JIRA ticket ID above to start fixing a bug,</p>
              <p>or select a ticket from the Tickets List tab.</p>
            </div>
          ) : (
            <>
              <div className="grid gap-6 md:grid-cols-2">
                <PlannerAgent 
                  status={plannerStatus} 
                  progress={plannerProgress}
                  analysis={plannerAnalysis}
                />
                
                <DeveloperAgent 
                  onStart={() => console.log('Developer started')}
                  onComplete={() => console.log('Developer completed')}
                />
              </div>
              
              <div className="grid gap-6 md:grid-cols-2 mt-6">
                <QAAgent 
                  status={qaStatus} 
                  progress={qaProgress}
                  testResults={testResults}
                  summary={testResults ? {
                    total: testResults.length,
                    passed: testResults.filter(t => t.status === 'pass').length,
                    failed: testResults.filter(t => t.status === 'fail').length,
                    duration: testResults.reduce((acc, curr) => acc + curr.duration, 0)
                  } : undefined}
                />
                
                <CommunicatorAgent 
                  status={communicatorStatus} 
                  progress={communicatorProgress}
                  updates={updates}
                  prUrl={updates && updates.length > 0 ? "https://github.com/org/repo/pull/45" : undefined}
                  jiraUrl={activeTicket ? `https://jira.company.com/browse/${activeTicket.id}` : undefined}
                />
              </div>
            </>
          )}
        </TabsContent>
        
        <TabsContent value="list">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle>Tickets</CardTitle>
              <div className="flex space-x-2">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search tickets..."
                    className="pl-8 w-[200px]"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <div className="relative">
                  <Filter className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <select
                    className="h-10 pl-8 pr-4 rounded-md border border-input bg-background text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    value={filterStatus || ''}
                    onChange={(e) => setFilterStatus(e.target.value || null)}
                  >
                    <option value="">All Status</option>
                    <option value="planning">Planning</option>
                    <option value="development">Development</option>
                    <option value="qa">QA</option>
                    <option value="pr-opened">PR Opened</option>
                    <option value="escalated">Escalated</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoadingTickets ? (
                <Loading message="Loading tickets..." className="py-10" />
              ) : (
                <div className="space-y-4">
                  <TicketsList 
                    tickets={ticketsList} 
                    onSelectTicket={selectTicket}
                    selectedTicketId={selectedTicketId}
                    isLoading={isLoadingTickets}
                    searchQuery={searchQuery}
                    filterStatus={filterStatus}
                  />
                  {ticketsList.length > 0 && (
                    <div className="flex justify-end">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => fetchTickets()}
                      >
                        Refresh
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}