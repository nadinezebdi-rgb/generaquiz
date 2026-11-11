import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, Download, Loader2, AlertCircle, Copy } from "lucide-react";
import { toast } from "sonner";
import Navbar from "@/components/Navbar";
import { api, BACKEND_URL } from "@/lib/api";

const MAX_TRIES = 8;

function GiftReady({ gift, pdfUrl }) {
  const copy = () => navigator.clipboard?.writeText(gift.code).then(() => toast.success("Code copié"));
  return (
    <div className="bg-navy-dark text-cream rounded-[32px] p-8 sm:p-10 shadow-warm border-4 border-mustard/70" data-testid="gift-ready">
      <CheckCircle2 className="w-16 h-16 text-mustard mx-auto mb-4" />
      <h1 className="font-display text-3xl sm:text-4xl font-extrabold mb-2">Votre cadeau est prêt !</h1>
      <p className="text-cream/80 mb-6">{gift.offer_label} pour {gift.recipient_name}. Imprimez la carte et glissez-la sous le sapin.</p>
      <div className="inline-flex items-center gap-3 bg-mustard text-navy rounded-2xl px-6 py-4 mb-6">
        <span className="font-mono text-2xl sm:text-3xl font-extrabold tracking-wider" data-testid="gift-code">{gift.code}</span>
        <button type="button" onClick={copy} aria-label="Copier le code" data-testid="gift-code-copy" className="p-2 rounded-full hover:bg-white/50 transition-colors"><Copy className="w-5 h-5" /></button>
      </div>
      <div>
        <a href={`${BACKEND_URL}${pdfUrl}`} target="_blank" rel="noreferrer" data-testid="gift-pdf-download"
          className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full transition-colors">
          <Download className="w-5 h-5" /> Télécharger la carte à imprimer
        </a>
      </div>
      <p className="text-sm text-cream/60 mt-6">Gardez ce lien : la carte reste téléchargeable depuis cette page. L&apos;année démarre le jour où {gift.recipient_name} active le code.</p>
    </div>
  );
}

export default function OffrirMerci() {
  const [params] = useSearchParams();
  const sessionId = params.get("session_id");
  const [state, setState] = useState({ status: sessionId ? "checking" : "error" });

  useEffect(() => {
    if (!sessionId) return undefined;
    let stop = false;
    const poll = async (n) => {
      if (stop) return;
      try {
        const { data } = await api.get(`/gifts/order/${sessionId}`);
        if (data.payment_status === "paid") return setState({ status: "paid", ...data });
        if (data.status === "expired") return setState({ status: "expired" });
      } catch { /* on réessaie */ }
      if (n >= MAX_TRIES) return setState({ status: "error" });
      setTimeout(() => poll(n + 1), 2000);
    };
    poll(0);
    return () => { stop = true; };
  }, [sessionId]);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />
      <main className="max-w-2xl mx-auto px-4 py-16 text-center">
        {state.status === "checking" && (
          <div data-testid="gift-checking">
            <Loader2 className="w-14 h-14 text-terracotta mx-auto mb-5 animate-spin" />
            <h1 className="font-display text-3xl font-extrabold text-navy">Vérification du paiement…</h1>
          </div>
        )}
        {state.status === "paid" && <GiftReady gift={state.gift} pdfUrl={state.pdf_url} />}
        {(state.status === "error" || state.status === "expired") && (
          <div className="bg-white border-2 border-cream-dark rounded-3xl p-8" data-testid="gift-error">
            <AlertCircle className="w-12 h-12 text-bordeaux mx-auto mb-3" />
            <h1 className="font-display text-2xl font-extrabold text-navy mb-2">Paiement non confirmé</h1>
            <p className="text-navy/70 mb-5">Si vous avez été débité, écrivez-nous à contact@generaquiz.fr avec votre e-mail : nous vous renverrons la carte.</p>
            <Link to="/offrir" className="inline-flex bg-navy text-cream font-bold px-6 py-3 rounded-full" data-testid="gift-error-back">Retour à la page Offrir</Link>
          </div>
        )}
      </main>
    </div>
  );
}
