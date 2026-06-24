import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import { CheckCircle2, Loader2, AlertCircle, Crown, ArrowRight } from "lucide-react";

export default function Success() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const { refresh } = useAuth();
  const [status, setStatus] = useState("checking"); // checking | paid | expired | error
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!sessionId) {
      setStatus("error");
      return;
    }
    let cancelled = false;
    const poll = async (n) => {
      if (cancelled) return;
      try {
        const { data } = await api.get(`/checkout/status/${sessionId}`);
        if (data.payment_status === "paid") {
          await refresh();
          setStatus("paid");
          return;
        }
        if (data.status === "expired") {
          setStatus("expired");
          return;
        }
        if (n >= 6) {
          setStatus("error");
          return;
        }
        setAttempts(n);
        setTimeout(() => poll(n + 1), 2000);
      } catch {
        if (n >= 6) {
          setStatus("error");
        } else {
          setTimeout(() => poll(n + 1), 2000);
        }
      }
    };
    poll(0);
    return () => { cancelled = true; };
  }, [sessionId, refresh]);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-2xl mx-auto px-4 py-16 text-center">
        {status === "checking" && (
          <div data-testid="success-checking">
            <Loader2 className="w-16 h-16 text-terracotta mx-auto mb-6 animate-spin" />
            <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Vérification du paiement...</h1>
            <p className="text-navy/70 text-lg">Patientez quelques instants. Tentative {attempts + 1}/6.</p>
          </div>
        )}

        {status === "paid" && (
          <div className="bg-white border-4 border-mustard rounded-[32px] p-10 shadow-warm" data-testid="success-paid">
            <CheckCircle2 className="w-20 h-20 text-[#3D9970] mx-auto mb-4 pop-anim" strokeWidth={2} />
            <h1 className="font-display text-4xl font-extrabold text-navy mb-3">Bienvenue chez Premium !</h1>
            <p className="text-xl text-navy/80 mb-6">
              Votre abonnement est actif. Profitez de questions illimitées, des activités exclusives et bien plus.
            </p>
            <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-5 py-3 rounded-full mb-7">
              <Crown className="w-5 h-5" /> Membre Premium
            </div>
            <div>
              <Link
                to="/app/dashboard"
                data-testid="success-to-dashboard"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-7 py-4 rounded-full text-lg shadow-warm"
              >
                Aller au tableau de bord <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        )}

        {status === "expired" && (
          <div data-testid="success-expired">
            <AlertCircle className="w-16 h-16 text-[#D9534F] mx-auto mb-4" />
            <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Session expirée</h1>
            <p className="text-navy/70 mb-6">Veuillez réessayer le paiement.</p>
            <Link to="/app/pricing" className="bg-terracotta text-white font-bold px-6 py-3 rounded-full">
              Retour aux tarifs
            </Link>
          </div>
        )}

        {status === "error" && (
          <div data-testid="success-error">
            <AlertCircle className="w-16 h-16 text-[#D9534F] mx-auto mb-4" />
            <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Impossible de confirmer</h1>
            <p className="text-navy/70 mb-6">
              Si vous avez bien payé, votre compte sera mis à jour dans quelques minutes. Sinon, réessayez.
            </p>
            <Link to="/app/dashboard" className="bg-navy text-white font-bold px-6 py-3 rounded-full">
              Tableau de bord
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
