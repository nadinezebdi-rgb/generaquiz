import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Play, Users, Heart, Sparkles, Check, ArrowRight, Star,
  Brain, Music, Film, Phone, Landmark, Utensils, BookOpen, Mail, Camera, Newspaper, Type, Activity, Book,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import StatsSection from "@/components/StatsSection";
import { api, BACKEND_URL } from "@/lib/api";

const ACTIVITIES = [
  { id: "atelier-memoire", title: "Atelier Mémoire", desc: "Séquences, associations, logique progressive.", icon: Brain, badge: "Nouveau" },
  { id: "journal-vie", title: "Mon Journal de Vie", desc: "Racontez votre histoire, chapitre après chapitre.", icon: BookOpen, badge: "Populaire" },
  { id: "recettes-antan", title: "Recettes d'Antan", desc: "Les saveurs de votre enfance et de votre terroir.", icon: Utensils },
  { id: "gym-douce", title: "Gym Douce", desc: "Exercices adaptés, guidés pas à pas.", icon: Activity, badge: "Santé" },
  { id: "correspondance", title: "Correspondance", desc: "Messagerie simplifiée pour vos proches.", icon: Mail },
  { id: "phototheque", title: "Photothèque", desc: "Numérisez et organisez vos albums.", icon: Camera },
  { id: "actualites", title: "Actualités simples", desc: "L'essentiel en gros caractères, sans pub.", icon: Newspaper, badge: "Quotidien" },
  { id: "jeux-mots", title: "Jeux de Mots", desc: "Mots croisés, charades, mots mêlés.", icon: Type },
];

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
            <div className="inline-flex items-center gap-2 bg-cream border-2 border-mustard-dark text-navy font-bold px-4 py-2 rounded-full text-sm mb-6">
              <Star className="w-4 h-4 text-terracotta fill-terracotta" /> Le jeu qui réunit les générations
            </div>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-extrabold text-navy leading-[1.05] mb-6">
              Réveillez vos <span className="text-terracotta italic">souvenirs</span><br />
              en vous amusant !
            </h1>
            <p className="text-xl sm:text-2xl text-navy/80 leading-relaxed max-w-2xl mb-10">
              Des quiz culturels et ludiques pour entretenir votre mémoire, explorer la France d&apos;autrefois
              et partager de bons moments avec vos petits-enfants.
            </p>
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
                href="#demo"
                data-testid="hero-cta-demo"
                className="inline-flex items-center justify-center gap-3 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-white font-bold text-xl px-8 py-5 rounded-full transition min-h-[64px]"
              >
                <Users className="w-6 h-6" />
                Essayer un quiz
              </a>
            </div>

            <div className="mt-12 grid grid-cols-3 gap-6 max-w-xl border-t-2 border-cream-dark pt-8">
              {[
                { k: "800+", v: "Questions" },
                { k: "8", v: "Catégories" },
                { k: "12K+", v: "Joueurs actifs" },
              ].map((s) => (
                <div key={s.v}>
                  <div className="font-display text-4xl font-extrabold text-bordeaux">{s.k}</div>
                  <div className="text-navy/70 font-medium mt-1">{s.v}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Hero mascot card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.15 }}
            className="lg:col-span-5 relative"
          >
            <div className="relative">
              <div className="absolute -inset-6 bg-mustard/40 rounded-[40px] rotate-3" />
              <div className="relative bg-white border-4 border-navy rounded-[36px] p-6 shadow-warm">
                <div className="aspect-square rounded-3xl overflow-hidden bg-cream border-2 border-cream-dark mb-4 float-anim">
                  <img
                    src={`${BACKEND_URL}/api/static/mascots/chansons.png`}
                    alt="Yvette la chanteuse"
                    className="w-full h-full object-cover"
                    data-testid="hero-mascot-image"
                  />
                </div>
                <div className="text-center">
                  <div className="inline-block bg-terracotta text-white text-sm font-bold px-3 py-1 rounded-full mb-2">Quiz du Jour</div>
                  <h3 className="font-display text-2xl font-bold text-navy mb-1">Chansons françaises</h3>
                  <p className="text-navy/60 text-sm">avec Yvette la Chanteuse</p>
                </div>
                <div className="mt-5 bg-cream rounded-2xl p-4 text-center">
                  <p className="text-navy font-semibold">« Qui a chanté <em>La Vie en rose</em> en 1945 ? »</p>
                </div>
                <div className="grid grid-cols-2 gap-2 mt-3">
                  {["Charles Trenet", "Édith Piaf", "Brassens", "Brel"].map((o, i) => (
                    <div
                      key={o}
                      className={`text-sm font-bold py-2 px-3 rounded-xl border-2 text-center ${
                        i === 1 ? "bg-mustard border-mustard-dark text-navy" : "bg-white border-cream-dark text-navy/70"
                      }`}
                    >
                      {i === 1 && <Check className="w-4 h-4 inline mr-1" />}
                      {o}
                    </div>
                  ))}
                </div>
              </div>
              <div className="absolute -bottom-5 -right-5 bg-bordeaux text-cream rounded-2xl px-5 py-3 font-bold shadow-warm rotate-3">
                🏆 Score 4/5
              </div>
            </div>
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
              Huit univers, huit personnages
            </h2>
            <p className="text-xl text-navy/70 leading-relaxed">
              Chaque catégorie a son ambassadeur caricaturé pour vous accompagner dans la découverte —
              avec deux nouvelles thématiques de culture générale pour les <strong>quadras</strong> et les <strong>septuagénaires</strong>.
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

      {/* ============ ACTIVITIES ============ */}
      <section className="py-20 lg:py-28 bg-cream relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-3 gap-12 items-start">
            <div className="lg:col-span-1 lg:sticky lg:top-24">
              <span className="inline-block bg-bordeaux text-cream font-bold px-4 py-1 rounded-full text-sm mb-4">Au-delà des quiz</span>
              <h2 className="font-display text-4xl lg:text-5xl font-extrabold text-navy mb-4">
                Une plateforme<br />
                <span className="text-terracotta">complète</span>
              </h2>
              <p className="text-xl text-navy/70 leading-relaxed mb-6">
                8 activités conçues spécialement pour les seniors : mémoire, gym douce, journal,
                correspondance et plus encore.
              </p>
              <Link
                to="/register"
                className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-6 py-4 rounded-full transition"
              >
                Tout découvrir <ArrowRight className="w-5 h-5" />
              </Link>
            </div>

            <div className="lg:col-span-2 grid sm:grid-cols-2 gap-5">
              {ACTIVITIES.map((a, idx) => {
                const Icon = a.icon;
                return (
                  <motion.div
                    key={a.id}
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.04 }}
                    className="bg-white border-2 border-cream-dark rounded-2xl p-6 hover:border-terracotta hover:-translate-y-0.5 transition"
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-terracotta/15 flex items-center justify-center shrink-0">
                        <Icon className="w-6 h-6 text-terracotta" strokeWidth={2.5} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-display text-xl font-bold text-navy">{a.title}</h3>
                          {a.badge && (
                            <span className="text-xs font-bold bg-mustard text-navy px-2 py-0.5 rounded-full">{a.badge}</span>
                          )}
                        </div>
                        <p className="text-navy/70">{a.desc}</p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* ============ PRICING ============ */}
      <section id="tarifs" className="py-20 lg:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="inline-block bg-cream border-2 border-mustard-dark text-navy font-bold px-4 py-1 rounded-full text-sm mb-4">Tarifs simples</span>
            <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-4">
              Commencez gratuitement
            </h2>
            <p className="text-xl text-navy/70">Sans engagement. Annulez à tout moment.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <PricingCard
              title="Découverte"
              price="0€"
              period="à vie"
              features={["5 questions par quiz", "Accès à 6 catégories", "Statistiques basiques"]}
              cta="S'inscrire"
              ctaTo="/register"
              variant="ghost"
              testid="pricing-free"
            />
            <PricingCard
              title="Premium Mensuel"
              price="9,99€"
              period="par mois"
              features={["Questions illimitées", "Toutes les activités", "Défis famille", "Lecture vocale", "Statistiques détaillées"]}
              cta="Choisir Premium"
              ctaTo="/app/pricing"
              variant="primary"
              highlight
              testid="pricing-monthly"
            />
            <PricingCard
              title="Premium Annuel"
              price="89,99€"
              period="par an"
              features={["Tout Premium Mensuel", "12 mois pour le prix de 10", "Économisez 2 mois", "Support prioritaire"]}
              cta="Économiser"
              ctaTo="/app/pricing"
              variant="ghost"
              testid="pricing-yearly"
            />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}

function PricingCard({ title, price, period, features, cta, ctaTo, variant, highlight, testid }) {
  return (
    <div
      data-testid={testid}
      className={`relative rounded-3xl p-8 ${
        highlight
          ? "bg-navy text-white border-4 border-mustard shadow-warm scale-[1.02]"
          : "bg-white border-2 border-cream-dark"
      }`}
    >
      {highlight && (
        <span className="absolute -top-4 left-1/2 -translate-x-1/2 bg-mustard text-navy font-bold text-sm px-4 py-1.5 rounded-full">
          ★ Le plus populaire
        </span>
      )}
      <h3 className={`font-display text-2xl font-bold mb-2 ${highlight ? "text-mustard" : "text-navy"}`}>{title}</h3>
      <div className="mb-1">
        <span className={`font-display text-5xl font-extrabold ${highlight ? "text-white" : "text-bordeaux"}`}>{price}</span>
        <span className={`ml-2 ${highlight ? "text-cream/70" : "text-navy/60"}`}>{period}</span>
      </div>
      <ul className={`my-6 space-y-3 ${highlight ? "text-cream" : "text-navy/80"}`}>
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2">
            <Check className={`w-5 h-5 mt-1 shrink-0 ${highlight ? "text-mustard" : "text-terracotta"}`} strokeWidth={3} />
            <span className="font-medium">{f}</span>
          </li>
        ))}
      </ul>
      <Link
        to={ctaTo}
        className={`mt-4 inline-flex w-full items-center justify-center gap-2 px-6 py-4 rounded-full font-bold text-lg transition ${
          variant === "primary"
            ? "bg-terracotta hover:bg-terracotta-dark text-white"
            : "bg-cream hover:bg-mustard text-navy border-2 border-navy"
        }`}
      >
        {cta} <ArrowRight className="w-5 h-5" />
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
