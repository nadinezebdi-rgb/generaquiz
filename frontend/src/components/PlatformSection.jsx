import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Brain, BookOpen, ChefHat, Camera, PenLine, MessageCircle, Search, ArrowRight, Sparkles, Clock, Check } from "lucide-react";

/**
 * PlatformSection — "Au-delà des quiz : une plateforme complète".
 *
 * Marketing-focused hub. Cards with `href` are LIVE (clickable Link);
 * cards without `href` are still in development (badge "En dev." shown).
 * Injected between the categories and the pricing on the Landing page.
 */

const QUIZ_ACTIVITIES = [
  {
    key: "atelier-memoire",
    title: "Atelier Mémoire",
    desc: "Réminiscence guidée par thème — 5 questions, votre carnet privé.",
    icon: Brain,
    href: "/app/atelier",
    tag: { label: "En ligne", cls: "bg-[#3D9970]/20 text-[#2A7350]" },
  },
  {
    key: "journal-vie",
    title: "Mon Journal de Vie",
    desc: "Racontez votre histoire, chapitre après chapitre.",
    icon: BookOpen,
    tag: { label: "Populaire", cls: "bg-terracotta/25 text-terracotta-dark" },
  },
  {
    key: "recettes-antan",
    title: "Recettes d'Antan",
    desc: "Les saveurs de votre enfance et de votre terroir.",
    icon: ChefHat,
  },
  {
    key: "phototheque",
    title: "Photothèque",
    desc: "Numérisez et organisez vos albums.",
    icon: Camera,
  },
];

const WORD_GAMES = [
  {
    key: "charades",
    title: "Charades",
    desc: "Mon premier, mon deuxième… Charades classiques, +5 pts par bonne réponse.",
    icon: MessageCircle,
    href: "/app/charades",
    tag: { label: "En ligne", cls: "bg-[#3D9970]/20 text-[#2A7350]" },
  },
  {
    key: "mots-meles",
    title: "Mots Mêlés",
    desc: "Grilles thématiques générées chaque nuit par IA. Trouvez les mots cachés !",
    icon: Search,
    href: "/app/mots-meles",
    tag: { label: "Nouveau", cls: "bg-mustard text-navy" },
  },
  { key: "mots-croises", title: "Mots Croisés", desc: "La grille classique, en français.", icon: PenLine },
];

export default function PlatformSection() {
  const scrollToPricing = () => {
    const el = document.getElementById("tarifs");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <section id="plateforme" className="py-20 lg:py-28 bg-cream" data-testid="platform-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-10 lg:gap-16">

          {/* ============ SIDEBAR (LEFT) ============ */}
          <aside className="lg:w-[340px] lg:sticky lg:top-24 lg:self-start">
            <span
              className="inline-block bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-5"
              data-testid="platform-pill"
            >
              Au-delà des quiz
            </span>
            <h2 className="font-display text-4xl md:text-5xl font-extrabold text-navy leading-[1.05] mb-4">
              Une plateforme<br />
              <span className="text-terracotta italic">complète</span>
            </h2>
            <p className="text-navy/70 text-base leading-relaxed mb-6">
              Des activités conçues pour les seniors : mémoire, journal, recettes, photothèque — et des jeux de mots pour garder l&apos;esprit vif.
              <strong className="text-navy"> Deux sont déjà en ligne.</strong>
            </p>
            <button
              type="button"
              onClick={scrollToPricing}
              data-testid="platform-discover-btn"
              className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-cream font-bold px-6 py-3 rounded-full transition"
            >
              Tout découvrir <ArrowRight className="w-4 h-4" />
            </button>
          </aside>

          {/* ============ CONTENT (RIGHT) ============ */}
          <div className="flex-1 min-w-0 space-y-10">

            {/* ---- Quiz group ---- */}
            <div>
              <div className="flex items-center gap-3 mb-4 flex-wrap">
                <div className="w-11 h-11 rounded-2xl bg-terracotta/20 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-terracotta" strokeWidth={2.5} />
                </div>
                <span className="font-display text-xl font-extrabold text-navy">Quiz &amp; Activités</span>
                <span className="text-xs font-semibold text-navy/60 bg-cream-dark border border-cream-dark rounded-full px-2.5 py-0.5">
                  {QUIZ_ACTIVITIES.filter((a) => a.href).length} en ligne · {QUIZ_ACTIVITIES.filter((a) => !a.href).length} bientôt
                </span>
              </div>
              <hr className="border-t-2 border-cream-dark mb-5" />

              <div className="grid sm:grid-cols-2 gap-3">
                {QUIZ_ACTIVITIES.map((it, idx) => (
                  <ActivityCard key={it.key} item={it} accent="orange" delay={idx * 0.05} />
                ))}
              </div>
            </div>

            {/* ---- Separator ---- */}
            <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest text-navy/50" data-testid="platform-separator">
              <div className="flex-1 border-t border-dashed border-cream-dark" />
              Jeux de Mots
              <div className="flex-1 border-t border-dashed border-cream-dark" />
            </div>

            {/* ---- Word games group ---- */}
            <div>
              <div className="flex items-center gap-3 mb-4 flex-wrap">
                <div className="w-11 h-11 rounded-2xl bg-navy/10 flex items-center justify-center">
                  <PenLine className="w-5 h-5 text-navy" strokeWidth={2.5} />
                </div>
                <span className="font-display text-xl font-extrabold text-navy">Jeux de Mots</span>
                <span className="text-xs font-semibold text-navy/60 bg-cream-dark border border-cream-dark rounded-full px-2.5 py-0.5">
                  {WORD_GAMES.filter((w) => w.href).length} en ligne · {WORD_GAMES.filter((w) => !w.href).length} bientôt
                </span>
              </div>
              <hr className="border-t-2 border-cream-dark mb-5" />

              <div className="grid sm:grid-cols-2 gap-3">
                {WORD_GAMES.map((it, idx) => (
                  <ActivityCard key={it.key} item={it} accent="blue" delay={idx * 0.05} />
                ))}
              </div>
            </div>

            <p className="text-xs text-navy/50 text-center pt-2" data-testid="platform-availability-note">
              🚀 <strong>Atelier Mémoire</strong> et <strong>Charades</strong> sont déjà accessibles. Les autres arrivent bientôt.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function ActivityCard({ item, accent, delay }) {
  const Icon = item.icon;
  const iconBg = accent === "blue" ? "bg-navy/10 text-navy" : "bg-terracotta/20 text-terracotta";
  const isLive = Boolean(item.href);

  const inner = (
    <>
      <div className={`w-11 h-11 rounded-xl ${iconBg} flex items-center justify-center shrink-0`}>
        <Icon className="w-5 h-5" strokeWidth={2.5} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="font-display font-extrabold text-navy leading-tight">{item.title}</span>
          {item.tag && (
            <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${item.tag.cls}`}>
              {item.tag.label}
            </span>
          )}
        </div>
        <p className="text-sm text-navy/60 leading-snug">{item.desc}</p>
      </div>
      <span
        className={`absolute top-2 right-2 inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest ${
          isLive ? "text-[#2A7350]" : "text-navy/40"
        }`}
        data-testid={`platform-badge-${isLive ? "live" : "dev"}-${item.key}`}
      >
        {isLive ? <><Check className="w-3 h-3" /> Jouer</> : <><Clock className="w-3 h-3" /> En dev.</>}
      </span>
    </>
  );

  const commonClasses = "bg-white border-2 border-cream-dark rounded-2xl p-4 flex items-start gap-3 relative overflow-hidden hover:-translate-y-0.5 hover:shadow-warm transition";

  if (isLive) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay, duration: 0.35 }}
      >
        <Link
          to={item.href}
          data-testid={`platform-card-${item.key}`}
          className={`${commonClasses} hover:border-terracotta cursor-pointer`}
        >
          {inner}
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.35 }}
      data-testid={`platform-card-${item.key}`}
      className={`${commonClasses} cursor-not-allowed`}
      title="En cours de développement"
    >
      {inner}
    </motion.div>
  );
}
