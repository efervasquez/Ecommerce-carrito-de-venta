import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HealthStatus } from './components/HealthStatus';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <main
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          backgroundColor: '#f8fafc',
          padding: '1rem',
        }}
      >
        <HealthStatus />
      </main>
    </QueryClientProvider>
  );
};

export default App;
