"""Prompts et catalogue de thèmes pour Quiz d'Antan.

Ce module centralise les consignes envoyées à Mistral afin de générer
 des quiz intergénérationnels, variés et accessibles.
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict


Category = Literal["nostalgie", "moderne", "intemporel", "culture"]
Difficulty = Literal["facile", "moyen", "difficile", "mixte"]
Era = Literal["1950-1980", "1980-2000", "2000-2020", "intemporel", "mixte"]


class ThemeMetadata(TypedDict):
    """Métadonnées d'un thème proposé aux joueurs."""

    key: str
    label: str
    description: str
    category: Category
    era: Era
    target_difficulty: Difficulty


SYSTEM_PROMPT: Final[str] = """
Tu es le moteur de génération de quiz de « Quiz d'Antan », une plateforme
intergénérationnelle conçue pour faire jouer ensemble grands-parents, parents,
adolescents et enfants à partir de 8 ans.

Objectif principal : créer des questions conviviales, compréhensibles et
variées, qui donnent à chaque génération une chance de briller. Une même
session ne doit jamais rester bloquée sur une seule époque ou un seul public.

Univers de thèmes intergénérationnels à mélanger :

1) Nostalgie (années 50-80)
- chansons françaises populaires, yéyés, variété française ;
- cinéma français et grands classiques familiaux ;
- télévision d'antan, émissions, feuilletons, présentateurs connus ;
- publicités célèbres, objets du quotidien, marques mémorables ;
- jouets, jeux de cour, jeux de société, loisirs familiaux.

2) Culture populaire moderne (années 90-2020)
- films d'animation et grands succès familiaux ;
- jeux vidéo connus, consoles populaires, personnages emblématiques ;
- musique pop, rap accessible, tubes internationaux et français ;
- séries, dessins animés, phénomènes numériques simples à comprendre ;
- références récentes adaptées à un public familial.

3) Intemporel
- géographie de la France, régions, villes, monuments et paysages ;
- cuisine française, recettes, spécialités régionales, ingrédients ;
- nature, saisons, plantes, météo, environnement du quotidien ;
- sport français et international connu du grand public ;
- histoire générale, grandes périodes et personnages majeurs.

4) Culture générale accessible
- science amusante, expériences simples, corps humain, espace ;
- animaux domestiques, animaux sauvages, records naturels ;
- proverbes, expressions françaises, vocabulaire courant ;
- petites connaissances utiles, étonnantes ou drôles.

Règles de génération obligatoires :
- Varier les époques dans une même session : inclure, quand le thème le permet,
  des références anciennes, modernes et intemporelles.
- Alterner les niveaux : questions faciles pour enfants 8+, questions moyennes
  pour adolescents/adultes, et quelques questions « défi grand-parent » quand
  le thème s'y prête.
- Éviter les questions trop techniques, trop spécialisées, ambiguës ou basées
  sur des détails obscurs.
- Les questions doivent être positives, familiales, inclusives et adaptées à un
  jeu entre générations.
- Chaque question doit avoir exactement 4 choix distincts.
- Le champ "answer" doit contenir exactement le texte d'un des choix.
- Ne pas inventer de faits douteux. Si une information est incertaine, choisir
  une question plus générale.
- Répondre uniquement en JSON valide, sans Markdown, sans ```json, sans phrase
  d'introduction et sans commentaire.

Format de sortie strict attendu : un tableau JSON, et rien d'autre.
[
  {
    "question": "...",
    "choices": ["A", "B", "C", "D"],
    "answer": "A",
    "difficulty": "facile|moyen|difficile",
    "category": "nostalgie|moderne|intemporel|culture",
    "era": "1950-1980|1980-2000|2000-2020|intemporel"
  }
]
""".strip()


USER_PROMPT_TEMPLATES: Final[dict[str, str]] = {
    "chansons des années 70": (
        "Génère {nb} questions sur les chansons françaises et tubes populaires "
        "des années 70. Ajoute quelques passerelles avec des reprises ou souvenirs "
        "familiaux connus pour rendre le quiz jouable par plusieurs générations."
    ),
    "films d'animation": (
        "Génère {nb} questions sur les films d'animation familiaux, en mélangeant "
        "classiques plus anciens et films des années 1990 à 2020."
    ),
    "cuisine française": (
        "Génère {nb} questions sur la cuisine française, les spécialités régionales, "
        "les ingrédients du quotidien et les traditions familiales autour des repas."
    ),
    "sport français": (
        "Génère {nb} questions sur le sport en France : grands événements, sportifs "
        "connus, règles simples et souvenirs collectifs."
    ),
    "jeux des années 80": (
        "Génère {nb} questions sur les jeux, jouets, jeux de société, consoles et "
        "loisirs des années 80, avec des formulations compréhensibles par les enfants."
    ),
    "animaux et nature": (
        "Génère {nb} questions sur les animaux, la nature, les saisons, les records "
        "amusants et les observations du quotidien."
    ),
    "histoire de France": (
        "Génère {nb} questions accessibles sur l'histoire de France : grandes périodes, "
        "personnages connus, monuments et événements enseignés à l'école."
    ),
    "TV et pub d'antan": (
        "Génère {nb} questions sur la télévision, les émissions familiales, les slogans "
        "publicitaires et les souvenirs médiatiques des années 1950 à 1980."
    ),
    "musique moderne": (
        "Génère {nb} questions sur la musique moderne des années 1990 à 2020 : pop, "
        "variété, artistes connus et chansons familiales ou très populaires."
    ),
    "géographie France": (
        "Génère {nb} questions sur la géographie de la France : régions, villes, fleuves, "
        "montagnes, monuments et spécialités locales."
    ),
}


THEME_CATALOG: Final[list[ThemeMetadata]] = [
    {
        "key": "chansons des années 70",
        "label": "Chansons des années 70",
        "description": "Variété française, tubes populaires et souvenirs musicaux familiaux.",
        "category": "nostalgie",
        "era": "1950-1980",
        "target_difficulty": "mixte",
    },
    {
        "key": "films d'animation",
        "label": "Films d'animation",
        "description": "Classiques familiaux et films d'animation récents.",
        "category": "moderne",
        "era": "mixte",
        "target_difficulty": "facile",
    },
    {
        "key": "cuisine française",
        "label": "Cuisine française",
        "description": "Recettes, ingrédients et spécialités régionales.",
        "category": "intemporel",
        "era": "intemporel",
        "target_difficulty": "mixte",
    },
    {
        "key": "sport français",
        "label": "Sport français",
        "description": "Événements, champions et règles simples du sport.",
        "category": "intemporel",
        "era": "mixte",
        "target_difficulty": "moyen",
    },
    {
        "key": "jeux des années 80",
        "label": "Jeux des années 80",
        "description": "Jouets, jeux de société, loisirs et premières consoles.",
        "category": "nostalgie",
        "era": "1950-1980",
        "target_difficulty": "mixte",
    },
    {
        "key": "animaux et nature",
        "label": "Animaux et nature",
        "description": "Animaux, saisons, records naturels et science amusante.",
        "category": "culture",
        "era": "intemporel",
        "target_difficulty": "facile",
    },
    {
        "key": "histoire de France",
        "label": "Histoire de France",
        "description": "Grandes périodes, personnages et événements connus.",
        "category": "intemporel",
        "era": "intemporel",
        "target_difficulty": "moyen",
    },
    {
        "key": "TV et pub d'antan",
        "label": "TV et pub d'antan",
        "description": "Émissions, slogans, présentateurs et souvenirs télévisuels.",
        "category": "nostalgie",
        "era": "1950-1980",
        "target_difficulty": "difficile",
    },
    {
        "key": "musique moderne",
        "label": "Musique moderne",
        "description": "Pop, variété, artistes et tubes des années 1990 à 2020.",
        "category": "moderne",
        "era": "2000-2020",
        "target_difficulty": "mixte",
    },
    {
        "key": "géographie France",
        "label": "Géographie France",
        "description": "Régions, villes, fleuves, montagnes et monuments français.",
        "category": "intemporel",
        "era": "intemporel",
        "target_difficulty": "facile",
    },
]


DEFAULT_INTERGENERATIONAL_PROMPT: Final[str] = (
    "Génère {nb} questions pour une session intergénérationnelle complète. "
    "Mélange volontairement nostalgie des années 50-80, culture moderne des années "
    "90-2020, sujets intemporels et culture générale accessible. Le thème demandé "
    "est : {theme}."
)


def build_user_prompt(theme: str, nb: int) -> str:
    """Construit le prompt utilisateur le plus adapté au thème demandé."""

    normalized_theme = theme.strip().lower()
    template = USER_PROMPT_TEMPLATES.get(normalized_theme)
    if template is None:
        template = DEFAULT_INTERGENERATIONAL_PROMPT
    return template.format(theme=theme.strip(), nb=nb)


def list_theme_keys() -> list[str]:
    """Retourne les clés de thèmes disponibles."""

    return [theme["key"] for theme in THEME_CATALOG]
