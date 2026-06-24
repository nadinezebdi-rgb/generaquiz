"""Client Supabase partagé pour le backend FastAPI de Quiz d'Antan.

Le backend utilise la clé ``service_role`` afin de pouvoir écrire les scores,
les sessions et les badges côté serveur, y compris lorsque les politiques RLS
protègent les tables pour les clients publics.
"""

from __future__ import annotations

import os
from threading import Lock

from supabase import Client, create_client


_supabase_client: Client | None = None
_supabase_lock = Lock()


def get_supabase_client() -> Client:
    """Retourne un singleton Supabase initialisé paresseusement.

    Variables d'environnement requises :
    - ``SUPABASE_URL`` : URL du projet Supabase.
    - ``SUPABASE_SERVICE_ROLE_KEY`` : clé serveur service_role, jamais exposée
      au navigateur, utilisée pour contourner RLS depuis FastAPI.

    Raises:
        RuntimeError: si une variable d'environnement obligatoire est absente.
    """

    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    with _supabase_lock:
        if _supabase_client is not None:
            return _supabase_client

        supabase_url = os.getenv("SUPABASE_URL")
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        missing_variables: list[str] = []
        if not supabase_url:
            missing_variables.append("SUPABASE_URL")
        if not service_role_key:
            missing_variables.append("SUPABASE_SERVICE_ROLE_KEY")

        if missing_variables:
            missing = ", ".join(missing_variables)
            raise RuntimeError(f"Configuration Supabase incomplète : {missing} manquante(s).")

        # create_client retourne un client synchrone supabase-py v2. Les services
        # FastAPI l'exécutent dans un thread via asyncio.to_thread pour éviter de
        # bloquer la boucle événementielle.
        _supabase_client = create_client(supabase_url, service_role_key)
        return _supabase_client
