
import React from 'react';
import { 
  Table, 
  TableHeader, 
  TableRow, 
  TableHead, 
  TableBody, 
  TableCell 
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TicketListItem } from "@/hooks/useDashboardState";
import { format } from 'date-fns';
import { AlertTriangle, Clock, RefreshCcw } from 'lucide-react';
import { EscalationBadge } from './EscalationBadge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';

interface TicketsListProps {
  tickets: TicketListItem[];
  selectedTicketId?: string | null; 
  onSelectTicket?: (ticketId: string) => void;
  isLoading?: boolean;
  searchQuery?: string;
  filterStatus?: string | null;
}

export function TicketsList({ 
  tickets, 
  selectedTicketId, 
  onSelectTicket,
  isLoading = false,
  searchQuery = '',
  filterStatus = null
}: TicketsListProps) {
  // Function to determine status badge color
  const getStatusColor = (status: string): string => {
    const lowerStatus = status.toLowerCase();
    
    if (lowerStatus.includes('complete') || lowerStatus.includes('done')) {
      return 'bg-green-500 hover:bg-green-600';
    } else if (lowerStatus.includes('error') || lowerStatus.includes('fail')) {
      return 'bg-red-500 hover:bg-red-600';
    } else if (lowerStatus.includes('progress')) {
      return 'bg-blue-500 hover:bg-blue-600';
    } else if (lowerStatus.includes('escalat') || lowerStatus.includes('review')) {
      return 'bg-amber-500 hover:bg-amber-600';  
    }
    
    return 'bg-gray-500 hover:bg-gray-600';
  };

  // Function to format date
  const formatDate = (dateString: string): string => {
    try {
      return format(new Date(dateString), 'MMM d, HH:mm');
    } catch (e) {
      return 'Unknown';
    }
  };
  
  // Filter tickets based on search query and status filter
  const filteredTickets = tickets.filter(ticket => {
    // Filter by search query (case insensitive)
    const matchesSearch = searchQuery
      ? ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ticket.id.toLowerCase().includes(searchQuery.toLowerCase())
      : true;
      
    // Filter by status
    const matchesStatus = filterStatus
      ? ticket.status.toLowerCase().includes(filterStatus.toLowerCase())
      : true;
      
    return matchesSearch && matchesStatus;
  });

  return (
    <Card className="w-full">
      <CardHeader className="py-4">
        <CardTitle className="text-lg">Active Tickets</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Title</TableHead>
                <TableHead className="hidden md:table-cell">Status</TableHead>
                <TableHead className="hidden sm:table-cell">Updated</TableHead>
                <TableHead className="hidden lg:table-cell">Retry Attempts</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    <div className="flex flex-col items-center justify-center text-muted-foreground">
                      <Clock className="h-6 w-6 animate-pulse mb-2" />
                      <p>Loading tickets...</p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : filteredTickets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    {searchQuery || filterStatus 
                      ? "No tickets match your search criteria" 
                      : "No active tickets found"}
                  </TableCell>
                </TableRow>
              ) : (
                filteredTickets.map((ticket) => {
                  const isEarlyEscalation = ticket.escalated && 
                    (ticket.retryCount || 0) < (ticket.maxRetries || 4);
                    
                  const retryPercentage = ticket.maxRetries 
                    ? Math.min((ticket.retryCount || 0) / ticket.maxRetries * 100, 100) 
                    : 0;
                    
                  return (
                    <TableRow 
                      key={ticket.id}
                      className={`cursor-pointer hover:bg-muted/50 ${selectedTicketId === ticket.id ? 'bg-muted' : ''}`}
                      onClick={() => onSelectTicket && onSelectTicket(ticket.id)}
                    >
                      <TableCell className="font-medium">{ticket.id}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        <div className="flex items-center gap-2">
                          {ticket.escalated && (
                            <AlertTriangle className="h-4 w-4 text-destructive" />
                          )}
                          {ticket.title}
                        </div>
                      </TableCell>
                      <TableCell className="hidden md:table-cell">
                        <Badge className={`${getStatusColor(ticket.status)} text-xs text-white`}>
                          {ticket.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="hidden sm:table-cell text-muted-foreground text-sm">
                        {formatDate(ticket.updatedAt)}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex items-center gap-2">
                                <Badge 
                                  variant={ticket.escalated ? "destructive" : "outline"} 
                                  className="text-xs flex items-center gap-1"
                                >
                                  {ticket.retryCount ? <RefreshCcw className="h-3 w-3" /> : null}
                                  <span>{ticket.retryCount || 0}/{ticket.maxRetries || 4}</span>
                                </Badge>
                                
                                <Progress 
                                  value={retryPercentage} 
                                  className={`h-1.5 w-10 ${ticket.escalated ? "bg-red-100" : ""}`}
                                />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <div>
                                <p className="text-xs">
                                  {ticket.escalated 
                                    ? (isEarlyEscalation 
                                        ? "Early escalation before max retries"
                                        : "Escalated after max retries") 
                                    : `${ticket.retryCount || 0} of ${ticket.maxRetries || 4} attempts used`
                                  }
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
