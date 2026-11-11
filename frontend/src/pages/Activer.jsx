import { useEffect, useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Gift, Loader2, PartyPopper, Search } from "lucide-react";
import Navbar from "@/components/Navbar";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatCodeInput, fmtDate, PENDING_GIFT_KEY } from "@/lib/gifts";

function GiftPreview({ gift }) {
  return (
    <div className="bg-navy-dark text-cream rounded-3xl p-6 border-4 border-mustard/60 text-left" data-testid="activer-preview">
      <p className="text-mustard text-xs font-bold uppercase tracking-[0.2em] mb-2">{gift.offer_label}</p>
      <h2 className="font-display text-2xl font-extrabold mb-1">Pour {gift.recipient_name || "vous"}</h2>
      {gift.buyer_name && <p className="text-cream/80">De la part de {gift.buyer_name}</p>}
      {gift.message && <p className="font-display italic text-lg mt-3">« {gift.message} »</p>}
    </div>
  );
}

function ActivateAction({ gift, onDone }) {
  const { user, refresh } = useAuth();
  const [loading, setLoading] = useState(false);
  if (gift.status === "redeemed") return <p className="text-bordeaux font-semibold" data-testid="activer-already">Ce code a déjà été activé.</p>;
  if (!user) {
    const next = `/activer?code=${gift.code}`;
    const keep = () => { try { sessionStorage.setItem(PENDING_GIFT_KEY, gift.code); } catch { /* storage bloqué */ } };
    return (
      <div className="grid sm:grid-cols-2 gap-3" data-testid="activer-auth">
        <Link to={`/register?next=${encodeURIComponent(next)}`} onClick={keep} data-testid="activer-register" className="bg-terracotta text-white font-bold px-6 py-4 rounded-full text-center hover:bg-terracotta-dark transition-colors">Créer mon compte</Link>
        <Link to="/login" state={{ from: next }} onClick={keep} data-testid="activer-login" className="bg-white border-2 border-navy text-navy font-bold px-6 py-4 rounded-full text-center hover:bg-navy hover:text-cream transition-colors">J&apos;ai déjà un compte</Link>
      </div>
    );
  }
  const activate = async () => {
    setLoading(true);
    try {
      const { data } = await api.post("/gifts/redeem", { code: gift.code });
      try { sessionStorage.removeItem(PENDING_GIFT_KEY); } catch { /* storage bloqué */ }
      await refresh();
      onDone(data);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail));
      setLoading(false);
    }
  };
  return (
    <button type="button" onClick={activate} disabled={loading} data-testid="activer-submit"
      className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm transition-colors disabled:opacity-70">
      {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Gift className="w-5 h-5" />} Activer mon année ({user.name})
    </button>
  );
}

export default function Activer() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const initial = params.get("code") || (() => { try { return sessionStorage.getItem(PENDING_GIFT_KEY) || ""; } catch { return ""; } })();
  const [code, setCode] = useState(formatCodeInput(initial));
  const [gift, setGift] = useState(null);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);

  const lookup = async (c) => {
    setError("");
    try { setGift((await api.get(`/gifts/code/${encodeURIComponent(c)}`)).data); }
    catch (e) { setGift(null); setError(formatError(e.response?.data?.detail)); }
  };
  useEffect(() => { if (code.length === 12) lookup(code); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />
      <main className="max-w-xl mx-auto px-4 py-14" data-testid="activer-page">
        {done ? (
          <div className="bg-white rounded-3xl border-4 border-mustard p-8 text-center shadow-warm" data-testid="activer-success">
            <PartyPopper className="w-16 h-16 text-terracotta mx-auto mb-4" />
            <h1 className="font-display text-3xl font-extrabold text-navy mb-2">Votre cadeau est activé !</h1>
            <p className="text-navy/75 mb-6">{done.offer_label} {done.plan_expires_at ? <>jusqu&apos;au <strong>{fmtDate(done.plan_expires_at)}</strong></> : <>— votre accès à vie est conservé</>}.</p>
            {done.offer === "famille" && <p className="text-navy/75 mb-6">Invitez maintenant jusqu&apos;à 4 proches pour jouer ensemble.</p>}
            <button type="button" onClick={() => navigate(done.offer === "famille" ? "/app/famille" : "/app/dashboard")} data-testid="activer-continue"
              className="bg-navy text-cream font-bold px-8 py-4 rounded-full hover:bg-terracotta transition-colors">
              {done.offer === "famille" ? "Inviter mes proches" : "Commencer à jouer"}
            </button>
          </div>
        ) : (
          <>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-3">Activer un cadeau</h1>
            <p className="text-navy/70 mb-6">Saisissez le code inscrit sur votre carte cadeau.</p>
            <form onSubmit={(e) => { e.preventDefault(); lookup(code); }} className="flex gap-2 mb-4">
              <input value={code} onChange={(e) => setCode(formatCodeInput(e.target.value))} placeholder="GQ-XXXX-XXXX" aria-label="Code cadeau" data-testid="activer-code-input"
                className="flex-1 min-w-0 rounded-2xl border-2 border-cream-dark bg-white px-4 py-4 font-mono text-xl tracking-wider text-navy focus:border-navy outline-none" />
              <button type="submit" data-testid="activer-lookup" className="bg-navy text-cream font-bold px-5 rounded-2xl hover:bg-terracotta transition-colors inline-flex items-center gap-2">
                <Search className="w-5 h-5" /> <span className="hidden sm:inline">Vérifier</span>
              </button>
            </form>
            {error && <p className="text-bordeaux font-semibold mb-4" data-testid="activer-error">{error}</p>}
            {gift && <div className="grid gap-5"><GiftPreview gift={gift} /><ActivateAction gift={gift} onDone={setDone} /></div>}
          </>
        )}
      </main>
    </div>
  );
}
