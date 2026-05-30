import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthUser {
  name: string;
  email: string;
  picture?: string;
  sub: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  login: (userData: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Intentar recuperar el usuario del localStorage al cargar la app
    const storedUser = localStorage.getItem('fraudia_auth_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        console.error("Failed to parse stored user", e);
        localStorage.removeItem('fraudia_auth_user');
      }
    }
    setIsLoading(false);
  }, []);

  const login = (userData: AuthUser) => {
    setUser(userData);
    localStorage.setItem('fraudia_auth_user', JSON.stringify(userData));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('fraudia_auth_user');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
