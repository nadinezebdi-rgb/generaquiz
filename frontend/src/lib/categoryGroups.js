/** Univers de catégories (tableau de bord + accueil). */
export const UNIVERSES = [
  { id: "epoques", title: "Par époque" },
  { id: "intemporels", title: "Intemporels" },
  { id: "nostalgie", title: "Nostalgie" },
];

/** En dessous de ce stock, une catégorie s'affiche comme carte « Bientôt » non cliquable. */
export const MIN_PLAYABLE = 20;

export function groupCategories(categories) {
  return UNIVERSES.map((u) => ({
    ...u,
    items: categories
      .filter((c) => (UNIVERSES.some((x) => x.id === c.group) ? c.group : "intemporels") === u.id)
      .map((c) => ((c.count || 0) < MIN_PLAYABLE ? { ...c, soon: true } : c))
      .sort((a, b) => (a.sort_order ?? 500) - (b.sort_order ?? 500)),
  }));
}
