/**
 * pricing.js — source de vérité unique pour la grille tarifaire GénéraQuiz.
 *
 * ⚠️ AUCUN prix ne doit être écrit en dur dans les composants JSX. Tout dérive
 * de ce fichier via les helpers plus bas.
 *
 * Migration en cours (Stripe backend inchangé pour l'instant, une itération
 * séparée créera les vrais price IDs). Anciens plans → nouveaux :
 *   club_memoire  → solo
 *   famille       → famille (prix ajusté)
 *   premium       → heritage (annuel uniquement)
 */

export const PLANS = [
  {
    id: "decouverte",
    nom: "Découverte",
    tagline: "Pour découvrir GénéraQuiz",
    mensuel: 0,
    annuel: 0,
    comptes: 1,
    populaire: false,
    annuelUniquement: false,
    stripeIds: { monthly: null, yearly: null },
    features: [
      "Quiz du Jour complet",
      "3 catégories en illimité",
      "Historique 30 jours",
      "3 badges de démarrage",
    ],
    cta: "Commencer gratuitement",
    ctaTo: "/register",
  },
  {
    id: "solo",
    nom: "Solo",
    tagline: "Pour jouer seul, à votre rythme",
    mensuel: 6.99,
    annuel: 69,
    comptes: 1,
    populaire: false,
    annuelUniquement: false,
    stripeIds: { monthly: "solo_monthly", yearly: "solo_yearly" },    features: [
      "Quiz illimités toutes catégories",
      "Progression et badges",
      "Historique complet",
      "Streaks et Ligues hebdomadaires",
      "Livre de Vie en PDF",
      "−20 % sur le livre imprimé",
    ],
    cta: "Choisir Solo",
  },
  {
    id: "famille",
    nom: "Famille",
    tagline: "Pour partager en famille",
    mensuel: 9.99,
    annuel: 99,
    comptes: 6,
    populaire: true,
    annuelUniquement: false,
    stripeIds: { monthly: "famille_v2_monthly", yearly: "famille_v2_yearly" },
    features: [
      "Tout Solo, pour 6 personnes",
      "Classement familial privé",
      "Défis coopératifs illimités",
      "Quiz privés entre proches",
      "Notifications famille",
      "Score Mémoire 5 axes",
      "−25 % sur le livre imprimé",
    ],
    cta: "Choisir Famille",
  },
  {
    id: "heritage",
    nom: "Héritage",
    tagline: "L'abonnement + un livre imprimé chaque année",
    mensuel: null,
    annuel: 159,
    comptes: 6,
    populaire: false,
    annuelUniquement: true,
    stripeIds: { monthly: null, yearly: "heritage_yearly" },
    features: [
      "Tout Famille",
      "1 Livre de Vie imprimé offert chaque année",
      "Quiz exclusifs en avant-première",
      "Support prioritaire + téléphone",
      "Accès anticipé aux nouveautés",
    ],
    cta: "Choisir Héritage",
    argumentValue:
      "Famille (99 €) + un livre imprimé (79,90 €) = 178,90 € séparément. Vous économisez 19,90 € — et le livre revient chaque année.",
  },
];

// -----------------------------------------------------------------------------
// GIFT SKUs — cadeau
// -----------------------------------------------------------------------------
export const GIFTS = [
  {
    id: "carte_famille",
    nom: "Carte cadeau Famille",
    prix: 99,
    description: "1 an Famille, code envoyé par e-mail ou à imprimer.",
    badge: null,
    stripeId: "gift_famille",
  },
  {
    id: "coffret_heritage",
    nom: "Coffret Héritage",
    prix: 159,
    description: "1 an d'abonnement + le Livre de Vie imprimé.",
    badge: "Notre coffret cadeau",
    highlight: true,
    stripeId: "gift_heritage",
  },
  {
    id: "livre_seul",
    nom: "Le livre seul",
    prix: 79.9,
    description: "Un Livre de Vie imprimé, sans abonnement.",
    badge: null,
    stripeId: "gift_livre",
  },
];

// -----------------------------------------------------------------------------
// LIVRE imprimé (SKUs indépendants de l'abonnement)
// -----------------------------------------------------------------------------
export const PRINTED_BOOKS = [
  { id: "livre_1", nom: "1 livre", prix: 79.9, prixParLivre: 79.9, economie: 0, features: ["Format A5 (15 × 21 cm)", "Jusqu'à 130 pages", "Couverture rigide couleur"] },
  { id: "livre_2", nom: "2 livres", prix: 129.9, prixParLivre: 64.95, economie: 29.9, highlight: true, badge: "Le plus choisi", features: ["Idéal pour offrir", "Impression identique aux 2 exemplaires", "Livraison groupée"] },
  { id: "livre_3", nom: "3 livres", prix: 179.9, prixParLivre: 59.97, economie: 59.8, features: ["Pour toute la famille", "Petit-enfant, enfant, conjoint", "Frais de port offerts"] },
];

// Remise abonné sur le livre imprimé
export const BOOK_DISCOUNT_BY_TIER = {
  decouverte: 0,
  solo: 0.20,
  famille: 0.25,
  heritage: 1.0,   // inclus dans la formule (1 livre/an offert)
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

/** Calcule les données d'affichage pour un plan donné.
 *  Renvoie tout ce qu'il faut au JSX, jamais recalculé côté composant.
 */
export function pricePresentation(plan, period /* 'monthly' | 'yearly' */) {
  const monthly = plan.mensuel;
  const yearly = plan.annuel;

  if (period === "monthly") {
    if (monthly === 0) return { main: "0 €", suffix: "/mois", note: "à vie", available: true };
    if (monthly == null) {
      // Héritage en mode mensuel : non disponible
      return {
        main: fmt(yearly),
        suffix: "/an",
        note: "Disponible en annuel uniquement",
        available: false,
        switchToYearly: true,
      };
    }
    return { main: fmt(monthly), suffix: "/mois", note: null, available: true };
  }

  // period === "yearly"
  if (yearly === 0) return { main: "0 €", suffix: "/an", note: "à vie", available: true };
  const reference = monthly != null ? +(monthly * 12).toFixed(2) : null;
  const economie = reference != null ? +(reference - yearly).toFixed(2) : null;
  const pourcentage = reference && reference > 0 ? Math.round((economie / reference) * 100) : null;
  const parMois = +(yearly / 12).toFixed(2);
  return {
    main: fmt(yearly),
    suffix: "/an",
    monthlyEquivalent: parMois, // "soit X,XX €/mois"
    reference,                  // prix barré
    economie,                   // "Économisez X,XX €"
    pourcentage,                // -18%
    available: true,
  };
}

/** % d'économie appliqué au toggle "Annuel" — calculé sur Famille. */
export function annualDiscountBadge() {
  const famille = PLANS.find((p) => p.id === "famille");
  const ref = famille.mensuel * 12;
  const eco = ref - famille.annuel;
  return `Économisez ${Math.round((eco / ref) * 100)} %`;
}
