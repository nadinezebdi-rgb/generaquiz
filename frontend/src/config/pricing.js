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
    mensuel: 4.9,
    annuel: 49,
    acces: "1 accès personnel complet",
    badge: null,
    stripeIds: { monthly: "solo_monthly", yearly: "solo_yearly" },
    features: [
      "Quiz illimités",
      "Toutes les catégories",
      "Progression et historique",
      "Livre de Vie en PDF",
    ],
    cta: "Choisir Solo",
  },
  {
    id: "famille",
    nom: "Famille",
    tagline: "Pour jouer ensemble",
    mensuel: 7.9,
    annuel: 79,
    acces: "Accès complet + espace famille",
    badge: "Pour jouer ensemble",
    stripeIds: { monthly: "famille_v2_monthly", yearly: "famille_v2_yearly" },
    features: [
      "Tout Solo pour le bénéficiaire principal",
      "4 proches invités dans l'espace famille, sans supplément",
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
    description: "1 bénéficiaire + 4 proches pour partager une année de jeux.",
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

/** Un seul prix affiché selon la période choisie. */
export function pricePresentation(plan, period /* 'monthly' | 'yearly' */) {
  const amount = period === "monthly" ? plan.mensuel : plan.annuel;
  return { main: amount === 0 ? "Gratuit" : fmt(amount, { integer: true }), suffix: amount === 0 ? null : period === "monthly" ? "/mois" : "/an" };
}

/** L'annuel = 10 mensualités : « 2 mois offerts ». */
export function annualDiscountBadge() {
  const paid = PLANS.filter((p) => p.mensuel > 0);
  const months = Math.min(...paid.map((p) => Math.round(12 - p.annuel / p.mensuel)));
  return `${months} mois offerts avec l'abonnement annuel`;
}
