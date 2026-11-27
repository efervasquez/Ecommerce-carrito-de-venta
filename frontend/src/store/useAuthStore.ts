import { create } from 'zustand';
import { UsuarioPublico } from '../services/auth';

interface AuthState {
  accessToken: string | null;
  usuario: UsuarioPublico | null;
  setSession: (accessToken: string, usuario: UsuarioPublico) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  usuario: null,
  setSession: (accessToken, usuario) => {
    localStorage.setItem('access_token', accessToken);
    set({ accessToken, usuario });
  },
  clearSession: () => {
    localStorage.removeItem('access_token');
    set({ accessToken: null, usuario: null });
  },
}));
