export interface HealthStatusResponse {
  status: string;
  mysql: string;
  rabbitmq: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export async function fetchHealthStatus(): Promise<HealthStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok && response.status !== 503) {
    throw new Error(`Fallo en health check con codigo HTTP ${response.status}`);
  }

  return response.json();
}
