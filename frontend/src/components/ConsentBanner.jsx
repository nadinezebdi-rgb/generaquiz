import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const KEY = "gq_consent";

export const openConsentSettings = () => window.dispatchEvent(new Event("gq-consent-open"));

/** Mesure d'audience uniquement après accord explicite (CNIL) ; « Refuser » aussi simple qu'« Accepter ». */
export function ConsentBanner() {
  const [open, setOpen] = useState(() => {
    try { return !localStorage.getItem(KEY); } catch { return false; }
  });

  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener("gq-consent-open", show);
    return () => window.removeEventListener("gq-consent-open", show);
  }, []);

  // Laisse la place au bandeau : le bas de page (bouton d'inscription…) reste accessible au défilement.
  useEffect(() => {
    document.body.style.paddingBottom = open ? "220px" : "";
    return () => { document.body.style.paddingBottom = ""; };
  }, [open]);

  const choose = (yes) => {
    try { localStorage.setItem(KEY, yes ? "yes" : "no"); } catch { /* navigation privée */ }
    if (yes) window.gqStartAnalytics?.();
    else if (window.__gqAnalytics) { window.posthog?.opt_out_capturing?.(); window.posthog?.reset?.(); }
    setOpen(false);
  };

  if (!open) return null;
  const btn = "flex-1 sm:flex-none font-bold text-base px-6 py-3 rounded-full transition-colors min-h-[48px]";
  return (
    <div role="dialog" aria-live="polite" aria-label="Cookies et mesure d'audience" data-testid="consent-banner"
      className="fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-3xl bg-white border-2 border-navy rounded-3xl shadow-soft p-5 sm:p-6">
      <p className="text-navy text-base leading-relaxed mb-4">
        Nous aimerions mesurer, de façon anonyme, comment le site est utilisé pour l&apos;améliorer. Rien n&apos;est
        enregistré sans votre accord, et vos réponses et souvenirs ne sont jamais captés.{" "}
        <Link to="/confidentialite" className="underline font-semibold">En savoir plus</Link>
      </p>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => choose(false)} data-testid="consent-refuse"
          className={`${btn} border-2 border-navy text-navy hover:bg-cream`}>Refuser</button>
        <button type="button" onClick={() => choose(true)} data-testid="consent-accept"
          className={`${btn} bg-navy text-cream hover:bg-navy-dark`}>Accepter</button>
      </div>
    </div>
  );
}
