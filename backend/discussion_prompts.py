"""Enrichissement des questions existantes avec `discussion_prompt`.

Stratégie positionnelle : pour chaque catégorie ciblée, on enrichit les N
premières questions (sans écraser un discussion_prompt existant). Les
formulations sont des relances de conversation adaptées au thème, pensées
pour l'usage EHPAD.
"""
from __future__ import annotations

from core import db, logger


# Pour chaque catégorie : liste de discussion prompts (indexée sur les N
# premières questions retournées par ordre naturel Mongo).
DISCUSSION_PROMPTS_BY_CATEGORY: dict[str, list[str]] = {
    "cuisine-terroir": [
        "Avez-vous un souvenir de cuisine partagée avec votre mère ou grand-mère ?",
        "Quel plat de votre enfance aimeriez-vous refaire aujourd'hui ?",
        "Y avait-il un dessert emblématique le dimanche dans votre famille ?",
        "Racontez-nous un repas de famille dont vous vous souvenez encore.",
        "Quelle boisson chaude évoque le mieux votre enfance ?",
    ],
    "chansons": [
        "Quelle chanson vous rappelle instantanément vos 20 ans ?",
        "Quel artiste faisait rêver toute votre génération ?",
        "Vous souvenez-vous d'un bal ou d'un mariage où vous avez beaucoup dansé ?",
        "Y a-t-il une chanson que vous chantiez en famille ou à l'école ?",
        "Quel refrain vous fait aujourd'hui encore chanter à tue-tête ?",
    ],
    "cinema": [
        "Vous rappelez-vous du premier film que vous avez vu au cinéma ?",
        "Quel acteur ou actrice de votre jeunesse vous faisait le plus rêver ?",
        "Un film qui vous a fait pleurer ou beaucoup rire — racontez.",
        "Alliez-vous au cinéma en famille ou avec des amis ?",
        "Quel film aimeriez-vous montrer aujourd'hui à vos petits-enfants ?",
    ],
    "annees-50-60": [
        "Vous souvenez-vous de la première télévision entrée à la maison ?",
        "Quel objet emblématique des années 60 vous manque aujourd'hui ?",
        "Quel événement de ces années-là a le plus marqué votre jeunesse ?",
        "Comment fêtait-on Noël dans votre famille à cette époque ?",
        "Quelle mode ou coiffure des années 60 vous rappelle vos 20 ans ?",
    ],
    "culture-70-ans": [
        "Quelle grande invention de votre vie vous a le plus impressionné(e) ?",
        "Quel événement mondial vous a marqué(e) le plus fortement ?",
        "Un livre ou un discours qui a changé votre vision du monde ?",
    ],
    "culture-40-ans": [
        "Quel dessin animé du samedi matin vous rappelle votre enfance ?",
        "Un jouet phare de votre enfance dont vous vous souvenez avec tendresse ?",
        "Quel morceau des années 90 vous fait immédiatement sourire ?",
    ],
    "objets-antan": [
        "Quel objet ancien avez-vous encore chez vous et pourquoi y tenez-vous ?",
        "Un objet que vous n'utilisez plus mais qui vous manque ?",
        "Racontez la première fois où vous avez utilisé un appareil moderne (ordinateur, portable).",
    ],
    "histoire-france": [
        "Quel événement historique vous rappelle un moment fort de votre vie ?",
        "Un personnage historique que vous admirez particulièrement — pourquoi ?",
        "Que faisiez-vous le jour où vous avez appris [événement marquant, ex. mai 68] ?",
    ],
}


async def enrich_existing_questions() -> int:
    """Applique idempotemment un discussion_prompt aux N premières questions
    de chaque catégorie ciblée. Ne touche pas aux entrées qui en ont déjà un.
    """
    n_updated = 0
    for cat_id, prompts in DISCUSSION_PROMPTS_BY_CATEGORY.items():
        # Récupère les N premières questions de la catégorie qui n'ont PAS
        # déjà un discussion_prompt (par ordre d'insertion Mongo).
        cursor = db.questions.find(
            {
                "category_id": cat_id,
                "$or": [{"discussion_prompt": {"$exists": False}}, {"discussion_prompt": ""}],
            },
            {"_id": 1},
        ).limit(len(prompts))
        targets = await cursor.to_list(len(prompts))
        for oid_doc, prompt in zip(targets, prompts):
            r = await db.questions.update_one(
                {"_id": oid_doc["_id"]},
                {"$set": {"discussion_prompt": prompt}},
            )
            if r.modified_count:
                n_updated += 1
    if n_updated:
        logger.info(f"[discussion-prompts] enrichi {n_updated} question(s) existantes")
    return n_updated
