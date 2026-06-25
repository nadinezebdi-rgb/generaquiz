"""Test du prompt 'Quiz d'Antan' contre l'API Mistral."""
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from mistralai import Mistral

API_KEY = os.environ.get("MISTRAL_API_KEY")
MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")

SYSTEM_PROMPT = """Tu es un assistant expert dans la création de quiz culturels français de qualité.
Tu génères des questions à choix multiples (QCM) précises, vérifiables et culturellement riches,
adaptées à un public francophone, autour de la culture populaire d'antan (chansons, films,
publicités, objets et événements des années 1950 à 2000).

Règles strictes :
- 1 seule bonne réponse par question.
- 4 propositions plausibles (pas de pièges absurdes).
- Pas d'ambiguïté ni de question dont la réponse change avec le temps.
- Vocabulaire clair, ton bienveillant.
- Toujours renvoyer du JSON valide, sans texte autour."""

USER_PROMPT_TEMPLATE = """Génère 5 questions de quiz sur le thème "Chansons françaises des années 60-70".

Format de sortie attendu (JSON strict, sans markdown, sans commentaire) :
{
  "questions": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "B",
      "explication": "Courte phrase de contexte (1 ligne max)."
    }
  ]
}"""

def main():
    if not API_KEY:
        print("ERREUR: MISTRAL_API_KEY non défini dans l'environnement")
        sys.exit(1)
    print(f"Clé détectée (préfixe): {API_KEY[:6]}... longueur={len(API_KEY)}")
    print(f"Modèle: {MODEL}")
    print("=" * 60)

    client = Mistral(api_key=API_KEY)
    try:
        resp = client.chat.complete(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        print(f"ERREUR API: {type(e).__name__}: {e}")
        sys.exit(2)

    content = resp.choices[0].message.content
    print("Réponse brute Mistral:")
    print(content)
    print("=" * 60)
    try:
        parsed = json.loads(content)
        print("JSON parsé avec succès. Nombre de questions:",
              len(parsed.get("questions", [])))
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"JSON invalide: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
