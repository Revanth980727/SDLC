
import axios from 'axios';
import { Ticket } from '@/types/ticket';

// Get API base URL from environment variable or use a default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with common configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.status || 'Unknown', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export interface TicketListResponse {
  tickets: Ticket[];
}

export interface TicketDetailResponse {
  ticket: Ticket;
  agentOutputs: {
    planner?: {
      affectedFiles?: string[];
      rootCause?: string;
      suggestedApproach?: string;
    };
    developer?: {
      diffs?: {
        filename: string;
        diff: string;
        linesAdded: number;
        linesRemoved: number;
      }[];
      attempt: number;
      maxAttempts: number;
    };
    qa?: {
      testResults?: {
        name: string;
        status: 'pass' | 'fail';
        duration: number;
        errorMessage?: string;
      }[];
    };
    communicator?: {
      updates?: {
        timestamp: string;
        message: string;
        type: 'jira' | 'github' | 'system';
      }[];
      prUrl?: string;
      jiraUrl?: string;
    };
  };
  status: string;
  currentStage: 'planning' | 'development' | 'qa' | 'communicating' | 'completed' | 'escalated';
  escalated: boolean;
  retryCount: number;
  maxRetries: number;
}

export interface StartFixResponse {
  message: string;
  status: string;
  ticketId: string;
}

// API functions
export const api = {
  // Get list of all active tickets
  async getTickets(): Promise<Ticket[]> {
    try {
      const response = await apiClient.get('/tickets');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch tickets:', error);
      return [];
    }
  },

  // Get detailed info for a specific ticket
  async getTicketDetails(ticketId: string): Promise<TicketDetailResponse | null> {
    try {
      const response = await apiClient.get(`/tickets/${ticketId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch details for ticket ${ticketId}:`, error);
      return null;
    }
  },

  // Start the fix process for a ticket
  async startFix(ticketId: string): Promise<StartFixResponse | null> {
    try {
      const response = await apiClient.post('/process-ticket', { 
        ticket_id: ticketId,
        title: '', // These fields will be populated by backend from JIRA
        description: ''
      });
      return response.data;
    } catch (error) {
      console.error(`Failed to start fix for ticket ${ticketId}:`, error);
      return null;
    }
  },
  
  // Check health of backend services
  async checkHealth(): Promise<boolean> {
    try {
      await apiClient.get('/health');
      return true;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
};
