import { useState } from 'react';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../services/api';
import { useNavigate } from 'react-router-dom';

export default function LoginView() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleGuestLogin = () => {
    login({
      name: "Invitado",
      email: "guest@aseguradoradelsur.com",
      sub: "guest-123",
      picture: "https://lh3.googleusercontent.com/aida-public/AB6AXuAgJbOMgvqFxEXUWaxqfd3vMgVqVI__VidWmC8rq2pK2xo6LWe73KTarQxicezk0EHi-uGLX7CKubnqMw-SKz3Odu9y4smWhoKXrvt7MY8hwFsZykwNu63gHmFjF5pDL09GWQsBDlkRWfm8q3m7LsOUL5yVUruaPQQYYh0Fz7_GVYmRMNuvCKMHHWNp3qARplp_cywdC1mUbYPFlWorR-dJPyCOGSU3cLX1dawAFfZjq4PI2qLAHLJNokq2L7XUmTp-8OW28QQXcNg"
    });
    navigate('/');
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential }),
      });

      if (!res.ok) {
        throw new Error('Error validando credenciales con el servidor');
      }

      const data = await res.json();
      if (data.success && data.user) {
        login(data.user);
        navigate('/'); // Redirect to dashboard
      } else {
        throw new Error(data.error || 'Autenticación fallida');
      }
    } catch (err: any) {
      setError(err.message || 'Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-container-lowest flex items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-secondary/20 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md bg-surface/80 backdrop-blur-xl border border-outline-variant/50 rounded-3xl shadow-2xl overflow-hidden relative z-10">
        <div className="p-10 flex flex-col items-center">
          {/* Logo / Brand */}
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center shadow-lg shadow-primary/30 mb-6">
            <span className="material-symbols-outlined text-[32px] text-on-primary">shield_person</span>
          </div>
          
          <h1 className="font-headline-lg text-headline-lg font-bold text-on-surface mb-2 text-center">
            Aseguradora del Sur
          </h1>
          <p className="text-body-md text-on-surface-variant text-center mb-10">
            Plataforma Inteligente de Reclamos
          </p>

          {/* Error Message */}
          {error && (
            <div className="w-full bg-error-container/50 border border-error/20 text-error px-4 py-3 rounded-xl text-label-sm font-bold mb-6 text-center animate-pulse">
              {error}
            </div>
          )}

          {isLoading ? (
            <div className="flex flex-col items-center justify-center gap-4 py-8">
              <div className="w-8 h-8 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
              <p className="text-label-sm font-bold text-primary">Iniciando sesión...</p>
            </div>
          ) : (
            <div className="w-full space-y-4">
              {/* Google Login Wrapper */}
              <div className="flex justify-center w-full">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError('Google Login falló o fue cancelado')}
                  theme="filled_black"
                  shape="pill"
                  size="large"
                  text="continue_with"
                  width="100%"
                />
              </div>

              <div className="relative flex items-center py-4">
                <div className="flex-grow border-t border-outline-variant"></div>
                <span className="flex-shrink-0 mx-4 text-on-surface-variant text-label-xs font-bold uppercase tracking-wider">O</span>
                <div className="flex-grow border-t border-outline-variant"></div>
              </div>

              {/* Fake Outlook Button */}
              <button 
                className="w-full h-[40px] flex items-center justify-center gap-3 border border-outline-variant rounded-full text-on-surface font-label-md hover:bg-surface-container-low transition-colors relative overflow-hidden group"
                onClick={() => alert("Integración con Microsoft Outlook próximamente.")}
              >
                <img 
                  src="https://upload.wikimedia.org/wikipedia/commons/d/df/Microsoft_Office_Outlook_%282018%E2%80%93present%29.svg" 
                  alt="Outlook" 
                  className="w-5 h-5 grayscale opacity-70 group-hover:grayscale-0 group-hover:opacity-100 transition-all" 
                />
                <span>Continuar con Outlook</span>
                <span className="absolute right-3 bg-surface-container-high text-[10px] uppercase font-bold px-2 py-0.5 rounded-full text-on-surface-variant">Pronto</span>
              </button>

              {/* Guest Login Button */}
              <button 
                className="w-full h-[40px] flex items-center justify-center gap-3 border border-outline-variant rounded-full text-on-surface font-label-md hover:bg-surface-container-low transition-colors"
                onClick={handleGuestLogin}
              >
                <span className="material-symbols-outlined text-[20px] text-on-surface-variant">person</span>
                <span>Continuar como Invitado</span>
              </button>
            </div>
          )}

          <div className="mt-10 text-center space-y-2">
            <p className="text-[11px] text-on-surface-variant max-w-xs mx-auto leading-relaxed">
              El acceso a esta plataforma está restringido únicamente a personal autorizado de Aseguradora del Sur.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
