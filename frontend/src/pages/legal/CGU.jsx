import LegalLayout from "@/components/LegalLayout";

export default function CGU() {
  return (
    <LegalLayout title="Conditions Générales d'Utilisation" lastUpdated="15 février 2026" testId="cgu-page">
      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">1. Objet</h2>
        <p>
          Les présentes Conditions Générales d&apos;Utilisation (CGU) régissent l&apos;accès et l&apos;utilisation
          du service <strong>GénéraQuiz</strong>, plateforme de quiz intergénérationnelle accessible
          sur <a href="https://generaquiz.fr" className="text-terracotta underline">generaquiz.fr</a> et via
          ses applications mobiles iOS et Android.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">2. Éditeur</h2>
        <p>
          GénéraQuiz est édité par sa créatrice indépendante. Pour toute question, contactez :
          <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">3. Acceptation</h2>
        <p>
          L&apos;utilisation du service implique l&apos;acceptation pleine et entière des présentes CGU. Si
          vous n&apos;acceptez pas ces conditions, vous devez vous abstenir d&apos;utiliser le service.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">4. Compte utilisateur</h2>
        <p>
          Pour accéder à certaines fonctionnalités (sauvegarde du score, classement, Défi Famille), vous devez
          créer un compte. Vous vous engagez à fournir des informations exactes et à conserver la
          confidentialité de votre mot de passe. Vous pouvez supprimer votre compte à tout moment depuis la
          page <strong>Mon compte</strong> ; cette suppression est irréversible.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">5. Contenu</h2>
        <p>
          GénéraQuiz s&apos;efforce de proposer un contenu exact et factuellement vérifié. Le contenu des
          quiz a une vocation culturelle et de divertissement. Aucune valeur scientifique ou diagnostique
          n&apos;est garantie.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">6. Économie virtuelle (crédits)</h2>
        <p>
          Les <strong>crédits virtuels</strong> obtenus dans l&apos;application (bonus de bienvenue, défis
          relevés, publicités récompensées, achats in-app) n&apos;ont aucune valeur monétaire réelle, ne
          peuvent être convertis en argent et ne sont ni remboursables ni transférables entre comptes. Ils
          sont utilisables uniquement pour des fonctionnalités à l&apos;intérieur de GénéraQuiz.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">7. Abonnement Premium</h2>
        <p>
          Les abonnements payants (Premium Mensuel, Premium Annuel) sont facturés via Stripe (web),
          l&apos;App Store d&apos;Apple ou Google Play selon la plateforme utilisée. Les conditions de
          renouvellement automatique et de désabonnement sont précisées au moment de l&apos;achat. La
          résiliation prend effet à la fin de la période en cours.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">8. Comportement attendu</h2>
        <p>
          L&apos;utilisateur s&apos;engage à utiliser GénéraQuiz dans le respect d&apos;autrui : pas de
          contenu injurieux dans le pseudonyme, pas d&apos;automatisation des scores (bot), pas de tentative
          d&apos;intrusion dans les comptes d&apos;autres utilisateurs. Tout comportement abusif peut
          entraîner la suspension du compte sans préavis.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">9. Propriété intellectuelle</h2>
        <p>
          Les textes, images, logos, mascottes et code source de GénéraQuiz sont protégés par le droit
          d&apos;auteur. Toute reproduction sans autorisation écrite est interdite. Les questions des quiz
          peuvent être partagées dans un cadre familial mais ne peuvent être réutilisées dans un autre
          service commercial.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">10. Modification</h2>
        <p>
          Les présentes CGU peuvent être modifiées à tout moment. Les utilisateurs seront informés des
          changements significatifs par email. L&apos;utilisation continue du service après modification
          vaut acceptation.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">11. Droit applicable</h2>
        <p>
          Les présentes CGU sont soumises au droit français. En cas de litige, et après tentative de
          résolution amiable, les tribunaux français seront compétents.
        </p>
      </section>
    </LegalLayout>
  );
}
