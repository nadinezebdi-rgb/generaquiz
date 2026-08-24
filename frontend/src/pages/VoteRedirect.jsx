import { useEffect } from "react";
import { Sparkles } from "lucide-react";

/**
 * VoteRedirect — redirection publique vers la page de vote Emergent.
 *
 * SEULE LIGNE À CHANGER si le lien Emergent évolue : constante VOTE_URL ci-dessous.
 */
export const VOTE_URL =
  "https://app.emergent.sh/showcase/building-france/f122b885-05a4-4295-abe9-1a97fb455652";

export default function VoteRedirect() {
  useEffect(() => {
    // `replace` (et non `href = …`) pour que le bouton retour du navigateur
    // ne renvoie pas l'utilisateur en boucle sur /voter.
    window.location.replace(VOTE_URL);
  }, []);

  // Écran de repli affiché le court instant avant que le navigateur bascule.
  // Aucune indexation : cette route est une simple redirection.
  return (
    <div className="min-h-screen paper-bg flex items-center justify-center px-4">
      <meta name="robots" content="noindex" />
      <div className="max-w-md text-center">
        <span className="inline-flex w-14 h-14 rounded-full bg-terracotta shadow-warm items-center justify-center mb-6">
          <Sparkles className="w-7 h-7 text-white" strokeWidth={2.5} />
        </span>
        <h1 className="font-display text-3xl font-extrabold text-navy mb-3">
          Redirection vers la page de vote…
        </h1>
        <p className="text-navy/70 mb-6">
          Merci de soutenir GénéraQuiz sur la vitrine Emergent&nbsp;! Vous êtes redirigé
          automatiquement.
        </p>
        <a
          href={VOTE_URL}
          data-testid="vote-redirect-fallback"
          className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm"
        >
          Cliquez ici si rien ne se passe
        </a>
      </div>
    </div>
  );
}
