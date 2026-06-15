import LegalLayout from "@/components/LegalLayout";

export default function CGV() {
  return (
    <LegalLayout title="Conditions Générales de Vente" lastUpdated="15 février 2026" testId="cgv-page">
      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">1. Identification du vendeur</h2>
        <p>
          GénéraQuiz est édité par sa créatrice indépendante, joignable à
          <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">2. Produits et services proposés</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Premium Mensuel</strong> — 9,99 € / mois, accès illimité aux 30 questions par catégorie, défis famille illimités, lecture vocale, statistiques détaillées, sans publicité.</li>
          <li><strong>Premium Annuel</strong> — 89,99 € / an, soit 7,49 € / mois (économie de 17 %).</li>
          <li><strong>Packs de crédits virtuels</strong> (uniquement sur l&apos;app mobile) — produits consommables permettant d&apos;acquérir des crédits utilisables pour les indices, le sauvetage de série, etc. Les crédits n&apos;ont aucune valeur monétaire réelle (voir CGU article 6).</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">3. Prix</h2>
        <p>
          Les prix sont indiqués en euros toutes taxes comprises (TVA française applicable). GénéraQuiz se
          réserve le droit de modifier ses tarifs à tout moment, mais les abonnements en cours restent
          facturés au tarif en vigueur lors de la souscription.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">4. Modalités de paiement</h2>
        <p>
          Les paiements sont sécurisés. Selon la plateforme utilisée :
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Web (generaquiz.fr)</strong> : via Stripe (carte bancaire, Apple Pay, Google Pay)</li>
          <li><strong>iOS</strong> : via l&apos;App Store d&apos;Apple (Apple Pay, Apple ID)</li>
          <li><strong>Android</strong> : via Google Play Billing (Google Pay)</li>
        </ul>
        <p>
          GénéraQuiz ne conserve aucune donnée bancaire ; ces informations sont gérées exclusivement par les
          plateformes mentionnées ci-dessus.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">5. Renouvellement automatique</h2>
        <p>
          Les abonnements Premium se renouvellent automatiquement à la fin de chaque période, sauf
          désactivation au plus tard 24 heures avant l&apos;échéance. Le renouvellement est effectué par la
          plateforme de paiement utilisée lors de la souscription. Vous pouvez désactiver le renouvellement
          automatique à tout moment depuis :
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Web : votre <strong>Tableau de bord Stripe</strong> (lien envoyé par email)</li>
          <li>iOS : <strong>Réglages → Apple ID → Abonnements</strong></li>
          <li>Android : <strong>Google Play → Abonnements</strong></li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">6. Droit de rétractation</h2>
        <p>
          Conformément à l&apos;article L221-28 du Code de la consommation, le droit de rétractation ne peut
          être exercé pour les contenus numériques exécutés immédiatement après confirmation expresse de
          l&apos;utilisateur — ce qui est le cas dès l&apos;activation de l&apos;abonnement Premium ou
          l&apos;ajout de crédits. En cliquant sur « Acheter », vous reconnaissez expressément renoncer à
          votre droit de rétractation.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">7. Remboursement</h2>
        <p>
          Les demandes de remboursement doivent être adressées :
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Web</strong> : à <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline">contact@generaquiz.fr</a></li>
          <li><strong>iOS</strong> : via la procédure Apple (<a href="https://reportaproblem.apple.com" className="text-terracotta underline" target="_blank" rel="noreferrer">reportaproblem.apple.com</a>)</li>
          <li><strong>Android</strong> : via la procédure Google (<a href="https://support.google.com/googleplay" className="text-terracotta underline" target="_blank" rel="noreferrer">support.google.com/googleplay</a>)</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">8. Service client</h2>
        <p>
          Pour toute question, le service client répond par email à
          <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>
          sous 48 heures ouvrées.
        </p>
      </section>
    </LegalLayout>
  );
}
