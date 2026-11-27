import { useState } from "react";
import { Lock, Eye, EyeOff } from "lucide-react";

export function PasswordField({ id, label, value, onChange, autoComplete, testId, hint, minLength }) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-bold text-navy mb-2">{label}</label>
      <div className="relative">
        <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy/50 pointer-events-none" aria-hidden="true" />
        <input
          id={id} name={id} data-testid={testId}
          type={show ? "text" : "password"} required minLength={minLength}
          autoComplete={autoComplete} value={value} onChange={onChange}
          aria-describedby={hint ? `${id}-hint` : undefined}
          className="w-full pl-12 pr-14 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
        />
        <button type="button" onClick={() => setShow((v) => !v)} data-testid={`${testId}-toggle`}
          aria-label={show ? "Masquer le mot de passe" : "Afficher le mot de passe"} aria-pressed={show}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 rounded-xl text-navy hover:bg-cream transition-colors">
          {show ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
        </button>
      </div>
      {hint && <p id={`${id}-hint`} className="text-sm text-navy mt-1.5">{hint}</p>}
    </div>
  );
}
