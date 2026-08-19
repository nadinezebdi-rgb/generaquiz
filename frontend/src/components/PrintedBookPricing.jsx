import { motion } from "framer-motion";
import { BookOpen, Building2, Check, Star, Sparkles } from "lucide-react";

/**
 * PrintedBookPricing — 2 catégories tarifaires supplémentaires ajoutées
 * sous la grille des abonnements individuels sur la page Tarifs :
 *
 *   1. 📖 Livre imprimé — 3 offres 1/2/3 livres, mise en avant du "2 livres"
 *      Le PDF est GRATUIT pour tout abonné. L'impression est optionnelle.
 *   2. 🏥 Offre Pro — EHPAD, associations, club du 3e âge, CCAS,
 *      collectivités, structures médicalisées, médiathèques, bibliothèques.
 *
 * ⚠️ Aucun bouton d'achat live pour l'instant : contact commercial requis.
 *   Les Stripe packages `livre_1`, `livre_2`, `livre_3`, `pro_lite`, etc.
 *   seront ajoutés dans une itération dédiée après validation utilisateur.
 */

const BOOK_OFFERS = [
  {
    key: "livre-1",
    emoji: "📕",
    title: "1 livre",
    price: "79,90 €",
    unit: "79,90 € / livre",
    saving: null,
    features: ["Format A5 (15 × 21 cm)", "Jusqu'à 130 pages", "Couverture rigide couleur"],
  },
  {
    key: "livre-2",
    emoji: "📚",
    title: "2 livres",
    price: "129,90 €",
    unit: "64,95 € / livre",
    saving: "Économie 29,90 €",
    highlight: true,
    badge: "Le plus choisi",
    features: ["Idéal pour offrir à un proche", "Impression identique aux 2 exemplaires", "Livraison groupée"],
  },
  {
    key: "livre-3",
    emoji: "🎁",
    title: "3 livres",
    price: "179,90 €",
    unit: "59,97 € / livre",
    saving: "Économie 59,80 €",
    features: ["Pour toute la famille", "Petit-enfant, enfant, conjoint", "Frais de port offerts"],
  },
];

const PRO_TYPES = [
  "EHPAD",
  "Associations",
  "Clubs du 3ᵉ âge",
  "CCAS",
  "Collectivités territoriales",
  "Structures médicalisées",
  "Médiathèques",
  "Bibliothèques",
];

export default function PrintedBookPricing() {
  return (
    <div className="mt-16 space-y-14" data-testid="printed-book-pricing">
      {/* ==================== LIVRE IMPRIMÉ ==================== */}
      <section>
        <div className="text-center max-w-2xl mx-auto mb-8">
          <span className="inline-block bg-mustard text-navy font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            📖 Livre imprimé
          </span>
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="printed-book-title">
            Votre Livre de Vie, <span className="text-terracotta italic">en vrai</span>
          </h2>
          <p className="text-navy/70 leading-relaxed">
            <span className="inline-flex items-center gap-1 bg-[#3D9970]/15 text-[#2A7350] font-bold px-3 py-1 rounded-full text-sm">
              <Check className="w-4 h-4" /> PDF gratuit inclus
            </span>{" "}
            pour tous les abonnés. L&apos;impression est optionnelle : format A5, couverture rigide couleur, envoyé chez vous.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5" data-testid="printed-book-grid">
          {BOOK_OFFERS.map((o, i) => (
            <motion.div
              key={o.key}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              className={`relative bg-white rounded-3xl p-6 border-2 flex flex-col ${
                o.highlight ? "border-terracotta shadow-warm scale-[1.02] ring-4 ring-terracotta/15" : "border-cream-dark"
              }`}
              data-testid={`printed-book-card-${o.key}`}
            >
              {o.badge && (
                <span
                  data-testid={`printed-book-badge-${o.key}`}
                  className="absolute -top-3 left-1/2 -translate-x-1/2 bg-terracotta text-white text-[11px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-warm inline-flex items-center gap-1"
                >
                  <Star className="w-3 h-3 fill-current" /> {o.badge}
                </span>
              )}
              <div className="text-4xl mb-2">{o.emoji}</div>
              <h3 className="font-display text-2xl font-extrabold text-navy mb-1">{o.title}</h3>
              <div className="mb-1">
                <span className="font-display text-4xl font-extrabold text-bordeaux">{o.price}</span>
              </div>
              <p className="text-sm text-navy/60 mb-1">{o.unit}</p>
              {o.saving && (
                <p className="text-sm font-bold text-[#2A7350] mb-3">{o.saving}</p>
              )}
              <ul className="my-4 space-y-2 flex-1">
                {o.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-navy/80 text-sm">
                    <Check className="w-4 h-4 mt-0.5 shrink-0 text-terracotta" strokeWidth={3} />
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="mailto:contact@generaquiz.fr?subject=Commande%20Livre%20de%20Vie%20imprim%C3%A9"
                data-testid={`printed-book-cta-${o.key}`}
                className={`inline-flex items-center justify-center gap-2 font-bold px-5 py-3 rounded-full transition min-h-[52px] ${
                  o.highlight
                    ? "bg-terracotta text-white hover:bg-terracotta-dark shadow-warm"
                    : "bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream"
                }`}
              >
                <BookOpen className="w-4 h-4" /> Commander
              </a>
            </motion.div>
          ))}
        </div>
        <p className="text-center text-xs text-navy/50 mt-4">
          <Sparkles className="w-3 h-3 inline mr-1" />
          Impression à la demande · Livraison France métropolitaine ~10 jours ouvrés · Vous validez la maquette avant impression
        </p>
      </section>

      {/* ==================== OFFRE PRO ==================== */}
      <section>
        <div className="text-center max-w-2xl mx-auto mb-8">
          <span className="inline-block bg-navy text-cream font-bold px-4 py-1.5 rounded-full text-xs uppercase tracking-wider mb-4">
            🏥 Offre Pro
          </span>
          <h2 className="font-display text-3xl md:text-4xl font-extrabold text-navy mb-3" data-testid="pro-offer-title">
            Pour les <span className="text-terracotta italic">professionnels du lien social</span>
          </h2>
          <p className="text-navy/70 leading-relaxed">
            Un espace animateur dédié, des séances collectives, des tableaux de bord établissement — pensé pour tous ceux qui accompagnent nos aînés au quotidien.
          </p>
        </div>

        <div className="bg-white rounded-3xl border-2 border-navy/20 p-6 md:p-8 max-w-4xl mx-auto" data-testid="pro-offer-card">
          <div className="flex items-start gap-4 mb-5">
            <div className="w-14 h-14 rounded-2xl bg-navy text-cream flex items-center justify-center shrink-0">
              <Building2 className="w-7 h-7" />
            </div>
            <div>
              <h3 className="font-display text-2xl font-extrabold text-navy mb-1">GénéraQuiz Pro</h3>
              <p className="text-navy/70">Adapté à votre structure. Devis personnalisé sous 48 h.</p>
            </div>
          </div>

          <div className="mb-5">
            <p className="text-sm font-bold text-navy/60 uppercase tracking-wider mb-2">Pour qui ?</p>
            <div className="flex flex-wrap gap-2" data-testid="pro-offer-types">
              {PRO_TYPES.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 bg-cream border-2 border-cream-dark px-3 py-1 rounded-full text-sm text-navy/80 font-semibold"
                >
                  <Check className="w-3.5 h-3.5 text-terracotta" strokeWidth={3} />
                  {t}
                </span>
              ))}
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <ul className="space-y-2 text-navy/80">
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Espace animateur & résidents illimités</li>
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Séances collectives (quiz + ateliers mémoire)</li>
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Discussion prompts pour lancer les conversations</li>
            </ul>
            <ul className="space-y-2 text-navy/80">
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Tableau de bord d&apos;établissement</li>
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Formation initiale & support dédié</li>
              <li className="flex items-start gap-2"><Check className="w-4 h-4 mt-1 text-terracotta shrink-0" strokeWidth={3}/>Facturation groupée sur devis</li>
            </ul>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-cream rounded-2xl p-4">
            <p className="text-navy/70 text-sm">
              <strong className="text-navy">Tarif indicatif :</strong> à partir de 59 €/mois par établissement.
              <br className="hidden sm:inline" />
              Devis sur mesure selon le nombre de résidents et d&apos;animateurs.
            </p>
            <a
              href="mailto:contact@generaquiz.fr?subject=Demande%20de%20devis%20Pro"
              data-testid="pro-offer-cta"
              className="inline-flex items-center justify-center gap-2 bg-navy text-cream font-bold px-6 py-3 rounded-full hover:bg-navy-dark transition min-h-[52px] whitespace-nowrap"
            >
              <Building2 className="w-4 h-4" /> Demander un devis
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
