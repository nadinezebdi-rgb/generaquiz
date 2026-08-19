import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Star, Sparkles, Gift, ChevronRight, Phone, Mail } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { PLANS, GIFTS, pricePresentation, annualDiscountBadge, fmt } from "@/config/pricing";
import ProPricing from "@/components/ProPricing";
import PrintedBookPricing from "@/components/PrintedBookPricing";

/**
 * Pricing — Nouvelle grille tarifaire GénéraQuiz.
 *
 * 4 plans B2C (Découverte / Solo / Famille / Héritage) + section "Offrir"
 * (cadeaux) + Livre imprimé + Offre Pro. Toutes les valeurs viennent de
 * /config/pricing.js.
 */

export default function Pricing() {
  const [period, setPeriod] = useState("yearly"); // 'monthly' | 'yearly'
  const annualBadge = annualDiscountBadge();

  function switchToYearly() { setPeriod("yearly"); }

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* HEADER */}
        <div className="text-center max-w-3xl mx-auto mb-10">
          <span className="inline-block bg-cream border-2 border-mustard-dark text-navy font-bold px-4 py-1.5 rounded-full text-sm mb-4">
            Tarifs simples
          </span>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold mb-3" data-testid="pricing-h1">
            Choisissez ce qui <span className="text-terracotta italic">vous ressemble</span>
          </h1>
          <p className="text-lg text-navy/70">
            Sans engagement · Résiliable à tout moment · Support en français
          </p>
        </div>

        {/* TOGGLE Mensuel / Annuel */}
        <div className="flex items-center justify-center gap-3 mb-10" data-testid="pricing-toggle">
          <button
            type="button"
            onClick={() => setPeriod("monthly")}
            data-testid="pricing-toggle-monthly"
            className={`px-5 py-2 rounded-full font-bold text-sm transition ${period === "monthly" ? "bg-navy text-cream" : "text-navy/60 hover:text-navy"}`}
          >
            Mensuel
          </button>
          <button
            type="button"
            onClick={() => setPeriod("yearly")}
            data-testid="pricing-toggle-yearly"
            className={`inline-flex items-center gap-2 px-5 py-2 rounded-full font-bold text-sm transition ${period === "yearly" ? "bg-navy text-cream" : "text-navy/60 hover:text-navy"}`}
          >
            Annuel
            <span className="bg-terracotta text-white text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full">
              {annualBadge}
            </span>
          </button>
        </div>

        {/* PLANS */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {PLANS.map((plan) => (
            <PlanCard key={plan.id} plan={plan} period={period} switchToYearly={switchToYearly} />
          ))}
        </div>

        {period === "yearly" && (
          <p className="text-xs text-navy/50 text-center mb-14" data-testid="pricing-legal-annual">
            Prix TTC. Abonnement annuel débité en une fois, renouvelable par tacite reconduction. Résiliable à tout moment.
          </p>
        )}

        {/* ============ SECTION OFFRIR ============ */}
        <section className="mt-14 mb-14" data-testid="offrir-section">
          <div className="text-center max-w-3xl mx-auto mb-8">
            <span className="inline-block bg-terracotta text-white font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
              <Gift className="w-3.5 h-3.5 inline mr-1" /> Offrir GénéraQuiz
            </span>
            <h2 className="font-display text-3xl md:text-4xl font-extrabold mb-3" data-testid="offrir-title">
              Le plus beau cadeau à faire à ses <span className="text-terracotta italic">parents ou grands-parents</span>
            </h2>
            <p className="text-navy/70">
              Un abonnement, un coffret, ou simplement leur Livre de Vie — à offrir pour un anniversaire, une fête ou pour Noël.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            {GIFTS.map((g) => (
              <GiftCard key={g.id} gift={g} />
            ))}
          </div>
          <p className="text-xs text-navy/50 text-center mt-4">
            Chaque cadeau : destinataire, message personnalisé et choix de la date d&apos;envoi. Génération d&apos;un code cadeau à usage unique après paiement.
          </p>
        </section>

        {/* ============ LIVRE IMPRIMÉ ============ */}
        <PrintedBookPricing />

        {/* ============ OFFRE PRO ============ */}
        <ProPricing />
      </main>

      <Footer />
    </div>
  );
}

function PlanCard({ plan, period, switchToYearly }) {
  const pres = pricePresentation(plan, period);
  const isFree = plan.mensuel === 0 && plan.annuel === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className={`relative bg-white rounded-3xl border-2 p-6 flex flex-col ${
        plan.populaire ? "border-terracotta shadow-warm ring-4 ring-terracotta/15 scale-[1.02]" : "border-cream-dark"
      }`}
      data-testid={`plan-card-${plan.id}`}
    >
      {plan.populaire && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full inline-flex items-center gap-1 shadow-warm">
          <Star className="w-3 h-3 fill-current" /> Le plus populaire
        </span>
      )}

      <h3 className="font-display text-2xl font-extrabold text-navy mb-1">{plan.nom}</h3>
      <p className="text-sm text-navy/60 mb-4 min-h-[36px]">{plan.tagline}</p>

      {/* Prix : ordre STRICT du brief */}
      <div className="mb-4">
        {period === "yearly" && pres.reference != null && pres.reference !== plan.annuel && (
          <div className="text-sm text-navy/40 line-through" data-testid={`plan-ref-${plan.id}`}>
            {fmt(pres.reference)}
          </div>
        )}
        <div className="flex items-baseline gap-1">
          <span className="font-display text-4xl font-extrabold text-bordeaux" data-testid={`plan-price-${plan.id}`}>
            {pres.main}
          </span>
          {pres.suffix && <span className="text-sm text-navy/60">{pres.suffix}</span>}
        </div>
        {period === "yearly" && pres.monthlyEquivalent != null && (
          <p className="text-xs text-navy/50 mt-1" data-testid={`plan-equiv-${plan.id}`}>
            soit {fmt(pres.monthlyEquivalent)}/mois
          </p>
        )}
        {period === "yearly" && pres.economie != null && pres.economie > 0 && (
          <span
            className="inline-flex items-center gap-1 bg-[#3D9970]/15 text-[#2A7350] font-bold px-2 py-0.5 rounded-full text-xs mt-2"
            data-testid={`plan-eco-${plan.id}`}
          >
            <Sparkles className="w-3 h-3" /> Économisez {fmt(pres.economie)} (−{pres.pourcentage} %)
          </span>
        )}
        {isFree && <p className="text-xs text-navy/50 mt-1">Sans carte bancaire · à vie</p>}
        {pres.note && !isFree && (
          <p className="text-xs text-mustard-dark mt-2 font-semibold">{pres.note}</p>
        )}
      </div>

      <p className="text-xs text-navy/50 mb-3 uppercase tracking-wider font-bold">
        {plan.comptes} compte{plan.comptes > 1 ? "s" : ""}
      </p>

      <ul className="space-y-2 mb-5 flex-1">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
            <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      {plan.argumentValue && period === "yearly" && (
        <div className="bg-cream border border-cream-dark rounded-xl p-3 mb-4 text-xs text-navy/70" data-testid={`plan-argument-${plan.id}`}>
          {plan.argumentValue}
        </div>
      )}

      {pres.available ? (
        plan.ctaTo ? (
          <Link
            to={plan.ctaTo}
            data-testid={`plan-cta-${plan.id}`}
            className="w-full inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark transition min-h-[52px]"
          >
            {plan.cta} <ChevronRight className="w-4 h-4" />
          </Link>
        ) : (
          <Link
            to={`/app/checkout?plan=${plan.id}&period=${period}`}
            data-testid={`plan-cta-${plan.id}`}
            className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
              plan.populaire ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm" : "bg-navy text-cream hover:bg-navy-dark"
            }`}
          >
            {plan.cta} <ChevronRight className="w-4 h-4" />
          </Link>
        )
      ) : (
        <button
          type="button"
          onClick={switchToYearly}
          data-testid={`plan-cta-${plan.id}`}
          className="w-full inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy font-bold px-5 py-3 rounded-full hover:bg-navy hover:text-cream transition min-h-[52px]"
        >
          Passer en annuel <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </motion.div>
  );
}

function GiftCard({ gift }) {
  const mailtoSubject = encodeURIComponent(`Offrir : ${gift.nom}`);
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
        gift.highlight ? "border-terracotta ring-4 ring-terracotta/15 shadow-warm" : "border-cream-dark"
      }`}
      data-testid={`gift-card-${gift.id}`}
    >
      {gift.badge && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-warm">
          {gift.badge}
        </span>
      )}
      <Gift className="w-8 h-8 text-terracotta mb-3" />
      <h3 className="font-display text-xl font-extrabold text-navy mb-1">{gift.nom}</h3>
      <div className="font-display text-3xl font-extrabold text-bordeaux mb-2">{fmt(gift.prix)}</div>
      <p className="text-sm text-navy/70 mb-4 flex-1">{gift.description}</p>
      <a
        href={`mailto:contact@generaquiz.fr?subject=${mailtoSubject}`}
        data-testid={`gift-cta-${gift.id}`}
        className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
          gift.highlight ? "bg-terracotta text-white hover:bg-terracotta-dark" : "bg-navy text-cream hover:bg-navy-dark"
        }`}
      >
        <Gift className="w-4 h-4" /> Offrir maintenant
      </a>
    </motion.div>
  );
}
