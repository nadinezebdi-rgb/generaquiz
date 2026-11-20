import { useState, useEffect, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Check, Gift, ChevronRight, Users } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { PLANS, GIFTS, fmt, isChristmasPromo, packageFor } from "@/config/pricing";
import { PeriodToggle, PromoHeader, PlanPrice, CheckoutRecap } from "@/components/pricing/Offer";
import ProPricing from "@/components/ProPricing";
import PrintedBookPricing from "@/components/PrintedBookPricing";
import { useAuth } from "@/contexts/AuthContext";
import { useGiftOffers } from "@/lib/gifts";

/**
 * Pricing — Nouvelle grille tarifaire GénéraQuiz.
 *
 * 3 plans B2C (Découverte / Solo / Famille) + section "Offrir"
 * (cadeaux) + Livre imprimé + Offre Pro. Toutes les valeurs viennent de
 * /config/pricing.js.
 */

export default function Pricing() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [period, setPeriod] = useState(searchParams.get("periode") === "monthly" ? "monthly" : "yearly");
  const promo = isChristmasPromo();
  const [recapPkg, setRecapPkg] = useState(null);
  const closeRecap = useCallback(() => setRecapPkg(null), []);
  const { user, loading } = useAuth();
  const giftOffers = useGiftOffers();

  // Reprise du checkout après connexion / inscription : si un pkg est en attente
  // (URL ?pkg=... ou sessionStorage), on relance dès que l'utilisateur est
  // authentifié.
  useEffect(() => {
    if (loading) return;
    const urlPkg = searchParams.get("pkg");
    let pending = urlPkg;
    if (!pending) {
      try { pending = sessionStorage.getItem("pending_checkout_package"); } catch { /* storage bloqué */ }
    }
    if (!pending) return;
    if (!user) return; // pas connecté → on garde le pkg et on attend
    // On nettoie AVANT la redirection Stripe pour éviter les boucles
    try { sessionStorage.removeItem("pending_checkout_package"); } catch { /* storage bloqué */ }
    if (urlPkg) {
      const next = new URLSearchParams(searchParams);
      next.delete("pkg");
      setSearchParams(next, { replace: true });
    }
    setRecapPkg(pending); // le récapitulatif s'affiche toujours avant la saisie de la carte
  }, [user, loading, searchParams, setSearchParams]);

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
          <PromoHeader promo={promo} />
        </div>

        <PeriodToggle period={period} setPeriod={setPeriod} promo={promo} />

        {/* PLANS */}
        <div className="grid md:grid-cols-3 gap-5 mb-6 max-w-5xl mx-auto">
          {PLANS.map((plan) => (
            <PlanCard key={plan.id} plan={plan} period={period} promo={promo} onChoose={setRecapPkg} />
          ))}
        </div>

        {promo && (
          <p className="text-base text-navy font-bold text-center mb-2" data-testid="pricing-annual-note">
            Promo annuelle : les 12 mois commencent à la première connexion. Idéal à offrir pour Noël 🎁
          </p>
        )}
        <p className="text-sm text-navy text-center mb-14" data-testid="pricing-legal">
          Prix TTC. {period === "yearly"
            ? `Abonnement annuel débité en une fois, renouvelé automatiquement chaque année à ${fmt(69, { integer: true })} (Solo) ou ${fmt(99, { integer: true })} (Famille), rappel par e-mail 30 jours avant.`
            : "Abonnement mensuel sans engagement."} Résiliable à tout moment en un clic.
        </p>
        <CheckoutRecap packageId={recapPkg} onClose={closeRecap} />

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
              Une année de jeux à partager — à offrir pour un anniversaire, une fête ou pour Noël.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4 max-w-3xl mx-auto">
            {GIFTS.map((g) => (
              <GiftCard key={g.id} gift={g} offer={giftOffers?.offers.find((o) => o.id === g.id)} />
            ))}
          </div>
          <p className="text-xs text-navy/50 text-center mt-4">
            Après le paiement : une carte cadeau à imprimer avec un code à usage unique. L&apos;année commence le jour de l&apos;activation.
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

function PlanCard({ plan, period, promo, onChoose }) {
  const packageId = packageFor(plan, period, promo);
  const featured = Boolean(plan.badge);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className={`relative bg-white rounded-3xl border-2 p-6 flex flex-col ${
        featured ? "border-terracotta shadow-warm ring-4 ring-terracotta/15" : "border-cream-dark"
      }`}
      data-testid={`plan-card-${plan.id}`}
    >
      {featured && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full inline-flex items-center gap-1 shadow-warm" data-testid={`plan-badge-${plan.id}`}>
          <Users className="w-3 h-3" /> {plan.badge}
        </span>
      )}

      <h3 className="font-display text-2xl font-extrabold text-navy mb-1">{plan.nom}</h3>
      <p className="text-sm text-navy/60 mb-4">{plan.tagline}</p>

      <PlanPrice plan={plan} period={period} promo={promo} />

      <p className="text-xs text-navy/60 mb-3 uppercase tracking-wider font-bold" data-testid={`plan-access-${plan.id}`}>
        {plan.acces}
      </p>

      <ul className="space-y-2 mb-5 flex-1">
        {plan.features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
            <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      {plan.ctaTo ? (
        <Link
          to={plan.ctaTo}
          data-testid={`plan-cta-${plan.id}`}
          className="w-full inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark transition-colors min-h-[52px]"
        >
          {plan.cta} <ChevronRight className="w-4 h-4" />
        </Link>
      ) : (
        <button
          type="button"
          onClick={() => onChoose(packageId)}
          disabled={!packageId}
          data-testid={`plan-cta-${plan.id}`}
          className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition-colors min-h-[52px] disabled:opacity-70 disabled:cursor-not-allowed ${
            featured ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm" : "bg-navy text-cream hover:bg-navy-dark"
          }`}
        >
          {plan.cta} <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </motion.div>
  );
}

function GiftCard({ gift, offer }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
        gift.highlight ? "border-terracotta ring-4 ring-terracotta/15 shadow-warm" : "border-cream-dark"
      }`}
      data-testid={`gift-card-${gift.id}`}
    >
      <Gift className="w-8 h-8 text-terracotta mb-3" />
      <h3 className="font-display text-xl font-extrabold text-navy mb-1">{gift.nom}</h3>
      <div className="flex items-baseline gap-2 mb-2" data-testid={`gift-price-${gift.id}`}>
        {offer?.regular_price && <span className="text-navy/50 line-through text-lg">{fmt(offer.regular_price, { integer: true })}</span>}
        <span className="font-display text-3xl font-extrabold text-bordeaux">{offer ? fmt(offer.price, { integer: true }) : "…"}</span>
        <span className="text-sm text-navy/60">pour 1 an</span>
      </div>
      <p className="text-sm text-navy/70 mb-4 flex-1">{gift.description}</p>
      <Link
        to={`/offrir?offre=${gift.id}`}
        data-testid={`gift-cta-${gift.id}`}
        className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition-colors min-h-[52px] ${
          gift.highlight ? "bg-terracotta text-white hover:bg-terracotta-dark" : "bg-navy text-cream hover:bg-navy-dark"
        }`}
      >
        <Gift className="w-4 h-4" /> Offrir
      </Link>
    </motion.div>
  );
}
