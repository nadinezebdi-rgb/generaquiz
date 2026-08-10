"""Charades game — French charades organized in themed packs.

Each charade has been VERIFIED manually: the syllable decomposition must
REALLY match the final word when spoken aloud in French. Answer is normalized
(no accents, lowercase) for tolerant comparison.

Packs
-----
  classique — timeless everyday charades (13)
  nature    — flora & fauna (4)
  cuisine   — food & ingredients (2)

Adding a new charade
--------------------
  1. Read it out loud: the pronounced syllables of the answer MUST match
     the individual clues. If you have to squint, discard it.
  2. Add a `pack` field.
  3. The assertion at the end of the file catches display/normalized mismatch.
"""

# Pack metadata (order controls the UI tab order)
PACKS: list[dict] = [
    {"id": "classique", "label": "Classiques",   "emoji": "🎭", "desc": "Les charades du quotidien"},
    {"id": "nature",    "label": "Nature",       "emoji": "🌿", "desc": "Faune, flore et saisons"},
    {"id": "cuisine",   "label": "Cuisine",      "emoji": "🍽️", "desc": "Saveurs et légumes"},
]

CHARADES: list[dict] = [
    # ===================== PACK CLASSIQUE =====================
    {"id": "ch01", "pack": "classique",
     "parts": ["Mon premier miaule sur les toits.",
               "Mon deuxième se boit et coule dans les rivières.",
               "Mon tout est une grande demeure ancienne."],
     "answer_display": "Château", "answer": "chateau", "hint": "Chat + eau. Un noble y habitait."},
    {"id": "ch02", "pack": "classique",
     "parts": ["Mon premier est un adjectif qui signifie « agréable ».",
               "Mon deuxième est le contraire de la nuit.",
               "Mon tout est une salutation du matin."],
     "answer_display": "Bonjour", "answer": "bonjour", "hint": "Bon + jour."},
    {"id": "ch03", "pack": "classique",
     "parts": ["Mon premier est un petit parasite qui s'invite dans les cheveux.",
               "Mon deuxième est le contraire de « beau ».",
               "Mon tout se rôtit à la broche et se sert à table."],
     "answer_display": "Poulet", "answer": "poulet", "hint": "Pou + laid. Une volaille."},
    {"id": "ch04", "pack": "classique",
     "parts": ["Mon premier est une boisson alcoolisée rouge ou blanche.",
               "Mon deuxième est un adjectif signifiant « acide, désagréable ».",
               "Mon tout est un condiment qui accompagne la salade."],
     "answer_display": "Vinaigre", "answer": "vinaigre", "hint": "Vin + aigre."},
    {"id": "ch05", "pack": "classique",
     "parts": ["Mon premier est une ancienne petite pièce de monnaie.",
               "Mon deuxième est une céréale que l'on mange souvent en Asie.",
               "Mon tout est un petit rongeur gris."],
     "answer_display": "Souris", "answer": "souris", "hint": "Sou + riz."},
    {"id": "ch06", "pack": "classique",
     "parts": ["Mon premier est un article défini féminin.",
               "Mon deuxième se mange à tous les repas, croustillant.",
               "Mon tout est un petit animal aux longues oreilles."],
     "answer_display": "Lapin", "answer": "lapin", "hint": "La + pain."},
    {"id": "ch07", "pack": "classique",
     "parts": ["Mon premier miaule.",
               "Mon deuxième est un pronom personnel indéfini.",
               "Mon tout est le petit du chat."],
     "answer_display": "Chaton", "answer": "chaton", "hint": "Chat + on."},
    {"id": "ch08", "pack": "classique",
     "parts": ["Mon premier est une petite étendue d'eau stagnante.",
               "Mon deuxième est un petit insecte qui abîme les vêtements.",
               "Mon tout est une grande casserole ronde."],
     "answer_display": "Marmite", "answer": "marmite", "hint": "Mare + mite."},
    {"id": "ch09", "pack": "classique",
     "parts": ["Mon premier miaule.",
               "Mon deuxième recouvre notre corps.",
               "Mon tout se pose sur la tête."],
     "answer_display": "Chapeau", "answer": "chapeau", "hint": "Chat + peau."},
    {"id": "ch10", "pack": "classique",
     "parts": ["Mon premier est un adjectif qui signifie « agréable, savoureux ».",
               "Mon deuxième est le même mot que le premier.",
               "Mon tout est une friandise sucrée que les enfants adorent."],
     "answer_display": "Bonbon", "answer": "bonbon", "hint": "Bon + bon."},
    {"id": "ch11", "pack": "classique",
     "parts": ["Mon premier est un adjectif possessif féminin (« à moi »).",
               "Mon deuxième est un arbre à aiguilles vert toute l'année.",
               "Mon tout est l'arbre traditionnel de Noël."],
     "answer_display": "Sapin", "answer": "sapin", "hint": "Sa + pin."},
    {"id": "ch12", "pack": "classique",
     "parts": ["Mon premier est un métal précieux jaune.",
               "Mon deuxième est une créature ailée des Cieux.",
               "Mon tout est un agrume rond à la peau colorée."],
     "answer_display": "Orange", "answer": "orange", "hint": "Or + ange."},
    {"id": "ch13", "pack": "classique",
     "parts": ["Mon premier est un petit véhicule à moteur.",
               "Mon deuxième est le nom d'une grande hotte de cheminée.",
               "Mon tout est un légume orange que les lapins adorent."],
     "answer_display": "Carotte", "answer": "carotte", "hint": "Car + hotte."},

    # ===================== PACK NATURE =====================
    {"id": "n01", "pack": "nature",
     "parts": ["Mon premier est un cervidé du Grand Nord.",
               "Mon deuxième désigne la peinture, la sculpture, la musique.",
               "Mon tout est un animal rusé au pelage roux."],
     "answer_display": "Renard", "answer": "renard", "hint": "Renne + art."},
    {"id": "n02", "pack": "nature",
     "parts": ["Mon premier est un oiseau de la basse-cour, chef du poulailler.",
               "Mon deuxième est un meuble sur lequel on dort.",
               "Mon troisième est l'abréviation de « compagnie ».",
               "Mon tout est une fleur rouge des champs."],
     "answer_display": "Coquelicot", "answer": "coquelicot", "hint": "Coq + lit + co."},
    {"id": "n03", "pack": "nature",
     "parts": ["Mon premier est une interjection de surprise.",
               "Mon deuxième est une céréale qui pousse dans l'eau.",
               "Mon troisième est un adjectif possessif masculin (« à lui »).",
               "Mon tout est un petit animal couvert de piquants."],
     "answer_display": "Hérisson", "answer": "herisson", "hint": "Hé + ris + son."},
    {"id": "n04", "pack": "nature",
     "parts": ["Mon premier est un grand bâtiment vertical (comme celle d'Eiffel).",
               "Mon deuxième est la planète sur laquelle nous vivons.",
               "Mon troisième est un pronom personnel féminin.",
               "Mon tout est un oiseau qui roucoule."],
     "answer_display": "Tourterelle", "answer": "tourterelle", "hint": "Tour + terre + elle."},

    # ===================== PACK CUISINE =====================
    {"id": "c01", "pack": "cuisine",
     "parts": ["Mon premier est un fruit à pépins de forme allongée.",
               "Mon deuxième se boit et coule dans les rivières.",
               "Mon tout est un légume long et vert, ingrédient de la soupe."],
     "answer_display": "Poireau", "answer": "poireau", "hint": "Poire + eau."},
    {"id": "c02", "pack": "cuisine",
     "parts": ["Mon premier est un condiment piquant que l'on met dans le moulin.",
               "Mon deuxième est un pronom personnel indéfini.",
               "Mon tout est un légume rouge, jaune ou vert, à farcir."],
     "answer_display": "Poivron", "answer": "poivron", "hint": "Poivre + on."},
]


def normalize(text: str) -> str:
    """Lowercase, strip accents, remove non-alphanumerics for comparison."""
    import unicodedata
    s = text.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum())


PACK_IDS = {p["id"] for p in PACKS}
assert all(c.get("pack") in PACK_IDS for c in CHARADES), "Charade with unknown pack id"
assert all(normalize(c["answer_display"]) == c["answer"] for c in CHARADES), \
    "Charade answer/answer_display mismatch"


def charades_for_pack(pack_id: str | None) -> list[dict]:
    if not pack_id or pack_id == "all":
        return CHARADES
    return [c for c in CHARADES if c["pack"] == pack_id]
