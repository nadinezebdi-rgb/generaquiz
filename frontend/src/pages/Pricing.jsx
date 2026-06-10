import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Check, Crown, ArrowRight, Loader2, Ticket, Sparkles } from "lucide-react";

export default function Pricing() {
  const { user, refresh } = useAuth();
  const [packages, setPackages] = useState([]);
  const [loadingId, setLoadingId] = useState(null);
  const [err, setErr] = useState("");
  const [promoCode, setPromoCode] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoMsg, setPromoMsg] = useState(null); // { type: 'success'|'error', text, isLifetime? }
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/packages").then((r) => setPackages(r.data)).catch(() => {});
  }, []);

  const PERKS = {
    premium_monthly: [
      "Questions illimitées (jusqu'à 30 par quiz)",
      "Accès à toutes les activités",
      "Défis famille avec petits-enfants",
      "Lecture vocale des questions",
      "Statistiques détaillées",
      "Sans publicité",
    ],
    premium_yearly: [
      "Tout Premium Mensuel",
      "12 mois pour le prix de 10",
      "Économisez ~17 €",
      "Support prioritaire",
    ],
  };

  const checkout = async (packageId) => {
    setErr(""); setLoadingId(packageId);
    try {
      const origin = window.location.origin;
      const { data } = await api.post("/checkout/session", { package_id: packageId, origin_url: origin });
      if (data.url) window.location.href = data.url;
    } catch (e) {
      setErr(e.response?.data?.detail || e.message || "Erreur");
      setLoadingId(null);
    }
  };

  const redeem = async (e) => {
    e.preventDefault();
    setPromoMsg(null); setPromoLoading(true);
    try {
      const { data } = await api.post("/promo/redeem", { code: promoCode.trim().toUpperCase() });
      await refresh();
      setPromoMsg({
        type: "success",
        text: data.is_lifetime
          ? "Félicitations ! Vous avez désormais un accès Premium illimité 🎉"
          : `Code accepté ! ${data.duration_days} jours de Premium ajoutés à votre compte.`,
        isLifetime: data.is_lifetime,
      });
      setPromoCode("");
      setTimeout(() => navigate("/app/dashboard"), 2500);
    } catch (e2) {
      setPromoMsg({ type: "error", text: e2.response?.data?.detail || "Code invalide" });
    } finally {
      setPromoLoading(false);
    }
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-1 rounded-full text-sm mb-4">
            <Crown className="w-4 h-4" /> Devenir Premium
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-3">
            Profitez sans limite
          </h1>
          <p className="text-xl text-navy/70 max-w-2xl mx-auto">
            Débloquez toutes les fonctionnalités pour vous et votre famille. Annulez à tout moment.
          </p>
          {user?.plan === "premium" && (
            <div className="mt-6 inline-flex items-center gap-2 bg-[#3D9970]/15 border-2 border-[#3D9970]/40 text-navy font-bold px-5 py-3 rounded-full">
              <Check className="w-5 h-5 text-[#3D9970]" strokeWidth={3} /> Vous êtes déjà Premium !
            </div>
          )}
        </div>

        {err && (
          <div className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy text-center mb-6" data-testid="pricing-error">
            {err}
          </div>
        )}

        {/* ====== PROMO CODE REDEEM (success message also shown to fresh-Premium users for ~2.5s) ====== */}
        {(user?.plan !== "premium" || promoMsg?.type === "success") && (
          <div className="bg-white border-4 border-mustard rounded-[28px] p-6 md:p-8 mb-8 shadow-soft" data-testid="promo-redeem-block">
            {user?.plan !== "premium" && (
              <div className="flex flex-col md:flex-row md:items-center gap-5">
                <div className="flex items-center gap-3 md:shrink-0">
                  <span className="w-14 h-14 rounded-2xl bg-mustard/40 flex items-center justify-center">
                    <Ticket className="w-7 h-7 text-bordeaux" strokeWidth={2.5} />
                  </span>
                  <div>
                    <h2 className="font-display text-2xl font-bold text-navy leading-tight">Vous avez un code ?</h2>
                    <p className="text-navy/70 text-sm">Activez Premium sans paiement.</p>
                  </div>
                </div>
                <form onSubmit={redeem} className="flex-1 flex flex-col sm:flex-row gap-3 w-full">
                  <input
                    data-testid="promo-redeem-input"
                    type="text"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                    placeholder="Saisissez votre code"
                    className="flex-1 p-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px] font-mono uppercase"
                    maxLength={40}
                  />
                  <button
                    type="submit"
                    data-testid="promo-redeem-submit"
                    disabled={!promoCode.trim() || promoLoading}
                    className="inline-flex items-center justify-center gap-2 bg-bordeaux hover:bg-[#5d262e] text-cream font-bold px-6 py-4 rounded-full min-h-[56px] disabled:opacity-60 transition"
                  >
                    {promoLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                    Activer
                  </button>
                </form>
              </div>
            )}
            {promoMsg && (
              <div
                data-testid={`promo-redeem-${promoMsg.type}`}
                className={`${user?.plan !== "premium" ? "mt-5" : ""} rounded-2xl p-4 border-2 ${
                  promoMsg.type === "success"
                    ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                    : "bg-[#D9534F]/10 border-[#D9534F]/40"
                }`}
              >
                <p className="text-navy font-medium text-lg">
                  {promoMsg.type === "success" ? "✅ " : "❌ "}{promoMsg.text}
                </p>
                {promoMsg.type === "success" && (
                  <p className="text-navy/60 text-sm mt-1">Redirection vers votre tableau de bord...</p>
                )}
              </div>
            )}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {packages.map((pkg) => {
            const isYearly = pkg.id === "premium_yearly";
            return (
              <div
                key={pkg.id}
                data-testid={`pricing-pkg-${pkg.id}`}
                className={`relative rounded-[28px] p-8 ${
                  isYearly
                    ? "bg-navy text-white border-4 border-mustard shadow-warm"
                    : "bg-white border-2 border-cream-dark"
                }`}
              >
                {isYearly && (
                  <span className="absolute -top-4 left-1/2 -translate-x-1/2 bg-mustard text-navy font-bold text-sm px-4 py-1.5 rounded-full">
                    ★ Meilleur rapport
                  </span>
                )}
                <h2 className={`font-display text-2xl font-bold mb-1 ${isYearly ? "text-mustard" : "text-navy"}`}>
                  {pkg.label}
                </h2>
                <p className={`mb-5 ${isYearly ? "text-cream/70" : "text-navy/60"}`}>{pkg.description}</p>
                <div className="mb-6">
                  <span className={`font-display text-5xl font-extrabold ${isYearly ? "text-white" : "text-bordeaux"}`}>
                    {pkg.amount.toFixed(2).replace(".", ",")} €
                  </span>
                  <span className={`ml-2 ${isYearly ? "text-cream/70" : "text-navy/60"}`}>
                    {isYearly ? "/ an" : "/ mois"}
                  </span>
                </div>

                <ul className={`space-y-3 mb-7 ${isYearly ? "text-cream" : "text-navy/80"}`}>
                  {(PERKS[pkg.id] || []).map((p) => (
                    <li key={p} className="flex items-start gap-2">
                      <Check className={`w-5 h-5 mt-1 shrink-0 ${isYearly ? "text-mustard" : "text-terracotta"}`} strokeWidth={3} />
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>

                <button
                  data-testid={`pricing-buy-${pkg.id}`}
                  onClick={() => checkout(pkg.id)}
                  disabled={loadingId !== null || user?.plan === "premium"}
                  className={`w-full inline-flex items-center justify-center gap-2 font-bold text-lg px-6 py-4 rounded-full min-h-[60px] disabled:opacity-60 transition ${
                    isYearly
                      ? "bg-mustard hover:bg-mustard-dark text-navy"
                      : "bg-terracotta hover:bg-terracotta-dark text-white shadow-warm"
                  }`}
                >
                  {loadingId === pkg.id ? (
                    <><Loader2 className="w-5 h-5 animate-spin" /> Redirection...</>
                  ) : user?.plan === "premium" ? (
                    "Vous êtes Premium"
                  ) : (
                    <>S'abonner <ArrowRight className="w-5 h-5" /></>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <p className="text-center text-navy/60 mt-8 text-sm">
          Paiement sécurisé par Stripe. Annulation possible à tout moment depuis votre compte.
        </p>
      </main>

      <Footer />
    </div>
  );
}
