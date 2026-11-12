/** Univers de catégories (tableau de bord + accueil). Les cartes « Bientôt » n'existent que côté frontend. */
export const UNIVERSES = [
  { id: "epoques", title: "Par époque" },
  { id: "intemporels", title: "Intemporels" },
  { id: "nostalgie", title: "Nostalgie" },
];

const SOON = [
  { id: "soon-annees-80", title: "Années 80", group: "epoques", sort_order: 1.5, soon: true,
    description: "Les tubes, la télé et les grands moments des années 80." },
  { id: "soon-2010", title: "2010 à aujourd'hui", group: "epoques", sort_order: 999, soon: true,
    description: "Smartphones, séries et événements des quinze dernières années." },
];

export function groupCategories(categories, { withSoon = true } = {}) {
  const all = [...categories, ...(withSoon ? SOON : [])];
  return UNIVERSES.map((u) => ({
    ...u,
    items: all
      .filter((c) => (UNIVERSES.some((x) => x.id === c.group) ? c.group : "intemporels") === u.id)
      .sort((a, b) => (a.sort_order ?? 500) - (b.sort_order ?? 500)),
  }));
}
