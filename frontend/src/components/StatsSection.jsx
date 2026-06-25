import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Users2, Gamepad2, BookOpen, Flame, Globe2 } from "lucide-react";
import { api } from "@/lib/api";

/**
 * StatsSection — "En chiffres" social proof block.
 * Fetches /api/stats/public on mount and animates each counter from 0 to its
 * value when the section enters the viewport.
 */
export default function StatsSection() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/stats/public").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const items = [
    { key: "players_today", label: "Joueurs aujourd'hui", icon: Users2, color: "text-terracotta", suffix: "" },
    { key: "games_today", label: "Parties (24h)", icon: Gamepad2, color: "text-bordeaux", suffix: "" },
    { key: "questions_total", label: "Questions au catalogue", icon: BookOpen, color: "text-navy", suffix: "" },
    { key: "streak_record", label: "Record de série", icon: Flame, color: "text-mustard-dark", suffix: " j" },
    { key: "countries_active", label: "Pays / régions actifs", icon: Globe2, color: "text-terracotta", suffix: "" },
  ];

  return (
    <section id="stats" className="py-16 lg:py-20 cream-bg relative" data-testid="landing-stats-section">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="inline-block bg-navy text-cream font-bold px-4 py-1 rounded-full text-sm mb-4">
            En chiffres
          </span>
          <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-3">
            La communauté <span className="text-terracotta italic">GénéraQuiz</span> en temps réel
          </h2>
          <p className="text-lg text-navy/70">
            Chiffres mis à jour automatiquement. Bienvenue parmi nous !
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 md:gap-6">
          {items.map((it, idx) => (
            <StatCard
              key={it.key}
              icon={it.icon}
              color={it.color}
              label={it.label}
              value={stats ? stats[it.key] || 0 : 0}
              loaded={!!stats}
              suffix={it.suffix}
              delay={idx * 0.08}
              testid={`stat-${it.key.replace(/_/g, "-")}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function StatCard({ icon: Icon, color, label, value, loaded, suffix, delay, testid }) {
  const ref = useRef(null);
  const [displayed, setDisplayed] = useState(0);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    if (!loaded || hasAnimated) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setHasAnimated(true);
          // Animate count from 0 → value (~1.4s, ease-out)
          const start = performance.now();
          const duration = 1400;
          const tick = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - t, 3);
            setDisplayed(Math.round(eased * value));
            if (t < 1) requestAnimationFrame(tick);
            else setDisplayed(value);
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.4 },
    );
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [loaded, value, hasAnimated]);

  return (
    <motion.div
      ref={ref}
      data-testid={testid}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.4 }}
      className="bg-white border-2 border-cream-dark rounded-2xl p-5 md:p-6 text-center hover:-translate-y-0.5 hover:border-terracotta transition"
    >
      <Icon className={`w-7 h-7 mx-auto mb-2 ${color}`} strokeWidth={2.5} />
      <div className="font-display text-3xl md:text-4xl font-extrabold text-navy leading-none mb-1">
        {loaded ? displayed.toLocaleString("fr-FR") : "…"}{suffix}
      </div>
      <div className="text-xs md:text-sm font-bold uppercase tracking-wider text-navy/60">{label}</div>
    </motion.div>
  );
}
