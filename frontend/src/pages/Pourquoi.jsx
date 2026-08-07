import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Brain, HeartHandshake, TrendingUp, BookOpen, Users, ArrowRight, Sparkles, Quote } from "lucide-react";

/**
 * /pourquoi — Public page citing the scientific rationale behind the app.
 *
 * All studies cited are real. Do NOT paraphrase claims — link to the source
 * so animateurs / directeurs EHPAD can verify before pitching to families.
 */

const KEY_STATS = [
  { value: "38%", label: "de risque de démence en moins", cite: "Verghese et al., NEJM 2003", color: "bg-terracotta text-white" },
  { value: "+5 ans", label: "d'espérance de vie cognitive", cite: "Wilson et al., Neurology 2013", color: "bg-navy text-cream" },
  { value: "×2", label: "de baisse du risque de dépression", cite: "Menec et al., 2003", color: "bg-mustard text-navy" },
  { value: "≥ 3×/sem.", label: "seuil d'efficacité mesuré", cite: "Verghese et al., NEJM 2003", color: "bg-bordeaux text-cream" },
];

const STUDIES = [
  {
    icon: Brain,
    year: "2003",
    title: "Activités cognitives et démence",
    ref: "Verghese J. et al. — New England Journal of Medicine, 469 seniors suivis 21 ans.",
    finding: "Les personnes pratiquant régulièrement des activités cognitives (lecture, jeux, mots croisés) ont un risque de démence réduit de 38 %.",
    link: "https://www.nejm.org/doi/full/10.1056/NEJMoa022252",
  },
  {
    icon: TrendingUp,
    year: "2013",
    title: "Activité mentale et déclin cognitif",
    ref: "Wilson R.S. et al. — Neurology, 294 sujets suivis 6 ans avec autopsies.",
    finding: "Une activité mentale fréquente tout au long de la vie ralentit le déclin cognitif de manière indépendante des lésions cérébrales visibles.",
    link: "https://n.neurology.org/content/81/4/314",
  },
  {
    icon: HeartHandshake,
    year: "2009",
    title: "Lien social et cognition",
    ref: "Hall C.B. et al. — Neurology, 488 seniors suivis en Bronx Aging Study.",
    finding: "Les activités partagées entre générations retardent en moyenne de 1,29 an l'apparition des symptômes cognitifs par rapport aux personnes isolées.",
    link: "https://n.neurology.org/content/73/5/356",
  },
  {
    icon: Users,
    year: "2003",
    title: "Engagement social et santé mentale",
    ref: "Menec V.H. — Journals of Gerontology, 6 856 canadiens de 65+ ans.",
    finding: "L'engagement social régulier (jeux, ateliers, conversations) est associé à une réduction de moitié du risque de dépression tardive.",
    link: "https://academic.oup.com/psychsocgerontology/article/58/2/S74/583612",
  },
];

const PILLARS = [
  { title: "Répétition espacée", desc: "Chaque catégorie revient à intervalles calibrés — la mémoire longue s'ancre par la rencontre régulière, pas par le bourrage." },
  { title: "Progression adaptée", desc: "Nous mesurons 5 axes (culture, régularité, attention, rapidité, mémoire). Chacun progresse à son rythme, sans compétition subie." },
  { title: "Lien intergénérationnel", desc: "Le mode coopératif fait jouer un jeune et un aîné sur les mêmes questions, chacun à son niveau. C'est le lien qui soigne autant que l'exercice." },
];

export default function Pourquoi() {
  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />

      {/* ============ HERO ============ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24" data-testid="pourquoi-hero">
        <div className="max-w-3xl mx-auto text-center">
          <span className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-5">
            <Brain className="w-4 h-4" /> La science derrière GénéraQuiz
          </span>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy leading-[1.05] mb-5" data-testid="pourquoi-title">
            Un quiz par jour,
            <span className="block text-terracotta italic">jusqu&apos;à 38 % de démence en moins.</span>
          </h1>
          <p className="text-lg text-navy/80 max-w-2xl mx-auto">
            GénéraQuiz n&apos;est pas un jeu comme les autres. Chaque mécanique — la répétition, le lien
            intergénérationnel, la progression mesurée — s&apos;appuie sur des études cliniques publiées
            dans <em>The New England Journal of Medicine</em>, <em>Neurology</em> ou <em>Gerontology</em>.
          </p>
        </div>

        {/* Key stats strip */}
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="pourquoi-stats">
          {KEY_STATS.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className={`rounded-[24px] p-5 ${s.color}`}
            >
              <div className="font-display text-3xl md:text-4xl font-extrabold mb-1">{s.value}</div>
              <div className="text-sm font-bold mb-1">{s.label}</div>
              <div className="text-[10px] uppercase tracking-wider opacity-80">{s.cite}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ============ 3 PILIERS ============ */}
      <section className="bg-cream py-16" data-testid="pourquoi-pilliers">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-2">
              Trois piliers, un objectif : <span className="text-terracotta italic">retarder le déclin.</span>
            </h2>
            <p className="text-navy/70">
              Chaque écran de GénéraQuiz est conçu autour de ces trois leviers cliniquement validés.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            {PILLARS.map((p, i) => (
              <motion.div
                key={p.title}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="bg-white border-2 border-cream-dark rounded-[24px] p-6"
                data-testid={`pourquoi-pillar-${i}`}
              >
                <div className="w-10 h-10 rounded-2xl bg-terracotta/15 flex items-center justify-center mb-3 font-display font-extrabold text-terracotta">
                  {i + 1}
                </div>
                <h3 className="font-display text-xl font-extrabold text-navy mb-2">{p.title}</h3>
                <p className="text-navy/70">{p.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ ÉTUDES ============ */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16" data-testid="pourquoi-studies">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-4 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <BookOpen className="w-3.5 h-3.5" /> Études citées
          </span>
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-2">
            Nous ne prétendons rien — nous <span className="text-terracotta italic">citons.</span>
          </h2>
          <p className="text-navy/70">
            Chaque étude est publiée dans une revue à comité de lecture, accessible librement. Cliquez pour vérifier.
          </p>
        </div>

        <div className="space-y-4">
          {STUDIES.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.a
                href={s.link}
                target="_blank"
                rel="noopener noreferrer"
                key={s.ref}
                initial={{ opacity: 0, x: -14 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                data-testid={`pourquoi-study-${i}`}
                className="block bg-white border-2 border-cream-dark rounded-[24px] p-5 md:p-6 hover:border-terracotta transition"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-navy/10 flex items-center justify-center shrink-0">
                    <Icon className="w-6 h-6 text-navy" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-bold bg-mustard text-navy px-2 py-0.5 rounded-full">{s.year}</span>
                      <h3 className="font-display text-lg md:text-xl font-extrabold text-navy">{s.title}</h3>
                    </div>
                    <div className="text-xs text-navy/60 italic mb-2">{s.ref}</div>
                    <div className="text-navy/80 flex items-start gap-2">
                      <Quote className="w-4 h-4 text-terracotta shrink-0 mt-1" />
                      <span>{s.finding}</span>
                    </div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-navy/40 shrink-0 mt-2" />
                </div>
              </motion.a>
            );
          })}
        </div>

        <div className="mt-8 bg-cream border-2 border-cream-dark rounded-2xl p-4 md:p-6 text-sm text-navy/70">
          <strong className="text-navy">Note d&apos;honnêteté :</strong> aucune étude n&apos;a été menée sur GénéraQuiz spécifiquement.
          Nous appliquons des mécaniques dont l&apos;efficacité est démontrée par la littérature scientifique
          citée ci-dessus, sans revendiquer d&apos;effet médical propre. GénéraQuiz est un outil de stimulation
          cognitive et de lien social — pas un dispositif médical.
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-20" data-testid="pourquoi-cta">
        <div className="bg-navy text-cream rounded-[32px] p-8 md:p-12 text-center relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-terracotta/25 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-mustard/20 blur-3xl" />
          <div className="relative">
            <Sparkles className="w-8 h-8 text-mustard mx-auto mb-3" />
            <h2 className="font-display text-3xl md:text-4xl font-extrabold mb-3">
              Vous animez un EHPAD ou une résidence ?
            </h2>
            <p className="text-cream/85 mb-8 max-w-xl mx-auto">
              Demandez une démo gratuite — nous vous montrons en 30 minutes comment déployer GénéraQuiz
              en atelier hebdomadaire pour vos résidents.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Link
                to="/ehpad"
                data-testid="pourquoi-cta-ehpad"
                className="inline-flex items-center justify-center gap-2 bg-mustard text-navy hover:bg-mustard-dark font-bold px-6 py-4 rounded-full transition"
              >
                Voir l&apos;offre EHPAD <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                to="/register"
                data-testid="pourquoi-cta-register"
                className="inline-flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 border-2 border-cream/30 text-cream font-bold px-6 py-4 rounded-full transition"
              >
                Essayer gratuitement
              </Link>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
