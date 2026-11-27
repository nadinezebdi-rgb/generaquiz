import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const { refresh } = useAuth();
  const [state, setState] = useState({ status: "loading", msg: "" });
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return; // StrictMode : le lien ne sert qu'une fois
    done.current = true;
    const token = params.get("token") || "";
    if (token.length < 20) { setState({ status: "error", msg: "Ce lien est incomplet. Ouvrez-le directement depuis l'e-mail reçu, ou demandez un nouveau lien depuis votre tableau de bord." }); return; }
    api.post("/auth/verify-email", { token })
      .then(() => { setState({ status: "ok" }); refresh?.(); })
      .catch((e) => setState({ status: "error", msg: formatError(e.response?.data?.detail) || "Lien invalide." }));
  }, [params, refresh]);

  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4">
      <div className="bg-white border-2 border-cream-dark rounded-3xl p-8 max-w-md w-full text-center" data-testid="verify-email-page">
        {state.status === "loading" && <Loader2 className="w-10 h-10 animate-spin text-navy mx-auto" />}
        {state.status === "ok" && (
          <div role="status" data-testid="verify-email-success">
            <CheckCircle2 className="w-12 h-12 text-terracotta mx-auto mb-3" />
            <h1 className="font-display text-2xl font-extrabold text-navy mb-2">Adresse e-mail confirmée</h1>
            <p className="text-navy mb-6">Merci ! Votre compte est maintenant bien protégé.</p>
          </div>
        )}
        {state.status === "error" && (
          <div role="alert" data-testid="verify-email-error">
            <AlertCircle className="w-12 h-12 text-bordeaux mx-auto mb-3" />
            <h1 className="font-display text-2xl font-extrabold text-navy mb-2">Lien non valable</h1>
            <p className="text-navy mb-6">{state.msg}</p>
          </div>
        )}
        {state.status !== "loading" && (
          <Link to="/app/dashboard" data-testid="verify-email-continue" className="inline-block bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition-colors">
            Aller à mon tableau de bord
          </Link>
        )}
      </div>
    </div>
  );
}
