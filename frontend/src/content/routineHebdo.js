/**
 * Habitudes de la routine hebdomadaire « Bien vieillir ».
 *
 * Chaque habitude est adossée à une recommandation citée dans les fiches —
 * ne pas en ajouter sans source. `id` est persisté en localStorage et, à terme,
 * en base : ne JAMAIS renommer un id existant (cela effacerait l'historique
 * des utilisateurs). Pour retirer une habitude, la marquer `retired: true`
 * plutôt que la supprimer.
 *
 * Le backend garde la même liste dans `backend/routers/bien_vieillir.py`.
 * Les deux doivent rester alignés — voir le test d'alignement côté backend.
 */
export const ROUTINE_VERSION = 1;

/** Nombre d'habitudes à cocher pour qu'une semaine compte dans la série. */
export const WEEK_VALID_THRESHOLD = 4;

export const HABITS = [
  {
    id: "marche",
    emoji: "🚶",
    label: "Bouger 30 minutes, 5 jours",
    help: "L'OMS recommande au moins 150 minutes d'activité modérée par semaine après 65 ans.",
  },
  {
    id: "equilibre",
    emoji: "🤸",
    label: "Deux séances d'équilibre ou de renforcement",
    help: "Au moins deux fois par semaine, sur des jours non consécutifs. C'est le principal levier de prévention des chutes.",
  },
  {
    id: "memoire",
    emoji: "🧠",
    label: "Trois séances de stimulation cognitive",
    help: "Le seuil à partir duquel les études mesurent un effet (Verghese et al., NEJM, 2003).",
  },
  {
    id: "lien",
    emoji: "💬",
    label: "Trois vraies conversations",
    help: "En face à face ou au téléphone. L'engagement social régulier est associé à un risque de dépression tardive divisé par deux.",
  },
  {
    id: "sortie",
    emoji: "🌤️",
    label: "Sortir de chez soi cinq jours",
    help: "9 millions de personnes de 60 ans et plus ne sortent pas quotidiennement (Baromètre Petits Frères des Pauvres, 2025).",
  },
  {
    id: "sommeil",
    emoji: "🌙",
    label: "Des horaires de sommeil réguliers",
    help: "C'est pendant la nuit que les souvenirs de la journée se consolident.",
  },
];

export const HABIT_IDS = HABITS.map((h) => h.id);
