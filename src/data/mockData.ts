
import { Ticket, PlannerAnalysis, CodeDiff, TestResult, Update } from '../types/ticket';

export const mockTicket: Ticket = {
  id: 'DEMO-123',
  title: 'Fix login button not working',
  description: 'When clicking on the login button, nothing happens. Expected behavior is to show login modal.',
  status: 'Open',
  priority: 'High',
  reporter: 'John Doe',
  assignee: 'AI Bot',
  created: '2023-04-01T10:30:00Z',
  updated: '2023-04-01T11:45:00Z'
};

export const mockPlannerAnalysis: PlannerAnalysis = {
  ticket_id: 'DEMO-123',
  bug_summary: 'The event handler for the login button click is not correctly bound to the component context. This causes the handler to lose reference to the component state and methods when clicked.',
  affected_files: [
    'src/components/auth/LoginButton.js',
    'src/components/modals/LoginModal.js'
  ],
  error_type: 'Event Handler Binding Issue',
  // For backward compatibility
  affectedFiles: [
    'src/components/auth/LoginButton.js',
    'src/components/modals/LoginModal.js'
  ],
  rootCause: 'The event handler for the login button click is not correctly bound to the component context. This causes the handler to lose reference to the component state and methods when clicked.',
  suggestedApproach: 'Use React.useCallback hook to properly bind the event handler, ensuring it has access to the correct context and dependencies. Also verify that the modal context is properly imported and used.'
};

export const mockDiffs: CodeDiff[] = [
  {
    filename: 'src/components/auth/LoginButton.js',
    diff: `@@ -15,7 +15,7 @@
 const LoginButton = () => {
   const { showModal } = useContext(ModalContext);
 
-  const handleClick = () => {
+  const handleClick = useCallback(() => {
     showModal('login');
-  };
+  }, [showModal]);`,
    linesAdded: 2,
    linesRemoved: 2
  },
  {
    filename: 'src/components/modals/LoginModal.js',
    diff: `@@ -8,7 +8,7 @@
 export const LoginModal = ({ isOpen, onClose }) => {
   const { login } = useAuth();
   
-  const handleSubmit = (event) => {
+  const handleSubmit = useCallback((event) => {
     event.preventDefault();
     const { username, password } = event.target.elements;
     login(username.value, password.value);
@@ -18,5 +18,5 @@
       {/* Modal content */}
     </div>
   );
-};
+}, [login, onClose]);`,
    linesAdded: 5,
    linesRemoved: 3
  }
];

export const mockTestResults: TestResult[] = [
  {
    name: 'LoginButton should render correctly',
    status: 'pass',
    duration: 45
  },
  {
    name: 'LoginButton should show modal when clicked',
    status: 'pass',
    duration: 78
  },
  {
    name: 'LoginModal should handle form submission',
    status: 'pass',
    duration: 120
  },
  {
    name: 'Login flow should work end-to-end',
    status: 'pass',
    duration: 350
  }
];

export const mockUpdates: Update[] = [
  {
    timestamp: '2023-04-01T14:30:00Z',
    message: 'Analysis complete: identified issue in login button event binding',
    type: 'system'
  },
  {
    timestamp: '2023-04-01T14:35:00Z',
    message: 'Generated code changes for 2 files',
    type: 'system'
  },
  {
    timestamp: '2023-04-01T14:40:00Z',
    message: 'All tests passing after code changes',
    type: 'system'
  },
  {
    timestamp: '2023-04-01T14:45:00Z',
    message: 'Created pull request #45',
    type: 'github'
  },
  {
    timestamp: '2023-04-01T14:46:00Z',
    message: 'Updated ticket DEMO-123 with PR link',
    type: 'jira'
  },
  {
    timestamp: '2023-04-01T14:47:00Z',
    message: 'Set ticket status to "In Review"',
    type: 'jira'
  }
];

// Mock tickets list for the dashboard
export const mockTicketsList = [
  {
    id: 'DEMO-123',
    title: 'Fix login button not working',
    status: 'in-progress',
    stage: 'planning',
    prUrl: undefined,
    updatedAt: '2023-04-01T11:45:00Z'
  },
  {
    id: 'BUG-456',
    title: 'Fix crash on product page',
    status: 'failed',
    stage: 'escalated',
    prUrl: undefined,
    updatedAt: '2023-04-05T10:16:01Z'
  },
  {
    id: 'FEAT-789',
    title: 'Add user profile settings',
    status: 'success',
    stage: 'pr-opened',
    prUrl: 'https://github.com/org/repo/pull/42',
    updatedAt: '2023-03-28T15:22:30Z'
  },
  {
    id: 'DEMO-124',
    title: 'Fix pagination on search results',
    status: 'success',
    stage: 'completed',
    prUrl: 'https://github.com/org/repo/pull/41',
    updatedAt: '2023-03-25T09:15:45Z'
  },
  {
    id: 'BUG-457',
    title: 'Fix image loading on mobile devices',
    status: 'in-progress',
    stage: 'development',
    prUrl: undefined,
    updatedAt: '2023-04-06T08:30:12Z'
  },
  {
    id: 'FEAT-790',
    title: 'Implement dark mode',
    status: 'in-progress',
    stage: 'qa',
    prUrl: undefined,
    updatedAt: '2023-04-04T16:45:33Z'
  }
];
