import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Play, MessageCircle, Sparkles, HeartPulse, Moon, Apple, Brain, Footprints, Users } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { DailyTipCard } from "@/components/DailyTipCard";
import { BACKEND_URL } from "@/lib/api";

const SAMPLES = [
  { q: "Combien de portions de fruits et légumes est-il recommandé de manger chaque jour ?", a: "5 par jour", Icon: Apple },
  { q: "Quelle vitamine notre peau fabrique-t-elle grâce au soleil ?", a: "La vitamine D", Icon: Sparkles },
  { q: "Combien de minutes d'activité modérée par semaine l'OMS recommande-t-elle ?", a: "150 minutes", Icon: Footprints },
  { q: "Quelle hormone, produite la nuit, aide à réguler le sommeil ?", a: "La mélatonine", Icon: Moon },
  { q: "Jusqu'à quel âge a vécu la Française Jeanne Calment ?", a: "122 ans", Icon: HeartPulse },
  { q: "Quelle zone du cerveau, au nom d'animal marin, joue un rôle clé dans la mémoire ?", a: "L'hippocampe", Icon: Brain },
];

const THEMES = ["Alimentation", "Activité physique", "Sommeil", "Mémoire", "Lien social", "Prévention"];

const PLAY_TO = "/register?next=/app/quiz/bien-vieillir";

export default function BienVieillirShowcase() {
  const [revealed, setRevealed] = useState({});

  useEffect(() => {
    const prev = document.title;
    document.title = "Bien vieillir : le quiz santé et mémoire pour seniors | GénéraQuiz";
    const meta = document.querySelector('meta[name="description"]');
    const prevDesc = meta?.getAttribute("content");
    meta?.setAttribute("content", "Quiz Bien vieillir : alimentation, sommeil, mémoire, activité physique. 140 questions vérifiées et un conseil santé chaque jour avec Lucienne la Pétillante.");
    return () => {
      document.title = prev;
      if (meta && prevDesc) meta.setAttribute("content", prevDesc);
    };
  }, []);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />
      <main data-testid="bien-vieillir-showcase">
        <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-16">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <span className="inline-flex items-center gap-2 bg-[#6A994E]/20 text-navy font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-4">
                <HeartPulse className="w-3.5 h-3.5 text-[#6A994E]" /> Nouveau thème
              </span>
              <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy leading-[1.05] mb-4">
                Bien <span className="text-[#6A994E] italic">vieillir</span>
              </h1>
              <p className="text-base md:text-lg text-navy/80 leading-relaxed mb-6">
                Santé, mémoire, alimentation, sommeil et petites astuces pour vivre longtemps en forme. Un quiz à jouer en famille, avec la complicité de <b>Lucienne la Pétillante</b>.
              </p>
              <div className="flex flex-wrap gap-2 mb-7" data-testid="bien-vieillir-themes">
                {THEMES.map((t) => (
                  <span key={t} className="text-xs font-bold text-navy bg-white border-2 border-cream-dark px-3 py-1 rounded-full">{t}</span>
                ))}
              </div>
              <div className="flex gap-3 flex-wrap">
                <Link
                  to={PLAY_TO}
                  data-testid="bien-vieillir-cta-play"
                  className="inline-flex items-center gap-2 bg-[#6A994E] text-white font-bold px-6 py-3 rounded-full hover:bg-[#557d3e] transition-colors shadow-warm"
                >
                  <Play className="w-5 h-5" /> Jouer gratuitement
                </Link>
                <Link
                  to="/quiz-du-jour"
                  data-testid="bien-vieillir-cta-daily"
                  className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full hover:bg-navy hover:text-white transition-colors"
                >
                  Essayer le Quiz du jour
                </Link>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.92, rotate: 3 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="relative"
            >
              <div className="absolute -inset-4 bg-[#6A994E]/15 rounded-full blur-3xl" />
              <img
                src={`${BACKEND_URL}/api/static/mascots/bien-vieillir.png`}
                alt="Lucienne la Pétillante, mascotte du thème Bien vieillir"
                className="relative w-full max-w-md mx-auto rounded-3xl shadow-2xl"
                data-testid="bien-vieillir-lucienne-image"
              />
              <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-full px-5 py-2 shadow-warm border-2 border-cream-dark whitespace-nowrap">
                <span className="font-display font-extrabold text-navy">Lucienne la Pétillante</span>
              </div>
            </motion.div>
          </div>
        </section>

        <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-4">
          <DailyTipCard ctaTo={PLAY_TO} ctaLabel="Jouer au quiz Bien vieillir" />
        </section>

        <section className="bg-white py-16">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-10">
              <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
                <Sparkles className="w-3.5 h-3.5" /> Un aperçu
              </span>
              <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy">Quelques questions qui vous attendent</h2>
              <p className="text-navy/70 mt-2 max-w-2xl">Touchez une carte pour voir la réponse. 7 niveaux, du plus simple au plus pointu.</p>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {SAMPLES.map(({ q, a, Icon }, i) => (
                <motion.button
                  type="button"
                  key={q}
                  onClick={() => setRevealed((r) => ({ ...r, [i]: true }))}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                  viewport={{ once: true }}
                  data-testid={`bien-vieillir-sample-${i}`}
                  className="text-left bg-cream rounded-2xl border-2 border-cream-dark p-5 hover:border-[#6A994E] transition-colors"
                >
                  <Icon className="w-5 h-5 text-[#6A994E] mb-2" />
                  <p className="font-bold text-navy mb-2">{q}</p>
                  <p className={`text-sm font-mono transition-opacity ${revealed[i] ? "text-[#6A994E] opacity-100" : "text-navy/40 opacity-80"}`}>
                    {revealed[i] ? `→ ${a}` : "Voir la réponse"}
                  </p>
                </motion.button>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 bg-[#6A994E]/10">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 grid md:grid-cols-2 gap-10 items-center">
            <div>
              <span className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
                <MessageCircle className="w-3.5 h-3.5" /> En famille & en EHPAD
              </span>
              <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-4">Un quiz qui fait parler de ses habitudes.</h2>
              <p className="text-base md:text-lg text-navy/80 leading-relaxed">
                Chaque question peut ouvrir une conversation : « Où aimez-vous vous promener ? », « Avez-vous connu un centenaire ? ». Idéal pour un atelier mémoire ou un dimanche entre générations.
              </p>
            </div>
            <div className="bg-white rounded-2xl border-2 border-cream-dark p-6 shadow-warm">
              <Users className="w-6 h-6 text-[#6A994E] mb-3" />
              <p className="text-navy font-bold mb-2">« Quelle activité douce entretient le cœur et les articulations ? »</p>
              <p className="text-sm text-navy/60 mb-3">Puis la relance :</p>
              <p className="text-[#6A994E] font-bold italic">« Où aimez-vous vous promener ? Avez-vous une balade préférée ? »</p>
            </div>
          </div>
        </section>

        <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3">Prêt(e) à jouer avec Lucienne ?</h2>
          <p className="text-navy/70 text-base md:text-lg mb-6">Des questions vérifiées, un conseil santé chaque matin, et des souvenirs à partager.</p>
          <div className="flex gap-3 flex-wrap">
            <Link
              to={PLAY_TO}
              data-testid="bien-vieillir-cta-play-bottom"
              className="inline-flex items-center gap-2 bg-[#6A994E] text-white font-bold px-6 py-3 rounded-full hover:bg-[#557d3e] transition-colors shadow-warm"
            >
              <Play className="w-5 h-5" /> Créer mon compte gratuit
            </Link>
            <Link
              to="/#tarifs"
              data-testid="bien-vieillir-cta-pricing"
              className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full hover:bg-navy hover:text-white transition-colors"
            >
              Voir les abonnements
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
