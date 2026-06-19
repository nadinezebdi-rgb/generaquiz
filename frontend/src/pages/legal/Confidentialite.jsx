import LegalLayout from "@/components/LegalLayout";

export default function Confidentialite() {
  return (
    <LegalLayout title="Politique de Confidentialité — RGPD" lastUpdated="15 février 2026" testId="confidentialite-page">
      <section>
        <p>
          GénéraQuiz respecte votre vie privée et applique le Règlement Général sur la Protection des
          Données (RGPD, UE 2016/679). Cette page explique <strong>quelles données nous collectons,
          pourquoi, et comment vous pouvez les contrôler</strong>.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">1. Responsable du traitement</h2>
        <p>
          GénéraQuiz — créatrice indépendante, joignable à
          <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">2. Données collectées</h2>
        <p>
          Nous collectons uniquement le strict nécessaire au bon fonctionnement du service :
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Données de compte</strong> : email, prénom (facultatif), mot de passe haché (jamais en clair).</li>
          <li><strong>Données de jeu</strong> : scores, séries (streaks), participations aux défis, classements, crédits virtuels.</li>
          <li><strong>Données techniques</strong> : adresse IP (pour la protection anti-flood), type d&apos;appareil, version de l&apos;app, identifiants de session (cookies JWT).</li>
          <li><strong>Paiement</strong> : aucune donnée bancaire n&apos;est stockée par GénéraQuiz. Les paiements sont gérés par Stripe, l&apos;App Store ou Google Play, selon la plateforme.</li>
          <li><strong>Apple Sign-In / Google Sign-In</strong> (mobile uniquement) : email et identifiant unique du fournisseur, transmis avec votre accord explicite lors de la connexion.</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">3. Finalités</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Permettre la connexion et l&apos;identification (article 6.1.b — exécution du contrat)</li>
          <li>Sauvegarder votre progression, vos scores et vos crédits (6.1.b)</li>
          <li>Envoyer le rappel matinal Quiz du Jour si vous y avez consenti (6.1.a — consentement, révocable depuis votre compte)</li>
          <li>Améliorer l&apos;application via des statistiques agrégées et anonymisées (6.1.f — intérêt légitime)</li>
          <li>Lutter contre la fraude et l&apos;abus (6.1.f)</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">4. Durée de conservation</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Compte actif : tant que vous utilisez le service.</li>
          <li>Compte inactif (aucune connexion depuis 3 ans) : suppression automatique après notification email.</li>
          <li>Données de paiement (Stripe) : conservées par Stripe selon ses propres CGU, durée recommandée 10 ans pour la comptabilité.</li>
          <li>Logs techniques : 12 mois maximum.</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">5. Vos droits</h2>
        <p>Vous disposez à tout moment des droits suivants :</p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Droit d&apos;accès</strong> : consulter toutes les données que nous détenons sur vous.</li>
          <li><strong>Droit de rectification</strong> : modifier vos données depuis votre <strong>compte utilisateur</strong>.</li>
          <li><strong>Droit à l&apos;effacement</strong> : <em>« droit à l&apos;oubli »</em>, en cliquant sur <strong>Supprimer mon compte</strong> dans <strong>Mon compte → Zone de danger</strong>.</li>
          <li><strong>Droit à la portabilité</strong> : export de vos données sur demande à
            <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>.</li>
          <li><strong>Droit d&apos;opposition</strong> au traitement à des fins marketing : désactivable depuis votre compte.</li>
          <li><strong>Droit de réclamation</strong> auprès de la CNIL :
            <a href="https://www.cnil.fr/fr/plaintes" className="text-terracotta underline ml-1" target="_blank" rel="noreferrer">cnil.fr/plaintes</a>.</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">6. Sous-traitants</h2>
        <p>Nous utilisons les services suivants, qui peuvent traiter vos données pour notre compte :</p>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Stripe</strong> (Irlande) — paiements web</li>
          <li><strong>Apple / Google</strong> — paiements et authentification mobile</li>
          <li><strong>Resend</strong> (États-Unis, transfert encadré par les Clauses Contractuelles Types) — envoi des emails transactionnels (reset password, Quiz du Jour)</li>
          <li><strong>Hébergement</strong> — serveurs européens (région EU-West)</li>
          <li><strong>RevenueCat</strong> (États-Unis, mobile) — réconciliation des achats in-app</li>
          <li><strong>Google AdMob</strong> (mobile) — publicités récompensées, configurées pour minimiser le tracking</li>
        </ul>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">7. Cookies & traceurs</h2>
        <p>
          GénéraQuiz utilise uniquement des cookies <strong>strictement nécessaires</strong> au
          fonctionnement (session JWT, préférences). Nous n&apos;utilisons aucun cookie publicitaire ni
          traceur tiers sur le site web. L&apos;application mobile n&apos;utilise pas de cookies au sens
          classique, mais conserve un identifiant local d&apos;appareil pour l&apos;authentification.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">8. Sécurité</h2>
        <p>
          Vos mots de passe sont hachés avec l&apos;algorithme bcrypt. Toutes les communications sont
          chiffrées en HTTPS / TLS 1.3. Les bases de données sont hébergées dans l&apos;Union européenne
          avec des accès restreints. En cas de violation de données, nous nous engageons à notifier la CNIL
          dans les 72 heures et à informer les utilisateurs concernés sans délai.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">9. Mineurs</h2>
        <p>
          GénéraQuiz est ouvert aux familles, y compris aux mineurs jouant en présence d&apos;un parent ou
          d&apos;un tuteur. Les comptes sont réservés aux personnes de 15 ans ou plus (RGPD France). Pour
          les enfants plus jeunes, l&apos;utilisation se fait sous la responsabilité du compte parental.
        </p>
      </section>

      <section>
        <h2 className="font-display text-2xl font-bold text-navy mt-6 mb-3">10. Contact</h2>
        <p>
          Pour toute question relative à vos données personnelles :
          <a href="mailto:contact@generaquiz.fr" className="text-terracotta underline ml-1">contact@generaquiz.fr</a>.
          Nous nous engageons à répondre sous 30 jours.
        </p>
      </section>
    </LegalLayout>
  );
}
