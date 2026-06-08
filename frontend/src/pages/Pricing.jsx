import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Check, Crown, ArrowRight, Loader2 } from "lucide-react";

export default function Pricing() {
  const { user } = useAuth();
  const [packages, setPackages] = useState([]);
  const [loadingId, setLoadingId] = useState(null);
  const [err, setErr] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/packages").then((r) => setPackages(r.data)).catch(() => {});
  }, []);

  const PERKS = {
    premium_monthly: [
      "Questions illimitées (jusqu'à 20 par quiz)",
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
