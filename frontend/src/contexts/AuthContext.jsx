import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, formatError } from "@/lib/api";

const AuthContext = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch (e) {
      setUser(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Session expirée (7 jours, ou mot de passe changé sur un autre appareil) : retour à la connexion.
  useEffect(() => {
    const id = api.interceptors.response.use(undefined, (error) => {
      const url = error.config?.url || "";
      if (error.response?.status === 401 && user && !url.startsWith("/auth/") && !window.location.pathname.startsWith("/login")) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.assign(`/login?session=expiree&next=${next}`); // rechargement complet : l'état repart de zéro
      }
      return Promise.reject(error);
    });
    return () => api.interceptors.response.eject(id);
  }, [user]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data.user);
    return data.user;
  };

  const register = async (name, email, password, referralCode = null, birthYear = null) => {
    const payload = { name, email, password };
    if (referralCode) payload.referral_code = referralCode;
    if (birthYear) payload.birth_year = birthYear;
    const { data } = await api.post("/auth/register", payload);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh, formatError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
