import { motion } from "framer-motion";
import { Building2, Check, Star } from "lucide-react";
import { PRO_PLANS, PRO_SETUP_FEE, PRO_TYPES, fmt } from "@/config/pricing";

/**
 * ProPricing — 3 paliers B2B (Essentiel / Établissement / Réseau) +
 * frais de mise en service + types d'établissements ciblés.
 */
export default function ProPricing() {
  return (
    <section className="mt-14" data-testid="pro-pricing-section">
      <div className="text-center max-w-2xl mx-auto mb-8">
        <span className="inline-block bg-navy text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
          🏥 Offre Pro
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="pro-offer-title">
          Pour les <span className="text-terracotta italic">professionnels du lien social</span>
        </h2>
        <p className="text-navy/70">
          Un espace animateur dédié, des séances collectives, un tableau de bord établissement.
        </p>
      </div>

      {/* Types d'établissements */}
      <div className="flex flex-wrap gap-2 justify-center mb-8" data-testid="pro-offer-types">
        {PRO_TYPES.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 bg-white border-2 border-cream-dark px-3 py-1 rounded-full text-sm text-navy/80 font-semibold">
            <Check className="w-3.5 h-3.5 text-terracotta" strokeWidth={3} /> {t}
          </span>
        ))}
      </div>

      {/* 3 paliers */}
      <div className="grid md:grid-cols-3 gap-4 mb-4">
        {PRO_PLANS.map((p, i) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
              p.highlight ? "border-terracotta ring-4 ring-terracotta/15 shadow-warm" : "border-cream-dark"
            }`}
            data-testid={`pro-card-${p.id}`}
          >
            {p.badge && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full inline-flex items-center gap-1 shadow-warm">
                <Star className="w-3 h-3 fill-current" /> {p.badge}
              </span>
            )}
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="w-5 h-5 text-navy/60" />
              <h3 className="font-display text-2xl font-extrabold text-navy">{p.nom}</h3>
            </div>
            {p.onDemand ? (
              <div className="mb-4">
                <div className="font-display text-3xl font-extrabold text-bordeaux">Sur devis</div>
                <p className="text-xs text-navy/50 mt-1">Adapté à votre réseau</p>
              </div>
            ) : (
              <div className="mb-4">
                <div className="flex items-baseline gap-1">
                  <span className="font-display text-3xl font-extrabold text-bordeaux">{fmt(p.mensuel, { integer: true })}</span>
                  <span className="text-sm text-navy/60">/mois</span>
                </div>
                <p className="text-xs text-navy/50 mt-1">
                  ou <strong>{fmt(p.annuel, { integer: true })}/an</strong> (2 mois offerts)
                </p>
              </div>
            )}
            <ul className="space-y-2 mb-5 flex-1">
              {p.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
                  <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <a
              href={`mailto:contact@generaquiz.fr?subject=${encodeURIComponent("Devis GénéraQuiz Pro - " + p.nom)}`}
              data-testid={`pro-cta-${p.id}`}
              className={`w-full inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
                p.highlight ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm" : "bg-navy text-cream hover:bg-navy-dark"
              }`}
            >
              <Building2 className="w-4 h-4" /> {p.onDemand ? "Demander un devis" : "Choisir " + p.nom}
            </a>
          </motion.div>
        ))}
      </div>

      <p className="text-sm text-navy/70 text-center bg-cream border-2 border-cream-dark rounded-2xl p-4">
        <strong>Frais de mise en service : {fmt(PRO_SETUP_FEE, { integer: true })}</strong> — paramétrage, import des résidents, formation initiale.
      </p>
    </section>
  );
}
