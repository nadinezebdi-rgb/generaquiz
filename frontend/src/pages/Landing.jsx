import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Play, Users, Heart, Sparkles, Check, ArrowRight, Star,
  Brain, Music, Film, Phone, Landmark, Utensils, Book,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import StatsSection from "@/components/StatsSection";
import PlatformSection from "@/components/PlatformSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import PrintedBookPricing from "@/components/PrintedBookPricing";
import ProPricing from "@/components/ProPricing";
import HeroPhoneDemo from "@/components/HeroPhoneDemo";
import TestimonialsSection from "@/components/TestimonialsSection";
import { api, BACKEND_URL } from "@/lib/api";
import { PLANS, pricePresentation, annualDiscountBadge, fmt } from "@/config/pricing";

const ICON_MAP = { tv: Film, music: Music, film: Film, phone: Phone, landmark: Landmark, utensils: Utensils, sparkles: Sparkles, book: Book };

export default function Landing() {
  const [categories, setCategories] = useState([]);
  const [packages, setPackages] = useState([]);

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    api.get("/packages").then((r) => setPackages(r.data)).catch(() => {});
  }, []);

  return (
    <div className="paper-bg min-h-screen">
      <Navbar variant="landing" />

      {/* ============ HERO ============ */}
      <section className="relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-mustard/30 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 rounded-full bg-terracotta/20 blur-3xl pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24 grid lg:grid-cols-12 gap-10 items-center relative">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-7"
          >
            <div className="inline-flex items-center gap-2 bg-cream border-2 border-mustard-dark text-navy font-bold px-4 py-2 rounded-full text-sm mb-6" data-testid="hero-pill">
              <Star className="w-4 h-4 text-terracotta fill-terracotta" /> Jouer. Se souvenir. Transmettre.
            </div>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy leading-[1.1] mb-6" data-testid="hero-title">
              5 minutes pour jouer.<br />
              <span className="text-terracotta italic">Toute une vie</span><br />
              à raconter.
            </h1>
            <p className="text-lg sm:text-xl text-navy/80 leading-relaxed max-w-2xl mb-6" data-testid="hero-subtitle">
              GénéraQuiz fait revivre les souvenirs grâce au jeu
              et rapproche les générations pour mieux <strong>transmettre les histoires familiales</strong>.
            </p>

            {/* Rating + social proof line */}
            <div className="flex items-center gap-3 mb-8 flex-wrap" data-testid="hero-rating">
              <div className="flex items-center gap-0.5" aria-label="5 étoiles sur 5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-mustard-dark fill-mustard-dark" />
                ))}
              </div>
              <span className="text-sm font-bold text-navy/80">
                Déjà adopté par des familles partout en France
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link
                to="/register"
                data-testid="hero-cta-register"
                className="inline-flex items-center justify-center gap-3 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-xl px-8 py-5 rounded-full shadow-warm transition min-h-[64px]"
              >
                <Play className="w-6 h-6" fill="currentColor" />
                Commencer gratuitement
              </Link>
              <a
                href="#how-it-works"
                data-testid="hero-cta-discover"
                className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream font-bold text-lg px-6 py-5 rounded-full transition min-h-[64px]"
              >
                Découvrir GénéraQuiz
              </a>
            </div>

            <p className="text-sm text-navy/60 mt-4" data-testid="hero-reassurance">
              Sans engagement · Aucune carte bancaire requise · Prêt en 30 secondes
            </p>
          </motion.div>

          {/* Animated phone demo */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="lg:col-span-5 relative"
          >
            <HeroPhoneDemo />
          </motion.div>
        </div>

        {/* Marquee tape */}
        <div className="bg-bordeaux text-cream py-3 overflow-hidden border-y-2 border-bordeaux">
          <div className="marquee-track inline-flex whitespace-nowrap font-display text-xl">
            {Array.from({ length: 2 }).map((_, i) => (
              <span key={i} className="mx-8">
                ✦ Mémoire vive &nbsp;·&nbsp; Souvenirs partagés &nbsp;·&nbsp; Culture française &nbsp;·&nbsp; Jeux pour tous &nbsp;·&nbsp; Famille connectée &nbsp;·&nbsp; Plaisir d&apos;apprendre &nbsp;·&nbsp;
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ============ TESTIMONIALS ============ */}
      <TestimonialsSection />

      {/* ============ DAILY QUIZ CTA ============ */}
      <section className="py-12 lg:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative bg-gradient-to-br from-bordeaux via-navy to-bordeaux rounded-[36px] p-8 md:p-12 shadow-warm overflow-hidden"
          >
            <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-mustard/20 blur-3xl pointer-events-none" />
            <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-terracotta/20 blur-3xl pointer-events-none" />
            <div className="relative grid md:grid-cols-2 gap-8 items-center">
              <div className="text-white">
                <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-2 rounded-full text-sm mb-5">
                  <Sparkles className="w-4 h-4" /> Nouveauté · 100% gratuit
                </div>
                <h2 className="font-display text-4xl md:text-5xl font-extrabold mb-4 leading-tight">
                  Le <span className="text-mustard italic">Quiz du Jour</span><br />vous attend !
                </h2>
                <p className="text-cream/90 text-lg mb-6 leading-relaxed">
                  5 questions toutes catégories confondues, les mêmes pour tout le monde.
                  Comparez votre score à celui des autres joueurs et tentez d&apos;entrer dans le Top 10 quotidien.
                </p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <Link
                    to="/quiz-du-jour"
                    data-testid="landing-daily-cta"
                    className="inline-flex items-center justify-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold text-lg px-8 py-4 rounded-full transition min-h-[60px]"
                  >
                    Jouer le Quiz du Jour <ArrowRight className="w-5 h-5" />
                  </Link>
                  <span className="inline-flex items-center justify-center gap-2 text-cream/80 text-sm">
                    Pas besoin de compte — accès immédiat
                  </span>
                </div>
              </div>
              <div className="relative hidden md:block">
                <div className="absolute -inset-4 bg-mustard/30 rounded-3xl rotate-2" />
                <div className="relative bg-cream rounded-3xl p-6 text-navy">
                  <div className="font-display text-sm font-bold uppercase tracking-wider text-navy/60 mb-3">Comment ça marche</div>
                  <ul className="space-y-3">
                    {[
                      "5 questions tirées au sort chaque jour",
                      "Mêmes questions pour tous les joueurs",
                      "Classement quotidien Top 10",
                      "Compte gratuit pour apparaître au classement",
                    ].map((line) => (
                      <li key={line} className="flex items-start gap-2.5">
                        <Check className="w-5 h-5 text-terracotta shrink-0 mt-0.5" strokeWidth={3} />
                        <span className="font-medium">{line}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============ STATS PUBLIQUES ============ */}
      <StatsSection />

      {/* ============ CATEGORIES ============ */}
      <section id="categories" className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-14">
            <span className="inline-block bg-mustard text-navy font-bold px-4 py-1 rounded-full text-sm mb-4">Choisissez votre thème</span>
            <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-4">
              Neuf univers, neuf personnages
            </h2>
            <p className="text-xl text-navy/70 leading-relaxed">
              Chaque catégorie a son ambassadeur caricaturé pour vous accompagner dans la découverte —
              avec notre toute dernière <strong>Voyages &amp; régions de France</strong> guidée par Jeanne la Voyageuse.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-7">
            {categories.map((cat, idx) => {
              const Icon = ICON_MAP[cat.icon] || Sparkles;
              return (
                <motion.div
                  key={cat.id}
                  data-testid={`category-card-${cat.id}`}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.05 }}
                  className="group relative bg-white border-2 border-cream-dark rounded-[28px] p-6 hover:border-terracotta hover:-translate-y-1 transition-all shadow-soft hover:shadow-warm overflow-hidden"
                >
                  <div
                    className="absolute -top-12 -right-12 w-48 h-48 rounded-full opacity-15 group-hover:opacity-25 transition"
                    style={{ backgroundColor: cat.color }}
                  />
                  {cat.id === "voyages-france" && (
                    <span
                      data-testid={`category-badge-nouveau-${cat.id}`}
                      className="absolute top-3 right-3 z-10 inline-flex items-center gap-1 bg-terracotta text-white text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full shadow-warm"
                    >
                      ✨ Nouveau
                    </span>
                  )}
                  <div className="relative">
                    <div className="aspect-square w-32 mx-auto rounded-3xl overflow-hidden bg-cream border-2 border-cream-dark mb-5">
                      <img
                        src={`${BACKEND_URL}${cat.mascot_image}`}
                        alt={cat.mascot_name}
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                      />
                    </div>
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Icon className="w-5 h-5" style={{ color: cat.color }} strokeWidth={2.5} />
                      <span className="text-xs font-bold uppercase tracking-wider text-navy/60">{cat.count} questions</span>
                    </div>
                    <h3 className="font-display text-2xl font-bold text-navy text-center mb-2">{cat.title}</h3>
                    <p className="text-navy/70 text-center mb-4">{cat.description}</p>
                    <div className="text-center">
                      <span className="inline-block bg-cream text-navy font-bold text-sm px-3 py-1 rounded-full">
                        Avec {cat.mascot_name}
                      </span>
                    </div>
                    <Link
                      to="/register"
                      className="mt-5 w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-full bg-navy text-white font-bold hover:bg-terracotta transition"
                    >
                      Découvrir <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ============ DEMO QUIZ ============ */}
      <DemoQuiz />

      {/* ============ COMMENT ÇA MARCHE (Jouer → Se souvenir → Raconter → Transmettre) ============ */}
      <HowItWorksSection />

      {/* ============ PLATFORM (activities + word games) ============ */}
      <PlatformSection />

      {/* ============ PRICING (aperçu Découverte / Solo / Famille / Héritage) ============ */}
      <section id="tarifs" className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="inline-block bg-cream border-2 border-mustard-dark text-navy font-bold px-4 py-1 rounded-full text-sm mb-4">Tarifs simples</span>
            <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-3">
              Choisissez ce qui <span className="text-terracotta italic">vous ressemble</span>
            </h2>
            <p className="text-lg text-navy/70">
              Sans engagement · Résiliable à tout moment · Support en français
            </p>
            <p className="mt-3 text-sm text-terracotta font-bold">
              <Sparkles className="w-3.5 h-3.5 inline mr-1" />
              {annualDiscountBadge()} en formule annuelle
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            {PLANS.map((p) => <LandingPlanCard key={p.id} plan={p} />)}
          </div>

          <div className="text-center mb-14">
            <Link
              to="/app/pricing"
              data-testid="landing-see-all-pricing"
              className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-6 py-3 rounded-full hover:bg-navy-dark transition"
            >
              Voir tous les tarifs, cadeaux & livre imprimé <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Livre imprimé + Offre Pro (EHPAD Wivy-style) — visibles directement depuis la landing */}
          <PrintedBookPricing />
          <ProPricing />
        </div>
      </section>

      <Footer />
    </div>
  );
}

function LandingPlanCard({ plan }) {
  // Aperçu depuis la Landing : vue annuelle (mise en avant de l'économie), CTA vers /app/pricing.
  const pres = pricePresentation(plan, "yearly");
  const isFree = plan.mensuel === 0 && plan.annuel === 0;
  const ctaTo = plan.ctaTo || "/app/pricing";
  return (
    <div
      data-testid={`landing-plan-${plan.id}`}
      className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
        plan.populaire
          ? "border-terracotta shadow-warm ring-4 ring-terracotta/15 scale-[1.02]"
          : "border-cream-dark"
      }`}
    >
      {plan.populaire && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full inline-flex items-center gap-1 shadow-warm">
          <Star className="w-3 h-3 fill-current" /> Le plus populaire
        </span>
      )}
      <h3 className="font-display text-2xl font-extrabold text-navy mb-1">{plan.nom}</h3>
      <p className="text-sm text-navy/60 mb-4 min-h-[36px]">{plan.tagline}</p>

      <div className="mb-4">
        {pres.reference != null && pres.reference !== plan.annuel && (
          <div className="text-sm text-navy/40 line-through">{fmt(pres.reference)}</div>
        )}
        <div className="flex items-baseline gap-1">
          <span className="font-display text-4xl font-extrabold text-bordeaux">{pres.main}</span>
          {pres.suffix && <span className="text-sm text-navy/60">{pres.suffix}</span>}
        </div>
        {pres.monthlyEquivalent != null && (
          <p className="text-xs text-navy/50 mt-1">soit {fmt(pres.monthlyEquivalent)}/mois</p>
        )}
        {pres.economie != null && pres.economie > 0 && (
          <span className="inline-flex items-center gap-1 bg-[#3D9970]/15 text-[#2A7350] font-bold px-2 py-0.5 rounded-full text-xs mt-2">
            <Sparkles className="w-3 h-3" /> Économisez {fmt(pres.economie)} (−{pres.pourcentage} %)
          </span>
        )}
        {isFree && <p className="text-xs text-navy/50 mt-1">Sans carte bancaire · à vie</p>}
      </div>

      <p className="text-xs text-navy/50 mb-3 uppercase tracking-wider font-bold">
        {plan.comptes} compte{plan.comptes > 1 ? "s" : ""}
      </p>

      <ul className="space-y-2 mb-5 flex-1">
        {plan.features.slice(0, 5).map((f) => (
          <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
            <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <Link
        to={ctaTo}
        data-testid={`landing-plan-cta-${plan.id}`}
        className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
          plan.populaire
            ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm"
            : "bg-navy text-cream hover:bg-navy-dark"
        }`}
      >
        {plan.cta} <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}

function DemoQuiz() {
  const sample = {
    question: "Quel chanteur français a composé et interprété « La Mer » en 1946 ?",
    options: ["Édith Piaf", "Charles Trenet", "Jacques Brel", "Georges Brassens"],
    correct: 1,
    explanation: "Charles Trenet a composé « La Mer » en 1943 et l'a enregistrée en 1946.",
    category: "Chansons",
  };
  const [selected, setSelected] = useState(null);

  return (
    <section id="demo" className="py-20 lg:py-28 cream-bg relative">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <span className="inline-block bg-terracotta text-white font-bold px-4 py-1 rounded-full text-sm mb-4">Essai gratuit</span>
          <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-3">Testez-vous tout de suite !</h2>
          <p className="text-xl text-navy/70">Une question pour découvrir la plateforme.</p>
        </div>

        <div className="bg-white border-4 border-navy rounded-[32px] p-8 md:p-12 shadow-warm">
          <div className="flex justify-between items-center mb-6">
            <span className="text-sm font-bold uppercase tracking-wider text-navy/60">Question 1 / 1</span>
            <span className="bg-cream text-navy font-bold text-sm px-3 py-1 rounded-full border-2 border-cream-dark">{sample.category}</span>
          </div>

          <h3 className="font-display text-2xl md:text-3xl font-bold text-navy leading-snug mb-8">
            {sample.question}
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
            {sample.options.map((opt, i) => {
              let cls = "bg-white border-2 border-cream-dark text-navy hover:border-terracotta hover:bg-terracotta/5";
              if (selected !== null) {
                if (i === sample.correct) cls = "bg-[#3D9970]/15 border-2 border-[#3D9970] text-navy";
                else if (i === selected) cls = "bg-[#D9534F]/15 border-2 border-[#D9534F] text-navy";
                else cls = "bg-cream border-2 border-cream-dark text-navy/50";
              }
              return (
                <button
                  key={i}
                  data-testid={`demo-option-${i}`}
                  onClick={() => selected === null && setSelected(i)}
                  disabled={selected !== null}
                  className={`text-left px-6 py-5 rounded-2xl font-semibold text-lg transition min-h-[72px] ${cls}`}
                >
                  <span className="font-display text-xl mr-2 text-terracotta">{String.fromCharCode(65 + i)}.</span>
                  {opt}
                </button>
              );
            })}
          </div>

          {selected !== null && (
            <div
              className={`rounded-2xl p-5 border-2 fade-up ${
                selected === sample.correct
                  ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                  : "bg-[#D9534F]/10 border-[#D9534F]/40"
              }`}
              data-testid="demo-feedback"
            >
              <p className="font-display text-xl font-bold text-navy mb-1">
                {selected === sample.correct ? "✅ Bonne réponse !" : "❌ Pas tout à fait..."}
              </p>
              <p className="text-navy/80">{sample.explanation}</p>
              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  to="/register"
                  data-testid="demo-cta-register"
                  className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm transition"
                >
                  Continuer avec un compte gratuit <ArrowRight className="w-5 h-5" />
                </Link>
                <button
                  data-testid="demo-reset"
                  onClick={() => setSelected(null)}
                  className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-white font-bold px-6 py-3 rounded-full transition"
                >
                  Rejouer
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
