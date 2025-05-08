
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from '@/components/ui/sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TicketFormProps {
  onSubmit: (ticketId: string) => void;
  isProcessing: boolean;
}

export function TicketForm({ onSubmit, isProcessing }: TicketFormProps) {
  const [ticketId, setTicketId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketId.trim()) {
      toast.error('Please enter a valid JIRA ticket ID.');
      return;
    }
    onSubmit(ticketId);
    // Don't clear the input, in case the user wants to try again
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fix Bug</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="ticketId">JIRA Ticket ID</Label>
            <div className="flex gap-2">
              <Input
                id="ticketId"
                placeholder="E.g., PROJ-123"
                value={ticketId}
                onChange={(e) => setTicketId(e.target.value)}
                disabled={isProcessing}
              />
              <Button type="submit" disabled={isProcessing || !ticketId.trim()}>
                {isProcessing ? 'Processing...' : 'Fix Bug'}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
