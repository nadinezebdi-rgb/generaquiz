"""Charades game — 13 classic French charades, each verified.

Format traditionnel : "Mon premier..." pour chaque syllabe puis "Mon tout...".
Chaque charade a été vérifiée manuellement : la décomposition en syllabes doit
VRAIMENT correspondre au mot final quand on la prononce. La réponse est
normalisée (sans accent, minuscule) pour une comparaison tolérante.
"""

CHARADES: list[dict] = [
    {
        "id": "ch01",
        "parts": [
            "Mon premier miaule sur les toits.",
            "Mon deuxième se boit et coule dans les rivières.",
            "Mon tout est une grande demeure ancienne.",
        ],
        "answer_display": "Château",
        "answer": "chateau",
        "hint": "Chat + eau. Un noble y habitait.",
    },
    {
        "id": "ch02",
        "parts": [
            "Mon premier est un adjectif qui signifie « agréable ».",
            "Mon deuxième est le contraire de la nuit.",
            "Mon tout est une salutation du matin.",
        ],
        "answer_display": "Bonjour",
        "answer": "bonjour",
        "hint": "Bon + jour.",
    },
    {
        "id": "ch03",
        "parts": [
            "Mon premier est un petit parasite qui s'invite dans les cheveux.",
            "Mon deuxième est le contraire de « beau ».",
            "Mon tout se rôtit à la broche et se sert à table.",
        ],
        "answer_display": "Poulet",
        "answer": "poulet",
        "hint": "Pou + laid. Une volaille.",
    },
    {
        "id": "ch04",
        "parts": [
            "Mon premier est une boisson alcoolisée rouge ou blanche.",
            "Mon deuxième est un adjectif signifiant « acide, désagréable ».",
            "Mon tout est un condiment qui accompagne la salade.",
        ],
        "answer_display": "Vinaigre",
        "answer": "vinaigre",
        "hint": "Vin + aigre.",
    },
    {
        "id": "ch05",
        "parts": [
            "Mon premier est une ancienne petite pièce de monnaie.",
            "Mon deuxième est une céréale que l'on mange souvent en Asie.",
            "Mon tout est un petit rongeur gris.",
        ],
        "answer_display": "Souris",
        "answer": "souris",
        "hint": "Sou + riz.",
    },
    {
        "id": "ch06",
        "parts": [
            "Mon premier est un article défini féminin.",
            "Mon deuxième se mange à tous les repas, croustillant.",
            "Mon tout est un petit animal aux longues oreilles.",
        ],
        "answer_display": "Lapin",
        "answer": "lapin",
        "hint": "La + pain.",
    },
    {
        "id": "ch07",
        "parts": [
            "Mon premier miaule.",
            "Mon deuxième est un pronom personnel indéfini.",
            "Mon tout est le petit du chat.",
        ],
        "answer_display": "Chaton",
        "answer": "chaton",
        "hint": "Chat + on.",
    },
    {
        "id": "ch08",
        "parts": [
            "Mon premier est une petite étendue d'eau stagnante.",
            "Mon deuxième est un petit insecte qui abîme les vêtements.",
            "Mon tout est une grande casserole ronde.",
        ],
        "answer_display": "Marmite",
        "answer": "marmite",
        "hint": "Mare + mite.",
    },
    {
        "id": "ch09",
        "parts": [
            "Mon premier miaule.",
            "Mon deuxième recouvre notre corps.",
            "Mon tout se pose sur la tête.",
        ],
        "answer_display": "Chapeau",
        "answer": "chapeau",
        "hint": "Chat + peau.",
    },
    {
        "id": "ch10",
        "parts": [
            "Mon premier est un adjectif qui signifie « agréable, savoureux ».",
            "Mon deuxième est le même mot que le premier.",
            "Mon tout est une friandise sucrée que les enfants adorent.",
        ],
        "answer_display": "Bonbon",
        "answer": "bonbon",
        "hint": "Bon + bon.",
    },
    {
        "id": "ch11",
        "parts": [
            "Mon premier est un adjectif possessif féminin (« à moi »).",
            "Mon deuxième est un arbre à aiguilles vert toute l'année.",
            "Mon tout est l'arbre traditionnel de Noël.",
        ],
        "answer_display": "Sapin",
        "answer": "sapin",
        "hint": "Sa + pin.",
    },
    {
        "id": "ch12",
        "parts": [
            "Mon premier est un métal précieux jaune.",
            "Mon deuxième est une créature ailée des Cieux.",
            "Mon tout est un agrume rond à la peau colorée.",
        ],
        "answer_display": "Orange",
        "answer": "orange",
        "hint": "Or + ange.",
    },
    {
        "id": "ch13",
        "parts": [
            "Mon premier est un petit véhicule à moteur.",
            "Mon deuxième est le nom d'une grande hotte de cheminée.",
            "Mon tout est un légume orange que les lapins adorent.",
        ],
        "answer_display": "Carotte",
        "answer": "carotte",
        "hint": "Car + hotte.",
    },
]


def normalize(text: str) -> str:
    """Lowercase, strip accents, remove non-alphanumerics for comparison."""
    import unicodedata
    s = text.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return "".join(c for c in s if c.isalnum())


# Sanity check: each answer_display, once normalized, must match the answer field
assert all(normalize(c["answer_display"]) == c["answer"] for c in CHARADES), \
    "Charade answer/answer_display mismatch"
