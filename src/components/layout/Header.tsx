
import React from 'react';
import { Button } from '@/components/ui/button';
import { Bug } from 'lucide-react';

export function Header() {
  return (
    <header className="border-b border-border bg-card p-4">
      <div className="container flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bug className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold">BugFix AI Pilot</h1>
        </div>
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm">Documentation</Button>
          <Button size="sm">Settings</Button>
        </div>
      </div>
    </header>
  );
}
