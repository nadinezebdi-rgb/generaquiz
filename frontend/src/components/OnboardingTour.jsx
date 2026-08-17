import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { X, ArrowRight, Sparkles, BookOpen, TrendingUp, Sun } from "lucide-react";

/**
 * OnboardingTour — visite guidée 60 s pour les nouvelles familles.
 *
 * Se déclenche automatiquement à la première connexion (localStorage flag).
 * Rejouable depuis le compte via `?tour=1` dans l'URL.
 * 4 étapes narratives, chaque carte : icône + titre + descriptif + CTA.
 */

const STORAGE_KEY = "generaquiz_onboarding_v1";

const STEPS = [
  {
    icon: Sun,
    color: "bg-mustard/30 border-mustard",
    title: "Bienvenue dans GénéraQuiz 👋",
    subtitle: "Une app qui rapproche les générations",
    text: "En 60 secondes, laissez-nous vous montrer les 3 choses à savoir. Jouez, souvenez-vous, transmettez — à votre rythme, tout est privé.",
    ctaLabel: "C'est parti",
    linkTo: null,
  },
  {
    icon: Sparkles,
    color: "bg-terracotta/15 border-terracotta",
    title: "1️⃣ Le Quiz du Jour ✨",
    subtitle: "5 questions chaque matin",
    text: "Un thème par jour (années 60, chansons, cuisine…). Idéal en famille : les grands-parents brillent, les petits apprennent. 5 minutes suffisent.",
    ctaLabel: "Suivant",
    linkTo: null,
  },
  {
    icon: BookOpen,
    color: "bg-bordeaux/15 border-bordeaux",
    title: "2️⃣ Mon Livre de Vie 📖",
    subtitle: "Vos souvenirs guidés en 10 chapitres",
    text: "Enfance, école, rencontres, voyages… Répondez à une question, un souvenir à la fois. Vous pouvez écrire, enregistrer votre voix, ou vous faire aider par un proche.",
    ctaLabel: "Suivant",
    linkTo: null,
  },
  {
    icon: TrendingUp,
    color: "bg-navy/15 border-navy",
    title: "3️⃣ Votre progression 🌱",
    subtitle: "Douce, jamais culpabilisante",
    text: "Chaque quiz joué et chaque souvenir consigné fait grandir votre profil. Pas de score de honte, pas de pression — juste la fierté de transmettre.",
    ctaLabel: "Explorer",
    linkTo: "/app/livre",
  },
];


export default function OnboardingTour() {
  const [step, setStep] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const already = localStorage.getItem(STORAGE_KEY);
    const forced = new URLSearchParams(window.location.search).get("tour") === "1";
    if (!already || forced) {
      // Petit délai pour laisser le dashboard finir son animation d'entrée
      const t = setTimeout(() => setOpen(true), 700);
      return () => clearTimeout(t);
    }
  }, []);

  function close() {
    setOpen(false);
    localStorage.setItem(STORAGE_KEY, "seen");
  }

  function next() {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      close();
    }
  }

  if (!open) return null;
  const s = STEPS[step];
  const Icon = s.icon;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[70] bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4"
        data-testid="onboarding-tour-overlay"
      >
        <motion.div
          key={step}
          initial={{ y: 24, opacity: 0, scale: 0.96 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: -24, opacity: 0 }}
          transition={{ duration: 0.35 }}
          className="bg-cream rounded-3xl max-w-md w-full shadow-2xl overflow-hidden relative"
        >
          <button
            onClick={close}
            data-testid="onboarding-tour-close"
            aria-label="Fermer la visite"
            className="absolute top-3 right-3 p-2 hover:bg-cream-dark rounded-full transition"
          >
            <X className="w-5 h-5 text-navy" />
          </button>

          <div className={`p-8 pt-10 border-b-4 ${s.color} flex flex-col items-center text-center`}>
            <div className="bg-white rounded-2xl p-4 shadow-warm mb-4">
              <Icon className="w-10 h-10 text-navy" />
            </div>
            <h2 className="font-display text-2xl font-extrabold text-navy mb-1" data-testid="onboarding-tour-title">
              {s.title}
            </h2>
            <p className="text-sm font-bold text-terracotta uppercase tracking-wider">
              {s.subtitle}
            </p>
          </div>

          <div className="p-6">
            <p className="text-navy/80 leading-relaxed text-base mb-6">{s.text}</p>

            {/* Dots */}
            <div className="flex justify-center gap-2 mb-5" data-testid="onboarding-tour-dots">
              {STEPS.map((_, i) => (
                <span
                  key={i}
                  className={`h-2 rounded-full transition-all ${i === step ? "w-8 bg-terracotta" : "w-2 bg-cream-dark"}`}
                />
              ))}
            </div>

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={close}
                data-testid="onboarding-tour-skip"
                className="text-sm font-bold text-navy/60 hover:text-navy underline"
              >
                Passer la visite
              </button>
              {s.linkTo ? (
                <Link
                  to={s.linkTo}
                  onClick={close}
                  data-testid="onboarding-tour-cta"
                  className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2.5 rounded-full hover:bg-terracotta-dark transition shadow-warm"
                >
                  {s.ctaLabel} <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={next}
                  data-testid="onboarding-tour-next"
                  className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2.5 rounded-full hover:bg-terracotta-dark transition shadow-warm"
                >
                  {s.ctaLabel} <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
