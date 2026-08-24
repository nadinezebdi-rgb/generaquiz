import { motion } from "framer-motion";
import { Building2, Check, FileText, PenLine, ReceiptText, Sparkles, Users, ShieldCheck, PhoneCall } from "lucide-react";
import { PRO_RESIDENCE, PRO_RESEAU, PRO_STEPS, PRO_TYPES, fmt } from "@/config/pricing";

/**
 * ProPricing — Offre B2B alignée sur le modèle Wivy :
 *  1 abonnement annuel flat par résidence (utilisateurs illimités),
 *  engagement 12 mois SANS reconduction tacite, essai gratuit,
 *  process devis → signature → facture → activation.
 */
export default function ProPricing() {
  const contactSubject = encodeURIComponent("Devis GénéraQuiz Pro - " + PRO_RESIDENCE.nom);
  const contactHref = `mailto:contact@generaquiz.fr?subject=${contactSubject}`;
  const contactReseauHref = `mailto:contact@generaquiz.fr?subject=${encodeURIComponent("Devis GénéraQuiz Pro - Formule Réseau")}`;
  const essaiHref = "/register";

  return (
    <section className="mt-14" data-testid="pro-pricing-section">
      <div className="text-center max-w-2xl mx-auto mb-8">
        <span className="inline-block bg-navy text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
          Offre Pro
        </span>
        <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="pro-offer-title">
          Pour les <span className="text-terracotta italic">EHPAD & résidences seniors</span>
        </h2>
        <p className="text-navy/70">
          <strong>1 an d&apos;abonnement, tous vos résidents inclus.</strong> Sans reconduction tacite.
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

      {/* 2 formules : Résidence (flat) + Réseau (sur devis) */}
      <div className="grid md:grid-cols-2 gap-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="relative bg-white rounded-3xl p-7 border-2 border-terracotta ring-4 ring-terracotta/15 shadow-warm flex flex-col"
          data-testid={`pro-card-${PRO_RESIDENCE.id}`}
        >
          <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full inline-flex items-center gap-1 shadow-warm">
            <Sparkles className="w-3 h-3 fill-current" /> Notre formule
          </span>

          <div className="flex items-center gap-2 mb-2">
            <Building2 className="w-5 h-5 text-navy/60" />
            <h3 className="font-display text-2xl font-extrabold text-navy">{PRO_RESIDENCE.nom}</h3>
          </div>
          <p className="text-sm text-navy/60 mb-4">{PRO_RESIDENCE.tagline}</p>

          <div className="mb-4">
            <div className="flex items-baseline gap-2">
              <span className="font-display text-4xl font-extrabold text-bordeaux" data-testid="pro-price-ht">
                {fmt(PRO_RESIDENCE.prixHT, { integer: true })}
              </span>
              <span className="text-sm text-navy/60 font-bold">HT / an</span>
            </div>
            <p className="text-sm text-navy/60 mt-1" data-testid="pro-price-ttc">
              soit <strong>{fmt(PRO_RESIDENCE.prixTTC, { integer: true })} TTC</strong> — abonnement 12 mois
            </p>
            <span className="inline-flex items-center gap-1 bg-[#3D9970]/15 text-[#2A7350] font-bold px-2 py-0.5 rounded-full text-xs mt-3">
              <Users className="w-3 h-3" /> Utilisateurs illimités dans la résidence
            </span>
          </div>

          <ul className="space-y-2 mb-5 flex-1">
            {PRO_RESIDENCE.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
                <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
                <span>{f}</span>
              </li>
            ))}
          </ul>

          <div className="grid grid-cols-2 gap-2">
            <a
              href={contactHref}
              data-testid="pro-cta-devis"
              className="inline-flex items-center justify-center gap-2 bg-terracotta text-white hover:bg-terracotta-dark font-bold px-5 py-3 rounded-full transition min-h-[52px] shadow-warm"
            >
              <FileText className="w-4 h-4" /> Demander un devis
            </a>
            <a
              href={essaiHref}
              data-testid="pro-cta-essai"
              className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream font-bold px-5 py-3 rounded-full transition min-h-[52px]"
            >
              Essai gratuit
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          transition={{ delay: 0.08 }}
          className="relative bg-white rounded-3xl p-7 border-2 border-cream-dark flex flex-col"
          data-testid={`pro-card-${PRO_RESEAU.id}`}
        >
          <div className="flex items-center gap-2 mb-2">
            <Building2 className="w-5 h-5 text-navy/60" />
            <h3 className="font-display text-2xl font-extrabold text-navy">{PRO_RESEAU.nom}</h3>
          </div>
          <p className="text-sm text-navy/60 mb-4">{PRO_RESEAU.tagline}</p>

          <div className="mb-4">
            <div className="font-display text-4xl font-extrabold text-bordeaux">Sur devis</div>
            <p className="text-sm text-navy/60 mt-1">Tarif dégressif selon le nombre de sites</p>
          </div>

          <ul className="space-y-2 mb-5 flex-1">
            {PRO_RESEAU.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm text-navy/80">
                <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
                <span>{f}</span>
              </li>
            ))}
          </ul>

          <a
            href={contactReseauHref}
            data-testid="pro-cta-reseau"
            className="w-full inline-flex items-center justify-center gap-2 bg-navy text-cream hover:bg-navy-dark font-bold px-5 py-3 rounded-full transition min-h-[52px]"
          >
            <PhoneCall className="w-4 h-4" /> Demander un devis Réseau
          </a>
        </motion.div>
      </div>

      {/* Réassurance : sans engagement tacite */}
      <div className="grid md:grid-cols-3 gap-3 mb-6" data-testid="pro-reassurance">
        <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-[#2A7350] mt-0.5 shrink-0" />
          <p className="text-sm text-navy/80">
            <strong className="block text-navy">Sans reconduction tacite</strong>
            Nous vous contactons avant l&apos;expiration pour renouveler <em>avec votre accord</em>.
          </p>
        </div>
        <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-terracotta mt-0.5 shrink-0" />
          <p className="text-sm text-navy/80">
            <strong className="block text-navy">Essai gratuit et sans engagement</strong>
            Testez toutes les fonctionnalités avant de signer.
          </p>
        </div>
        <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4 flex items-start gap-3">
          <Users className="w-5 h-5 text-navy mt-0.5 shrink-0" />
          <p className="text-sm text-navy/80">
            <strong className="block text-navy">Utilisateurs illimités</strong>
            Tous vos résidents et animateurs, dans un seul abonnement.
          </p>
        </div>
      </div>

      {/* Process 4 étapes — inspiré Wivy */}
      <div className="bg-white border-2 border-cream-dark rounded-3xl p-6" data-testid="pro-steps">
        <h3 className="font-display text-xl font-extrabold text-navy text-center mb-5">
          Comment devenir client ?
        </h3>
        <div className="grid md:grid-cols-4 gap-4">
          {PRO_STEPS.map((s) => (
            <div key={s.n} className="flex flex-col items-center text-center gap-2" data-testid={`pro-step-${s.n}`}>
              <div className="w-12 h-12 rounded-full bg-terracotta text-white font-display text-xl font-extrabold flex items-center justify-center shadow-warm">
                {s.n}
              </div>
              <StepIcon n={s.n} />
              <div className="font-bold text-navy text-sm">{s.title}</div>
              <p className="text-xs text-navy/60 leading-snug">{s.desc}</p>
            </div>
          ))}
        </div>
        <p className="text-center text-sm text-navy/70 mt-5">
          <strong>Votre compte est activé instantanément après signature.</strong>
        </p>
      </div>
    </section>
  );
}

function StepIcon({ n }) {
  const cls = "w-5 h-5 text-navy/60";
  if (n === 1) return <FileText className={cls} />;
  if (n === 2) return <PenLine className={cls} />;
  if (n === 3) return <ReceiptText className={cls} />;
  return <Check className={cls} />;
}
