import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { HealthStatus } from './components/HealthStatus';
import { Activar } from './pages/Activar';
import { Catalogo } from './pages/Catalogo';
import { Carrito } from './pages/Carrito';
import { Checkout } from './pages/Checkout';
import { Confirmacion } from './pages/Confirmacion';
import { DetalleProducto } from './pages/DetalleProducto';
import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { OcrReceta } from './pages/OcrReceta';
import { Recuperar } from './pages/Recuperar';
import { Registro } from './pages/Registro';
import { Restablecer } from './pages/Restablecer';

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
          <Route path="/catalogo" element={<Catalogo />} />
          <Route path="/carrito" element={<Carrito />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/receta" element={<OcrReceta />} />
          <Route path="/pedidos/:numero" element={<Confirmacion />} />
          <Route path="/catalogo/productos/:id" element={<DetalleProducto />} />
          <Route path="/registro" element={<Registro />} />
          <Route path="/activar" element={<Activar />} />
          <Route path="/login" element={<Login />} />
          <Route path="/recuperar" element={<Recuperar />} />
          <Route path="/restablecer" element={<Restablecer />} />
          <Route path="/salud" element={<HealthStatus />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
