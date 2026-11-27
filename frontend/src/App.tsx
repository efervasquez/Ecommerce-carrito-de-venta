import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { HealthStatus } from './components/HealthStatus';
import { Activar } from './pages/Activar';
import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { Registro } from './pages/Registro';

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
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/activar" element={<Activar />} />
          <Route path="/login" element={<Login />} />
          <Route path="/salud" element={<HealthStatus />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
