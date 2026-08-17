import { motion } from "framer-motion";
import { Gamepad2, Sparkles, Mic, BookOpen, ArrowRight } from "lucide-react";

/**
 * HowItWorksSection — "Comment ça marche" : 4 étapes visuelles.
 *
 * Boucle signature GénéraQuiz : JOUER → SE SOUVENIR → RACONTER → TRANSMETTRE.
 * Ancrage : #how-it-works (lien depuis le CTA secondaire du Hero).
 *
 * Design : cartes larges, vocabulaire simple, contrastes AAA, boutons non-actifs
 * (section purement démonstrative). Optimisée seniors : text-base minimum,
 * min-h généreuse, un CTA global en pied.
 */

const STEPS = [
  {
    n: 1,
    icon: Gamepad2,
    emoji: "🎮",
    label: "Je joue",
    desc: "Je découvre des quiz autour des chansons, du cinéma, des objets d'antan, des voyages, de la cuisine…",
    accent: "bg-terracotta/20 text-terracotta",
    ring: "ring-terracotta",
  },
  {
    n: 2,
    icon: Sparkles,
    emoji: "💭",
    label: "Je me souviens",
    desc: "Une question réveille un souvenir personnel : un plat, une chanson, un été de vacances…",
    accent: "bg-mustard/25 text-mustard-dark",
    ring: "ring-mustard-dark",
  },
  {
    n: 3,
    icon: Mic,
    emoji: "❤️",
    label: "Je raconte",
    desc: "Je l'écris, ou je le raconte simplement à voix haute. GénéraQuiz s'occupe de le mettre en pages.",
    accent: "bg-navy/10 text-navy",
    ring: "ring-navy",
  },
  {
    n: 4,
    icon: BookOpen,
    emoji: "📖",
    label: "Je transmets",
    desc: "Mes souvenirs constituent mon Livre de Vie — à partager en famille, à imprimer, à laisser aux miens.",
    accent: "bg-bordeaux/15 text-bordeaux",
    ring: "ring-bordeaux",
  },
];

export default function HowItWorksSection() {
  return (
    <section
      id="how-it-works"
      className="py-20 lg:py-28 bg-white"
      data-testid="how-it-works-section"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* En-tête */}
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span
            className="inline-block bg-navy text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-5"
            data-testid="hiw-pill"
          >
            Comment ça marche
          </span>
          <h2 className="font-display text-4xl md:text-5xl font-extrabold text-navy leading-[1.05] mb-4">
            Un souvenir peut commencer<br />
            par <span className="text-terracotta italic">une simple question</span>.
          </h2>
          <p className="text-lg text-navy/70 leading-relaxed">
            Quatre étapes très simples, pour toute la famille — du petit-enfant curieux au grand-parent qui a des histoires à raconter.
          </p>
        </div>

        {/* Bandeau JOUER → SE SOUVENIR → RACONTER → TRANSMETTRE */}
        <div
          className="hidden md:flex items-center justify-center gap-4 mb-12 text-xs font-bold uppercase tracking-widest text-navy/60"
          data-testid="hiw-flow"
        >
          <span>Jouer</span>
          <ArrowRight className="w-4 h-4 text-terracotta" />
          <span>Se souvenir</span>
          <ArrowRight className="w-4 h-4 text-terracotta" />
          <span>Raconter</span>
          <ArrowRight className="w-4 h-4 text-terracotta" />
          <span>Transmettre</span>
        </div>

        {/* Étapes */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.n}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.4 }}
                className="bg-cream rounded-3xl border-2 border-cream-dark p-6 lg:p-7 flex flex-col hover:-translate-y-1 hover:shadow-warm transition"
                data-testid={`hiw-step-${step.n}`}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className={`w-14 h-14 rounded-2xl ${step.accent} flex items-center justify-center text-2xl`}>
                    <span aria-hidden>{step.emoji}</span>
                  </div>
                  <div className={`w-8 h-8 rounded-full bg-white border-2 ${step.ring.replace('ring-','border-')} flex items-center justify-center font-display font-extrabold text-navy`}>
                    {step.n}
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-navy/60" strokeWidth={2.5} />
                  <h3 className="font-display text-xl font-extrabold text-navy">{step.label}</h3>
                </div>
                <p className="text-base text-navy/75 leading-relaxed flex-1">{step.desc}</p>
              </motion.div>
            );
          })}
        </div>

        {/* CTA de fin */}
        <div className="text-center mt-14">
          <a
            href="/register"
            data-testid="hiw-cta"
            className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-8 py-4 rounded-full shadow-warm transition min-h-[60px]"
          >
            Commencer mon histoire
          </a>
          <p className="text-sm text-navy/50 mt-3">
            Sans engagement · Un souvenir raconté aujourd&apos;hui peut devenir une histoire transmise demain.
          </p>
        </div>
      </div>
    </section>
  );
}
