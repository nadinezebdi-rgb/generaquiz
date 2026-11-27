import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { PLANS, PROMO_END, fmt, isChristmasPromo } from "@/config/pricing";
import { PromoHeader, CheckoutRecap } from "@/components/pricing/Offer";
import { PlanCard } from "@/pages/Pricing";

/**
 * OffreNoel — super promo de Noël sur l'abonnement annuel (Solo 49 €, Famille 79 €
 * pour 12 mois, puis tarif normal). Valable jusqu'au 31 décembre 2026 : la même
 * date est appliquée par le serveur (backend/subscription.py).
 */

const PAID_PLANS = PLANS.filter((p) => p.mensuel > 0);
const endLabel = PROMO_END.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/Paris" });

export default function OffreNoel() {
  const promo = isChristmasPromo();
  const [recapPkg, setRecapPkg] = useState(null);
  const closeRecap = useCallback(() => setRecapPkg(null), []);

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center max-w-3xl mx-auto mb-10">
          <span className="inline-block bg-bordeaux text-cream font-bold px-4 py-1.5 rounded-full text-sm mb-4">
            🎄 Offre de Noël
          </span>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold mb-3" data-testid="noel-h1">
            La super promo de <span className="text-terracotta italic">Noël</span>
          </h1>
          {promo ? <PromoHeader promo testPrefix="noel" /> : (
            <p className="mt-3 font-bold text-bordeaux text-lg" role="status" data-testid="noel-ended">
              L&apos;offre de Noël est terminée depuis le {endLabel}.
            </p>
          )}
        </div>

        {promo && (
          <>
            <figure className="max-w-4xl mx-auto mb-10" data-testid="noel-gift-card">
              <div className="rounded-[28px] overflow-hidden border-4 border-mustard/70 shadow-warm">
                <img src="/images/offre-noel-carte-cadeau.webp" width="1536" height="1024" fetchPriority="high"
                  alt="Carte cadeau Joyeux Noël GénéraQuiz : possibilité de jouer au quiz pendant 1 an, formule Solo (1 accès personnel complet) ou Famille (1 bénéficiaire + 2 proches), valable 1 an sur generaquiz.fr"
                  className="w-full h-auto block" />
              </div>
              <figcaption className="text-sm text-navy/70 text-center mt-3">
                La carte cadeau de Noël, à imprimer et à offrir.{" "}
                <Link to="/offrir" className="font-bold text-terracotta underline" data-testid="noel-offrir-link">Offrir une carte cadeau</Link>
              </figcaption>
            </figure>

            <div className="grid md:grid-cols-2 gap-5 mb-6 max-w-3xl mx-auto">
              {PAID_PLANS.map((plan) => (
                <PlanCard key={plan.id} plan={plan} period="yearly" promo onChoose={setRecapPkg} />
              ))}
            </div>
            <p className="text-base text-navy font-bold text-center mb-2" data-testid="noel-annual-note">
              Promo annuelle : les 12 mois commencent à la première connexion. Idéal à offrir pour Noël 🎁
            </p>
            <p className="text-sm text-navy text-center mb-10" data-testid="noel-legal">
              Prix TTC. Offre valable pour toute souscription jusqu&apos;au {endLabel}. Abonnement annuel débité en une fois,
              puis renouvelé automatiquement au tarif normal ({PAID_PLANS.map((p) => `${fmt(p.annuel, { integer: true })}/an pour ${p.nom}`).join(", ")}),
              rappel par e-mail 30 jours avant. Résiliable à tout moment en un clic.
            </p>
          </>
        )}

        <div className="text-center">
          <Link to="/app/pricing" data-testid="noel-see-pricing"
            className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-6 py-3 rounded-full hover:bg-navy-dark transition">
            {promo ? "Voir les tarifs normaux, au mois ou à l'année" : "Voir nos tarifs"} <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <CheckoutRecap packageId={recapPkg} onClose={closeRecap} />
      </main>

      <Footer />
    </div>
  );
}
