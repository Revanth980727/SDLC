
import { Layout } from '@/components/layout/Layout';
import { Dashboard } from '@/components/dashboard/Dashboard';

const Index = () => {
  return (
    <Layout>
      <h1 className="text-3xl font-bold mb-8">Bug Fix AI Pilot</h1>
      <Dashboard />
    </Layout>
  );
};

export default Index;
