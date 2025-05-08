
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

interface AgentLog {
  input?: any;
  output?: any;
  errors?: Array<{
    timestamp: string;
    message: string;
  }>;
}

interface TicketLogs {
  [agentName: string]: AgentLog;
}

export function useLogData(ticketId: string) {
  const {
    data: logs,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['logs', ticketId],
    queryFn: async () => {
      // In a real implementation, fetch from your API endpoint
      // For now, using mock data
      const response = await fetch(`/api/logs/${ticketId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      return response.json();
    },
    // Mock implementation for now
    enabled: false
  });

  useEffect(() => {
    // This effect simulates the API response with mock data
    // In a real implementation, you'd just call refetch()
  }, [ticketId]);

  // For the purpose of demonstration, return mocked logs
  return {
    logs: mockLogs[ticketId] || getMockLogs(ticketId),
    isLoading: false,
    error: null
  };
}

// Mock logs for demonstration
const mockLogs: Record<string, TicketLogs> = {
  'DEMO-123': {
    planner: {
      input: {
        ticketId: 'DEMO-123',
        title: 'Fix login button not working',
        description: 'When clicking on the login button, nothing happens. Expected behavior is to show login modal.',
        created: '2023-04-01T10:30:45Z'
      },
      output: {
        affectedFiles: ['src/components/auth/LoginButton.js', 'src/components/modals/LoginModal.js'],
        rootCause: 'Event handler is not properly bound to the component',
        suggestedApproach: 'Use React.useCallback or bind the handler in constructor'
      },
      errors: []
    },
    developer: {
      input: {
        plannerAnalysis: {
          affectedFiles: ['src/components/auth/LoginButton.js', 'src/components/modals/LoginModal.js'],
          rootCause: 'Event handler is not properly bound to the component',
          suggestedApproach: 'Use React.useCallback or bind the handler in constructor'
        }
      },
      output: {
        diffs: [
          {
            filename: 'src/components/auth/LoginButton.js',
            diff: '@@ -15,7 +15,7 @@\n const LoginButton = () => {\n   const { showModal } = useContext(ModalContext);\n \n-  const handleClick = () => {\n+  const handleClick = useCallback(() => {\n     showModal(\'login\');\n-  };\n+  }, [showModal]);\n',
            linesAdded: 2,
            linesRemoved: 2
          }
        ],
        commitMessage: 'Fix login button click handler'
      },
      errors: []
    },
    qa: {
      input: {
        diffs: [
          {
            filename: 'src/components/auth/LoginButton.js',
            diff: '@@ -15,7 +15,7 @@\n const LoginButton = () => {\n   const { showModal } = useContext(ModalContext);\n \n-  const handleClick = () => {\n+  const handleClick = useCallback(() => {\n     showModal(\'login\');\n-  };\n+  }, [showModal]);\n',
            linesAdded: 2,
            linesRemoved: 2
          }
        ]
      },
      output: {
        passed: true,
        test_results: [
          {
            name: 'login button should show modal on click',
            status: 'pass',
            duration: 125
          }
        ]
      },
      errors: []
    },
    communicator: {
      input: {
        ticketId: 'DEMO-123',
        diffs: [
          {
            filename: 'src/components/auth/LoginButton.js',
            diff: '@@ -15,7 +15,7 @@\n const LoginButton = () => {\n   const { showModal } = useContext(ModalContext);\n \n-  const handleClick = () => {\n+  const handleClick = useCallback(() => {\n     showModal(\'login\');\n-  };\n+  }, [showModal]);\n',
            linesAdded: 2,
            linesRemoved: 2
          }
        ],
        test_results: [
          {
            name: 'login button should show modal on click',
            status: 'pass',
            duration: 125
          }
        ],
        commitMessage: 'Fix login button click handler'
      },
      output: {
        prUrl: 'https://github.com/org/repo/pull/45',
        jiraUrl: 'https://jira.company.com/browse/DEMO-123',
        updates: [
          {
            type: 'jira',
            message: 'Updated JIRA ticket status to "Done"',
            timestamp: '2023-04-01T15:32:45Z'
          },
          {
            type: 'github',
            message: 'Created PR #45',
            timestamp: '2023-04-01T15:32:40Z'
          }
        ]
      },
      errors: []
    }
  },
  'BUG-456': {
    planner: {
      input: {
        ticketId: 'BUG-456',
        title: 'Fix crash on product page',
        description: 'App crashes when navigating to product detail page with certain product IDs',
        created: '2023-04-05T09:12:33Z'
      },
      output: {
        affectedFiles: ['src/pages/ProductDetail.js', 'src/api/productApi.js'],
        rootCause: 'Missing null check for product data',
        suggestedApproach: 'Add proper null checks and error handling'
      },
      errors: []
    },
    developer: {
      input: {
        plannerAnalysis: {
          affectedFiles: ['src/pages/ProductDetail.js', 'src/api/productApi.js'],
          rootCause: 'Missing null check for product data',
          suggestedApproach: 'Add proper null checks and error handling'
        }
      },
      output: {
        diffs: [
          {
            filename: 'src/pages/ProductDetail.js',
            diff: '@@ -18,7 +18,7 @@\n   useEffect(() => {\n     const fetchProduct = async () => {\n       const data = await getProductById(productId);\n-      setProduct(data);\n+      if (data) setProduct(data);\n     };\n     fetchProduct();\n   }, [productId]);',
            linesAdded: 1,
            linesRemoved: 1
          },
          {
            filename: 'src/api/productApi.js',
            diff: '@@ -5,6 +5,11 @@\n export const getProductById = async (id) => {\n   try {\n     const response = await api.get(`/products/${id}`);\n+    \n+    // Check if the response contains valid product data\n+    if (!response.data || !response.data.id) {\n+      return null;\n+    }\n     return response.data;\n   } catch (error) {\n     console.error(`Error fetching product ${id}:`, error);',
            linesAdded: 5,
            linesRemoved: 0
          }
        ],
        commitMessage: 'Fix crash on product page by adding null checks'
      },
      errors: [
        {
          timestamp: '2023-04-05T09:45:22Z',
          message: 'Error applying patch: src/api/productApi.js uses named exports but attempted to apply default export'
        }
      ]
    },
    qa: {
      input: {
        diffs: [
          {
            filename: 'src/pages/ProductDetail.js',
            diff: '@@ -18,7 +18,7 @@\n   useEffect(() => {\n     const fetchProduct = async () => {\n       const data = await getProductById(productId);\n-      setProduct(data);\n+      if (data) setProduct(data);\n     };\n     fetchProduct();\n   }, [productId]);',
            linesAdded: 1,
            linesRemoved: 1
          }
        ]
      },
      output: {
        passed: false,
        test_results: [
          {
            name: 'should handle invalid product IDs',
            status: 'pass',
            duration: 87
          },
          {
            name: 'should display product details for valid products',
            status: 'fail',
            duration: 154,
            errorMessage: 'Timeout: Element with data-testid="product-title" not found'
          }
        ]
      },
      errors: []
    },
    communicator: {
      input: {
        ticketId: 'BUG-456',
        diffs: [],
        test_results: [],
        commitMessage: ''
      },
      output: null,
      errors: [
        {
          timestamp: '2023-04-05T10:15:45Z',
          message: 'Failed to create PR due to test failures'
        },
        {
          timestamp: '2023-04-05T10:16:01Z',
          message: 'Issue escalated to human reviewer'
        }
      ]
    }
  }
};

function getMockLogs(ticketId: string): TicketLogs {
  // Generate a mock log structure for tickets not in the mock database
  return {
    planner: {
      input: {
        ticketId: ticketId,
        title: 'Mock ticket title',
        description: 'This is a mock ticket description',
      },
      output: {
        affectedFiles: ['src/components/SomeComponent.js'],
        rootCause: 'Mock root cause analysis',
        suggestedApproach: 'Mock approach suggestion'
      },
      errors: []
    },
    developer: {
      input: {
        plannerAnalysis: { /* mock data */ }
      },
      output: {
        diffs: [
          {
            filename: 'src/components/SomeComponent.js',
            diff: '@@ -10,7 +10,7 @@\n // Mock diff content',
            linesAdded: 1,
            linesRemoved: 1
          }
        ]
      },
      errors: []
    },
    qa: {
      input: {
        diffs: [/* mock data */]
      },
      output: {
        passed: true,
        test_results: [
          {
            name: 'mock test',
            status: 'pass',
            duration: 50
          }
        ]
      },
      errors: []
    },
    communicator: {
      input: {
        ticketId: ticketId,
        diffs: [/* mock data */],
        test_results: [/* mock data */],
        commitMessage: 'Mock commit message'
      },
      output: {
        prUrl: `https://github.com/org/repo/pull/${Math.floor(Math.random() * 100)}`,
        jiraUrl: `https://jira.company.com/browse/${ticketId}`,
      },
      errors: []
    }
  };
}
