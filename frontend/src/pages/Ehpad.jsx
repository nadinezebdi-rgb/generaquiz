import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  Sparkles, Users, HeartHandshake, Brain, Shield, CheckCircle2,
  Phone, Mail, ArrowRight, Star,
} from "lucide-react";

/**
 * /ehpad — B2B landing targeted at animateurs, directeurs et cadres soignants
 * qui pilotent l'animation cognitive dans les EHPAD et résidences seniors.
 *
 * L'objectif est de générer des demandes de démo. Pas de checkout direct :
 * un formulaire simple envoie le contact sur mailto (temporaire) — à
 * connecter à un CRM (HubSpot / Brevo) dans un prochain sprint.
 */

const BENEFITS = [
  {
    icon: Brain,
    title: "Stimulation cognitive ciblée",
    desc: "Cinq axes mesurés : culture, régularité, attention, rapidité, mémoire. Chaque résident voit sa progression sur son propre radar.",
  },
  {
    icon: Users,
    title: "Séance de groupe ou individuelle",
    desc: "Grande police, contraste renforcé, lecture vocale. Utilisable sur tablette en atelier animé, ou seul dans la chambre.",
  },
  {
    icon: HeartHandshake,
    title: "Lien intergénérationnel",
    desc: "Chaque résident peut inviter ses petits-enfants sur un défi coopératif — le lien se recrée par le jeu, à distance.",
  },
  {
    icon: Shield,
    title: "Hébergement conforme RGPD",
    desc: "Données hébergées en Union européenne. Contrat de sous-traitance disponible pour votre DPO.",
  },
];

const SOCIAL_PROOF = [
  { label: "Catégories culturelles françaises", value: "8" },
  { label: "Questions actualisées chaque nuit", value: "300+" },
  { label: "Générations qui jouent ensemble", value: "3" },
];

export default function Ehpad() {
  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="landing" />

      {/* ============ HERO ============ */}
      <section className="relative overflow-hidden" data-testid="ehpad-hero">
        <div className="absolute inset-0 -z-10 pointer-events-none">
          <div className="absolute -top-20 -right-32 w-[520px] h-[520px] rounded-full bg-terracotta/12 blur-3xl" />
          <div className="absolute top-40 -left-32 w-[420px] h-[420px] rounded-full bg-navy/10 blur-3xl" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 grid lg:grid-cols-2 gap-12 items-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
              <Sparkles className="w-4 h-4" /> Pour les EHPAD & résidences seniors
            </span>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy leading-[1.05] mb-5" data-testid="ehpad-title">
              L&apos;animation cognitive
              <span className="block text-terracotta italic">qui plaît vraiment aux résidents.</span>
            </h1>
            <p className="text-navy/80 text-lg mb-6 max-w-xl">
              GénéraQuiz est une plateforme française de stimulation cognitive et de lien intergénérationnel,
              conçue pour les animateurs qui veulent des ateliers <strong>joyeux, mesurables et sans logistique</strong>.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mb-8">
              <a
                href="#demo"
                data-testid="ehpad-cta-demo"
                className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm transition"
              >
                Demander une démo <ArrowRight className="w-5 h-5" />
              </a>
              <Link
                to="/quiz-du-jour"
                data-testid="ehpad-cta-try"
                className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy font-bold px-6 py-4 rounded-full hover:bg-navy hover:text-cream transition"
              >
                Essayer le Quiz du Jour
              </Link>
            </div>

            <div className="flex items-center gap-2 text-navy/70">
              <div className="flex text-terracotta">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-current" />
                ))}
              </div>
              <span className="text-sm">« Nos résidents redemandent la séance chaque semaine. »</span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="relative"
          >
            <div className="bg-white border-2 border-cream-dark rounded-[32px] p-6 md:p-8 shadow-warm">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-11 h-11 rounded-2xl bg-terracotta/15 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-terracotta" />
                </div>
                <div>
                  <div className="font-display text-xl font-extrabold text-navy">EHPAD Les Tilleuls</div>
                  <div className="text-xs text-navy/60">Séance du mercredi · 14h30 · Salle commune</div>
                </div>
              </div>
              <div className="space-y-2 mb-4">
                {[
                  { name: "Yvette, 84 ans", score: "Chansons françaises · 8/10" },
                  { name: "Roger, 78 ans", score: "Cinéma français · 7/10" },
                  { name: "Denise, 91 ans", score: "Objets d'antan · 9/10" },
                ].map((r) => (
                  <div key={r.name} className="bg-cream rounded-2xl p-3 flex items-center justify-between">
                    <div>
                      <div className="font-bold text-navy text-sm">{r.name}</div>
                      <div className="text-xs text-navy/60">{r.score}</div>
                    </div>
                    <CheckCircle2 className="w-5 h-5 text-[#3D9970]" />
                  </div>
                ))}
              </div>
              <div className="text-xs text-navy/60 italic border-t border-cream-dark pt-3">
                Rapport exportable en PDF pour l&apos;équipe soignante — mesure de la stimulation par résident.
              </div>
            </div>
          </motion.div>
        </div>

        {/* Stats strip */}
        <div className="bg-navy/95 text-cream" data-testid="ehpad-stats">
          <div className="max-w-6xl mx-auto px-4 py-6 grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            {SOCIAL_PROOF.map((s) => (
              <div key={s.label}>
                <div className="font-display text-3xl md:text-4xl font-extrabold text-mustard">{s.value}</div>
                <div className="text-sm text-cream/80">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ BENEFITS ============ */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16" data-testid="ehpad-benefits">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3">
            Pensé pour votre équipe <span className="text-terracotta italic">d&apos;animation</span>
          </h2>
          <p className="text-navy/70">
            Un outil clé en main : vous branchez une tablette, vous choisissez la catégorie,
            et vos résidents jouent. Nous nous occupons du reste.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          {BENEFITS.map((b, i) => {
            const Icon = b.icon;
            return (
              <motion.div
                key={b.title}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
                data-testid={`ehpad-benefit-${i}`}
                className="bg-white border-2 border-cream-dark rounded-[24px] p-6 hover:border-terracotta transition"
              >
                <div className="w-12 h-12 rounded-2xl bg-terracotta/15 flex items-center justify-center mb-4">
                  <Icon className="w-6 h-6 text-terracotta" />
                </div>
                <h3 className="font-display text-xl font-extrabold text-navy mb-2">{b.title}</h3>
                <p className="text-navy/70">{b.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* ============ DEMO CTA ============ */}
      <section id="demo" className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-20" data-testid="ehpad-demo-cta">
        <div className="bg-bordeaux text-cream rounded-[32px] p-8 md:p-12 text-center relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-terracotta/25 blur-3xl" />
          <div className="absolute -bottom-24 -left-24 w-80 h-80 rounded-full bg-mustard/20 blur-3xl" />
          <div className="relative">
            <h2 className="font-display text-3xl md:text-4xl font-extrabold mb-3">
              Prêt à essayer avec vos résidents ?
            </h2>
            <p className="text-cream/85 mb-8 max-w-xl mx-auto">
              Nous vous offrons une démo de 30 minutes en visio avec un accès gratuit d&apos;un mois pour votre établissement.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a
                href="mailto:contact@generaquiz.fr?subject=Demande%20d%C3%A9mo%20EHPAD&body=Bonjour%2C%0AJe%20suis%20animateur%2Fdirecteur%20d%27EHPAD%20et%20je%20souhaite%20une%20d%C3%A9mo%20de%20GeneraQuiz.%0A%0ANom%20de%20l%27%C3%A9tablissement%20%3A%0ANombre%20de%20r%C3%A9sidents%20%3A%0AT%C3%A9l%C3%A9phone%20%3A%0A"
                data-testid="ehpad-cta-mail"
                className="inline-flex items-center justify-center gap-2 bg-mustard text-navy hover:bg-mustard-dark font-bold px-6 py-4 rounded-full shadow-warm transition"
              >
                <Mail className="w-5 h-5" /> Écrire à l&apos;équipe
              </a>
              <a
                href="tel:+33000000000"
                data-testid="ehpad-cta-phone"
                className="inline-flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 border-2 border-cream/30 text-cream font-bold px-6 py-4 rounded-full transition"
              >
                <Phone className="w-5 h-5" /> Nous appeler
              </a>
            </div>
            <p className="text-cream/60 text-xs mt-6">
              Sans engagement · Réponse en moins de 48h · Interlocuteur unique dédié
            </p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
