/** Questions de démonstration de l'accueil : deux tirées au hasard à chaque chargement (une par bloc). */
const DEMO_QUESTIONS = [
  {
    category: "Chansons d'antan",
    mascot: "chansons.png",
    mascotName: "Yvette la Chanteuse",
    question: "Quel chanteur français a composé et interprété « La Mer » en 1946 ?",
    options: ["Édith Piaf", "Charles Trenet", "Jacques Brel", "Georges Brassens"],
    correct: 1,
    explanation: "Charles Trenet a composé « La Mer » en 1943 et l'a enregistrée en 1946.",
  },
  {
    category: "Années 80",
    mascot: "culture-40-ans.png",
    mascotName: "Sophie la Quadra",
    question: "Quel groupe français chante « L'Aventurier » en 1982 ?",
    options: ["Téléphone", "Indochine", "Images", "Gold"],
    correct: 1,
    explanation: "« L'Aventurier » est le tube d'Indochine sorti en 1982, sur l'album du même nom.",
  },
  {
    category: "Années 90-2000",
    mascot: "culture-40-ans.png",
    mascotName: "Sophie la Quadra",
    question: "En quelle année la France remporte-t-elle sa première Coupe du monde de football ?",
    options: ["1994", "1998", "2002", "2006"],
    correct: 1,
    explanation: "Le 12 juillet 1998, la France bat le Brésil 3-0 en finale au Stade de France.",
  },
  {
    category: "Aujourd'hui",
    mascot: "voyages-france.png",
    mascotName: "Jeanne la Voyageuse",
    question: "Quelle ville a accueilli les Jeux olympiques d'été en 2024 ?",
    options: ["Tokyo", "Paris", "Los Angeles", "Londres"],
    correct: 1,
    explanation: "Paris a accueilli les Jeux d'été 2024, cent ans après ceux de 1924.",
  },
];

const first = Math.floor(Math.random() * DEMO_QUESTIONS.length);
const second = (first + 1 + Math.floor(Math.random() * (DEMO_QUESTIONS.length - 1))) % DEMO_QUESTIONS.length;

export const HERO_DEMO_QUESTION = DEMO_QUESTIONS[first];
export const BLOCK_DEMO_QUESTION = DEMO_QUESTIONS[second];
