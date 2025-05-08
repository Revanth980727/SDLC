
import React from 'react';

export function Footer() {
  return (
    <footer className="border-t border-border p-4 text-center text-sm text-muted-foreground">
      <p>BugFix AI Pilot &copy; {new Date().getFullYear()} - Running in Local Container Mode</p>
    </footer>
  );
}
