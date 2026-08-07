import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Check, Crown, Users, Sparkles, Loader2, Star, ArrowRight } from "lucide-react";

/**
 * Pricing — 3 paliers (Club Mémoire / Famille / Premium) × 2 périodes (mensuel / annuel).
 *
 * Backend est source de vérité (server-side PACKAGES) : le client se contente
 * de sélectionner un `package_id` que Stripe checkout facturera au bon montant.
 */
const TIER_META = {
  club: {
    key: "club",
    title: "Club Mémoire",
    tagline: "L'essentiel pour s'entretenir chaque jour",
    icon: Sparkles,
    color: "border-cream-dark",
    features: [
      "Quiz illimités dans toutes les catégories",
      "Progression et badges",
      "Historique complet",
      "Streaks et Ligues hebdomadaires",
    ],
  },
  famille: {
    key: "famille",
    title: "Famille",
    tagline: "Jusqu'à 5 comptes, l'esprit d'équipe",
    icon: Users,
    color: "border-terracotta ring-4 ring-terracotta/20",
    badge: "Le plus populaire",
    features: [
      "Tout Club Mémoire, pour 5 personnes",
      "Classement familial privé",
      "Défis coopératifs illimités",
      "Quiz privés entre proches",
      "Notifications famille",
    ],
  },
  premium: {
    key: "premium",
    title: "Premium",
    tagline: "Le meilleur de GénéraQuiz",
    icon: Crown,
    color: "border-navy",
    features: [
      "Tout Famille",
      "Quiz exclusifs (nouvelles catégories en avant-première)",
      "Statistiques avancées (Score Mémoire 5 axes)",
      "Support prioritaire",
      "Accès anticipé aux nouveautés",
    ],
  },
};

const YEARLY_SAVINGS = { club: 10, famille: 16, premium: 26 };

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [packages, setPackages] = useState([]);
  const [period, setPeriod] = useState("monthly"); // "monthly" | "yearly"
  const [buying, setBuying] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/packages").then((r) => setPackages(r.data)).catch(() => {});
  }, []);

  // Group packages by tier and period for easy lookup by the card
  const byKey = useMemo(() => {
    const m = {};
    for (const p of packages) m[`${p.tier}_${p.period}`] = p;
    return m;
  }, [packages]);

  const buy = async (packageId) => {
    if (!user) {
      navigate(`/login?next=/app/pricing`);
      return;
    }
    setBuying(packageId);
    setErr("");
    try {
      const origin = window.location.origin;
      const { data } = await api.post("/checkout/session", { package_id: packageId, origin_url: origin });
      window.location.href = data.url;
    } catch (e) {
      setErr(formatError(e.response?.data?.detail) || "Impossible de démarrer le paiement");
      setBuying(null);
    }
  };

  const currentTier = user?.plan_tier || null;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />
      <main id="tarifs" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">

        <div className="text-center max-w-2xl mx-auto mb-8">
          <span className="inline-block bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            Tarifs simples & justes
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-3" data-testid="pricing-title">
            Trois formules, <span className="text-terracotta italic">une seule promesse</span>
          </h1>
          <p className="text-navy/70 text-lg">
            Sans engagement · Annulation en 1 clic · Essai gratuit inclus
          </p>
        </div>

        {/* Period toggle */}
        <div className="flex justify-center mb-10" data-testid="pricing-period-toggle">
          <div className="bg-white border-2 border-cream-dark rounded-full p-1 inline-flex">
            <button
              type="button"
              onClick={() => setPeriod("monthly")}
              data-testid="pricing-period-monthly"
              className={`px-5 py-2 rounded-full font-bold text-sm transition ${
                period === "monthly" ? "bg-navy text-cream" : "text-navy/60 hover:text-navy"
              }`}
            >
              Mensuel
            </button>
            <button
              type="button"
              onClick={() => setPeriod("yearly")}
              data-testid="pricing-period-yearly"
              className={`px-5 py-2 rounded-full font-bold text-sm transition inline-flex items-center gap-2 ${
                period === "yearly" ? "bg-navy text-cream" : "text-navy/60 hover:text-navy"
              }`}
            >
              Annuel
              <span className="bg-mustard text-navy text-[10px] font-extrabold px-1.5 py-0.5 rounded-full uppercase">-16%</span>
            </button>
          </div>
        </div>

        {/* Tier grid */}
        <div className="grid lg:grid-cols-4 gap-5">
          {/* Gratuit */}
          <TierCard
            testid="pricing-tier-free"
            title="Découverte"
            price="0 €"
            period=""
            tagline="Pour tester GénéraQuiz sans engagement"
            features={[
              "Quiz du Jour quotidien",
              "5 questions par catégorie",
              "3 badges de démarrage",
              "Historique 7 jours",
            ]}
            ctaLabel={currentTier ? "Formule actuelle inférieure" : (user ? "Formule actuelle" : "Créer un compte")}
            ctaDisabled={!!currentTier}
            onCta={() => user ? null : navigate("/register")}
            highlight={!user && !currentTier}
            color="border-cream-dark"
          />

          {["club", "famille", "premium"].map((tier) => {
            const meta = TIER_META[tier];
            const Icon = meta.icon;
            const pkg = byKey[`${tier}_${period}`];
            const displayed = period === "yearly" && pkg ? (pkg.amount / 12) : pkg?.amount;
            const isCurrent = currentTier === tier;
            const canUpgrade = !!pkg;
            const label = isCurrent
              ? "Formule actuelle"
              : buying === pkg?.id
              ? "Redirection…"
              : "Choisir cette formule";
            return (
              <TierCard
                key={tier}
                testid={`pricing-tier-${tier}`}
                title={meta.title}
                price={displayed ? `${displayed.toFixed(2).replace(".", ",")} €` : "—"}
                periodLabel={period === "yearly" ? " /mois, facturé annuellement" : " /mois"}
                priceExtra={period === "yearly" && pkg ? `Soit ${pkg.amount.toFixed(2).replace(".", ",")} € par an — économie ${YEARLY_SAVINGS[tier]} €` : null}
                tagline={meta.tagline}
                features={meta.features}
                icon={Icon}
                badge={meta.badge}
                highlight={tier === "famille"}
                color={meta.color}
                ctaLabel={label}
                ctaDisabled={!canUpgrade || isCurrent || buying === pkg?.id}
                onCta={() => canUpgrade && buy(pkg.id)}
              />
            );
          })}
        </div>

        {err && (
          <div className="mt-6 max-w-lg mx-auto bg-bordeaux/10 border-2 border-bordeaux/40 rounded-xl p-4 text-bordeaux font-medium text-center" data-testid="pricing-error">
            {err}
          </div>
        )}

        {/* Reassurance strip */}
        <div className="mt-10 text-center text-sm text-navy/60 flex items-center justify-center gap-4 flex-wrap" data-testid="pricing-reassurance">
          <span className="inline-flex items-center gap-1"><Check className="w-4 h-4 text-[#3D9970]" /> Paiement sécurisé Stripe</span>
          <span className="inline-flex items-center gap-1"><Check className="w-4 h-4 text-[#3D9970]" /> Annulation en 1 clic</span>
          <span className="inline-flex items-center gap-1"><Check className="w-4 h-4 text-[#3D9970]" /> Support en français</span>
        </div>

        {/* FAQ mini */}
        <div className="mt-14 max-w-2xl mx-auto">
          <h2 className="font-display text-2xl font-bold text-navy mb-4 text-center">Questions fréquentes</h2>
          <div className="space-y-2">
            <details className="bg-white border-2 border-cream-dark rounded-2xl p-4">
              <summary className="font-bold text-navy cursor-pointer">Puis-je changer de formule à tout moment ?</summary>
              <p className="mt-2 text-navy/70">Oui, vous pouvez passer d&apos;une formule à l&apos;autre depuis votre espace Mon Compte. La différence est calculée au prorata.</p>
            </details>
            <details className="bg-white border-2 border-cream-dark rounded-2xl p-4">
              <summary className="font-bold text-navy cursor-pointer">Comment fonctionne la formule Famille ?</summary>
              <p className="mt-2 text-navy/70">Vous invitez jusqu&apos;à 5 proches par email. Ils créent leur propre compte gratuitement et bénéficient automatiquement de tous les avantages. Idéal pour connecter petits-enfants et grands-parents !</p>
            </details>
            <details className="bg-white border-2 border-cream-dark rounded-2xl p-4">
              <summary className="font-bold text-navy cursor-pointer">Puis-je annuler mon abonnement ?</summary>
              <p className="mt-2 text-navy/70">Oui, à tout moment depuis votre espace personnel. Vous gardez l&apos;accès jusqu&apos;à la fin de la période payée, puis basculez automatiquement en Découverte.</p>
            </details>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function TierCard({
  testid, title, price, periodLabel = "", priceExtra, tagline, features, icon: Icon,
  badge, highlight, color, ctaLabel, ctaDisabled, onCta,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      data-testid={testid}
      className={`relative bg-white rounded-[28px] p-6 border-2 flex flex-col ${color || "border-cream-dark"} ${
        highlight ? "shadow-warm scale-[1.02]" : ""
      }`}
    >
      {badge && (
        <div
          data-testid={`${testid}-badge`}
          className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-warm"
        >
          <Star className="w-3 h-3 inline mr-1 fill-current" />
          {badge}
        </div>
      )}
      {Icon && (
        <div className={`w-11 h-11 rounded-2xl bg-cream flex items-center justify-center mb-3`}>
          <Icon className="w-5 h-5 text-terracotta" strokeWidth={2.5} />
        </div>
      )}
      <div className="font-display text-xl font-extrabold text-navy mb-1">{title}</div>
      <div className="text-sm text-navy/60 mb-4 min-h-[40px]">{tagline}</div>
      <div className="mb-1">
        <span className="font-display text-4xl font-extrabold text-navy" data-testid={`${testid}-price`}>{price}</span>
        <span className="text-sm text-navy/60">{periodLabel}</span>
      </div>
      {priceExtra && <div className="text-xs text-terracotta font-bold mb-4">{priceExtra}</div>}
      {!priceExtra && <div className="mb-4" />}

      <ul className="space-y-2 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-navy/85">
            <Check className="w-4 h-4 text-[#3D9970] mt-0.5 shrink-0" strokeWidth={3} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onCta}
        disabled={ctaDisabled}
        data-testid={`${testid}-cta`}
        className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full text-sm transition min-h-[48px] ${
          highlight
            ? "bg-terracotta hover:bg-terracotta-dark text-white shadow-warm"
            : "bg-navy hover:bg-navy-dark text-cream"
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {ctaLabel === "Redirection…" ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
        {ctaLabel}
        {!ctaDisabled && ctaLabel !== "Redirection…" && <ArrowRight className="w-4 h-4" />}
      </button>
    </motion.div>
  );
}
