/**
 * pricing.js — source de vérité unique pour la grille tarifaire GénéraQuiz.
 *
 * ⚠️ AUCUN prix ne doit être écrit en dur dans les composants JSX. Tout dérive
 * de ce fichier via les helpers plus bas.
 *
 * 3 formules : Découverte / Solo / Famille. Héritage n'est plus vendu (abonnés
 * existants conservés côté backend). Le livre imprimé est une option séparée.
 */

export const PLANS = [
  {
    id: "decouverte",
    nom: "Découverte",
    tagline: "Pour découvrir GénéraQuiz",
    mensuel: 0,
    annuel: 0,
    acces: "1 compte",
    badge: null,
    stripeIds: { monthly: null, yearly: null },
    features: [
      "Quiz du jour",
      "Aperçu des activités",
      "Sans carte bancaire",
    ],
    cta: "Commencer gratuitement",
    ctaTo: "/register",
  },
  {
    id: "solo",
    nom: "Solo",
    tagline: "Pour jouer seul, à votre rythme",
    mensuel: 6.9,
    annuel: 69,
    annuelNoel: 49,
    acces: "1 accès personnel complet",
    badge: null,
    stripeIds: { monthly: "solo_monthly", yearly: "solo_yearly", yearlyNoel: "solo_yearly_noel" },
    features: [
      "Livre de Vie en PDF",
      "Quiz illimités",
      "Toutes les catégories",
      "Progression et historique",
    ],
    cta: "Choisir Solo",
  },
  {
    id: "famille",
    nom: "Famille",
    tagline: "Pour jouer ensemble",
    mensuel: 9.9,
    annuel: 99,
    annuelNoel: 79,
    acces: "Bénéficiaire + 2 invités",
    badge: "Pour jouer ensemble",
    stripeIds: { monthly: "famille_v2_monthly", yearly: "famille_v2_yearly", yearlyNoel: "famille_v2_yearly_noel" },
    features: [
      "3 personnes : 1 bénéficiaire + 2 invités",
      "Tout Solo pour le bénéficiaire principal",
      "2 invités dans l'espace famille, sans supplément",
      "Quiz, défis et classements familiaux sans limite de parties",
      "Pendant toute la durée de l'abonnement",
      "Chaque proche peut prendre Solo pour son propre catalogue et Livre de Vie",
    ],
    cta: "Choisir Famille",
  },
];

// -----------------------------------------------------------------------------
// GIFT SKUs — cadeau
// -----------------------------------------------------------------------------
export const GIFTS = [
  {
    id: "famille",
    nom: "Carte cadeau Famille",
    description: "1 bénéficiaire + 2 proches pour partager une année de jeux.",
    highlight: true,
  },
  {
    id: "solo",
    nom: "Carte cadeau Solo",
    description: "Une année complète de quiz et de souvenirs pour une personne.",
  },
];

// Accès de chacun dans l'offre Famille (affiché avant l'achat)
export const FAMILY_ACCESS = [
  { label: "Quiz et défis du groupe familial", owner: "Inclus", proches: "Inclus toute l'année" },
  { label: "Classement familial et résultats partagés", owner: "Inclus", proches: "Inclus" },
  { label: "Tout le catalogue pour jouer seul", owner: "Inclus", proches: "Abonnement personnel nécessaire" },
  { label: "Créer son propre Livre de Vie et télécharger son PDF", owner: "Inclus", proches: "Abonnement personnel nécessaire" },
];

// -----------------------------------------------------------------------------
// LIVRE imprimé — option séparée, commandée quand le Livre de Vie est prêt
// -----------------------------------------------------------------------------
export const PRINTED_BOOK = {
  prix: 79.9,
  features: ["Format A5 (15 × 21 cm)", "Jusqu'à 130 pages", "Couverture rigide couleur", "Vous validez la maquette avant impression"],
};

// -----------------------------------------------------------------------------
// PRO (B2B) — Modèle "Résidence" aligné sur Wivy : 1 abonnement annuel flat,
// utilisateurs illimités, engagement 12 mois SANS reconduction tacite, essai
// gratuit, process devis → signature → facture → activation.
// -----------------------------------------------------------------------------
export const PRO_RESIDENCE = {
  id: "pro_residence",
  nom: "Formule Résidence",
  tagline: "1 an d'abonnement, tous vos résidents inclus",
  prixHT: 990,
  prixTTC: 1188,
  duree: "12 mois",
  features: [
    "Utilisateurs illimités dans la résidence",
    "Quiz, Livre de Vie, séances collectives, activités clés en main",
    "Espace animateur dédié + tableau de bord établissement",
    "Formation en ligne + support en français",
    "Sans reconduction tacite (on vous recontacte avant expiration)",
  ],
};

export const PRO_RESEAU = {
  id: "pro_reseau",
  nom: "Formule Réseau",
  tagline: "Pour les groupes multi-établissements",
  onDemand: true,
  features: [
    "Multi-sites (2 résidences ou plus)",
    "Tableau de bord consolidé groupe",
    "Compte gestionnaire + facturation groupée",
    "Formation sur site incluse",
  ],
};

export const PRO_STEPS = [
  { n: 1, title: "Demandez un devis", desc: "En 30 secondes via le formulaire ou par e-mail." },
  { n: 2, title: "Renvoyez le devis signé", desc: "Aucun engagement tacite, tout est transparent." },
  { n: 3, title: "Vous recevez votre facture", desc: "Paiement par virement ou mandat administratif." },
  { n: 4, title: "Votre compte est activé", desc: "Accès instantané pour toute la résidence." },
];

export const PRO_TYPES = [
  "EHPAD",
  "Résidences services seniors",
  "Résidences autonomie",
  "Accueil de jour",
  "Foyers logements",
  "USLD",
  "Associations & clubs du 3ᵉ âge",
  "CCAS & collectivités",
];

// -----------------------------------------------------------------------------
// HELPERS de calcul et de format
// -----------------------------------------------------------------------------
const eurFmt = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
const eurFmt0 = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

/** Format monétaire FR : "9,99 €", "69 €", "1 790 €". */
export function fmt(amount, { integer = false } = {}) {
  if (amount == null) return "—";
  const formatter = integer && Number.isInteger(amount) ? eurFmt0 : eurFmt;
  return formatter.format(amount);
}

// -----------------------------------------------------------------------------
// SUPER PROMO DE NOËL — date fixe, identique pour tous (le serveur applique la même règle)
// -----------------------------------------------------------------------------
export const PROMO_END = new Date("2026-12-31T23:59:59+01:00");
export const isChristmasPromo = (now = new Date()) => now.getTime() <= PROMO_END.getTime();

/** package_id backend selon la période et la promo en cours. */
export function packageFor(plan, period, promo) {
  if (period === "monthly") return plan.stripeIds?.monthly ?? null;
  return (promo ? plan.stripeIds?.yearlyNoel : plan.stripeIds?.yearly) ?? null;
}

/** Comparaison autorisée uniquement avec le mensuel réellement vendu (jamais avec 69 € / 99 €). */
function monthsOffered(plan, annual, word = "offerts") {
  const saving = Math.round((plan.mensuel * 12 - annual) * 100) / 100;
  const months = saving / plan.mensuel;
  const whole = Math.floor(months);
  return { saving, label: `${months - whole > 0.1 ? "Plus de " : ""}${whole} mois ${word}` };
}

/** Bloc prix d'une carte : pastille, prix principal, économie, renouvellement. */
export function offerPresentation(plan, period, promo) {
  if (!plan.mensuel) return { main: "Gratuit" };
  if (period === "monthly") return { main: fmt(plan.mensuel), unit: "/mois", savings: "Sans engagement" };
  if (promo) {
    const { saving, label } = monthsOffered(plan, plan.annuelNoel);
    return {
      pill: "Super promo Noël",
      main: fmt(plan.annuelNoel, { integer: true }), unit: " pour 12 mois",
      savings: `${label} par rapport au mensuel (${fmt(saving)} d'économie)`,
      renewal: `puis ${fmt(plan.annuel, { integer: true })}/an · résiliable à tout moment`,
    };
  }
  const { saving, label } = monthsOffered(plan, plan.annuel, "d'économie");
  return { main: fmt(plan.annuel, { integer: true }), unit: "/an", savings: `${label} par rapport au mensuel (${fmt(saving)} économisés)` };
}

/** Un seul prix affiché selon la période choisie. */
/** Un seul prix affiché selon la période choisie. */
export function pricePresentation(plan, period /* 'monthly' | 'yearly' */) {
  const amount = period === "monthly" ? plan.mensuel : plan.annuel;
  return { main: amount === 0 ? "Gratuit" : fmt(amount, { integer: true }), suffix: amount === 0 ? null : period === "monthly" ? "/mois" : "/an" };
}

/** Bandeau au-dessus des cartes. */
export function annualDiscountBadge(promo = false) {
  if (promo) return "🎄 SUPER PROMO DE NOËL : jusqu'à 4 mois offerts sur l'abonnement annuel, jusqu'au 31 décembre 2026";
  const paid = PLANS.filter((p) => p.mensuel > 0);
  const months = Math.min(...paid.map((p) => Math.round(12 - p.annuel / p.mensuel)));
  return `${months} mois d'économie avec l'abonnement annuel`;
}
