import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchHealthStatus, HealthStatusResponse } from '../services/api';

export const HealthStatus: React.FC = () => {
  const { data, error, isLoading, isError, refetch } = useQuery<HealthStatusResponse, Error>({
    queryKey: ['system-health'],
    queryFn: fetchHealthStatus,
    refetchInterval: 10000,
  });

  return (
    <div
      data-testid="health-status-container"
      style={{
        fontFamily: 'system-ui, -apple-system, sans-serif',
        maxWidth: 480,
        margin: '2rem auto',
        padding: '1.5rem',
        border: '1px solid #e2e8f0',
        borderRadius: 8,
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      }}
    >
      <h2 style={{ marginTop: 0, fontSize: '1.25rem', color: '#1e293b' }}>
        Botica la Luz — Estado del Sistema
      </h2>

      {isLoading && (
        <p data-testid="health-loading" style={{ color: '#64748b' }}>
          Consultando estado de servicios...
        </p>
      )}

      {isError && !data && (
        <div
          data-testid="health-error"
          style={{
            color: '#ef4444',
            backgroundColor: '#fef2f2',
            padding: '0.75rem',
            borderRadius: 4,
            marginBottom: '1rem',
          }}
        >
          Error al conectar con el backend: {error?.message}
        </div>
      )}

      {data && (
        <div data-testid="health-data">
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ fontWeight: 600, marginRight: '0.5rem' }}>Estado Global:</span>
            <span
              data-testid="global-status"
              style={{
                display: 'inline-block',
                padding: '0.2rem 0.6rem',
                borderRadius: 4,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: data.status === 'ok' ? '#10b981' : '#f59e0b',
              }}
            >
              {data.status === 'ok' ? 'Operativo' : 'Degradado'}
            </span>
          </div>

          <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem' }}>
            <p style={{ margin: '0.4rem 0' }}>
              <strong>MySQL:</strong>{' '}
              <span
                data-testid="mysql-status"
                data-status={data.mysql}
                style={{
                  color: data.mysql === 'connected' ? '#10b981' : '#ef4444',
                  fontWeight: 500,
                }}
              >
                {data.mysql === 'connected' ? 'Disponible' : 'No disponible'}
              </span>
            </p>
            <p style={{ margin: '0.4rem 0' }}>
              <strong>RabbitMQ:</strong>{' '}
              <span
                data-testid="rabbitmq-status"
                data-status={data.rabbitmq}
                style={{
                  color: data.rabbitmq === 'connected' ? '#10b981' : '#ef4444',
                  fontWeight: 500,
                }}
              >
                {data.rabbitmq === 'connected' ? 'Disponible' : 'No disponible'}
              </span>
            </p>
          </div>
        </div>
      )}

      <button
        type="button"
        data-testid="health-refresh"
        onClick={() => refetch()}
        style={{
          marginTop: '1rem',
          padding: '0.5rem 1rem',
          backgroundColor: '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: 'pointer',
          fontWeight: 500,
        }}
      >
        Actualizar Estado
      </button>
    </div>
  );
};
