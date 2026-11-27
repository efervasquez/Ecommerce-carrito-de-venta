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
  setSession: (accessToken, usuario) => set({ accessToken, usuario }),
  clearSession: () => set({ accessToken: null, usuario: null }),
}));
