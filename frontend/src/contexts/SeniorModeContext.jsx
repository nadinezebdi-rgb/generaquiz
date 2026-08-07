import { createContext, useContext, useEffect, useState } from "react";

/**
 * SeniorModeContext — accessibility toggle for larger fonts, bigger contrast,
 * and slower animations. Persisted to localStorage so the pref is sticky.
 *
 * Applied via a `.senior-mode` class on <html>. See index.css for the rules.
 */
const SeniorModeContext = createContext({ enabled: false, toggle: () => {} });

const STORAGE_KEY = "gq_senior_mode";

export function SeniorModeProvider({ children }) {
  const [enabled, setEnabled] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (enabled) root.classList.add("senior-mode");
    else root.classList.remove("senior-mode");
    try {
      localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
    } catch {
      /* localStorage may be disabled */
    }
  }, [enabled]);

  const value = { enabled, toggle: () => setEnabled((v) => !v) };
  return <SeniorModeContext.Provider value={value}>{children}</SeniorModeContext.Provider>;
}

export function useSeniorMode() {
  return useContext(SeniorModeContext);
}
