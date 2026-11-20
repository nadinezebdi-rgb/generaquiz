/**
 * Contenu éditorial de la rubrique « Bien vieillir ».
 *
 * Source de vérité unique : les pages React ET le script de prérendu
 * (`frontend/scripts/prerender-seo.js`) lisent d'ici (via bienVieillirSeo.json
 * pour la partie <head>). Ne pas dupliquer un titre ou une description ailleurs.
 *
 * RÈGLE ÉDITORIALE — chaque chiffre cité est daté et sourcé, avec un lien vers
 * la source primaire. Les montants et les dispositifs français sont révisés
 * chaque année : avant toute republication, revérifier les blocs `sources`.
 * Dernière vérification des données : septembre 2026.
 *
 * Cette rubrique est informative. Elle ne délivre aucun conseil médical et
 * renvoie systématiquement vers un professionnel de santé ou un point
 * d'information local pour les situations individuelles.
 */

export const HUB = {
  emoji: "🌿",
  kicker: "Bien vieillir",
  title: "Vieillir en gardant la tête, le lien et l'autonomie",
  intro:
    "Bien vieillir n'est pas une affaire de chance. Trois leviers font l'essentiel du travail : entretenir son cerveau, garder des liens réels, et se faire aider avant l'épuisement. Cette rubrique rassemble ce qui est documenté, ce qui existe comme aide en France, et de quoi s'y tenir semaine après semaine.",
  disclaimer:
    "Ces pages sont informatives et ne remplacent pas un avis médical. Pour une situation personnelle, parlez-en à votre médecin traitant ou à un point d'information local dédié aux personnes âgées.",
};

export const FICHES = [
  {
    slug: "stimulation-cognitive",
    emoji: "🧠",
    label: "Stimulation cognitive",
    teaser:
      "Ce qui entretient réellement le cerveau après 60 ans, à quelle fréquence, et ce que les études ne disent pas.",
    kicker: "Stimulation cognitive",
    title: "Stimulation cognitive après 60 ans : ce qui marche vraiment",
    intro:
      "Le marché des « jeux pour le cerveau » promet beaucoup. La recherche, elle, est plus nuancée mais pas silencieuse : certaines activités sont associées à un vieillissement cognitif plus favorable, à condition d'être régulières et suffisamment variées. Voici ce qui est établi, et ce qui ne l'est pas.",
    keyFigures: [
      { value: "38 %", label: "de risque de démence en moins chez les pratiquants réguliers d'activités cognitives", source: "Verghese et al., NEJM, 2003" },
      { value: "≥ 3×/sem.", label: "le seuil de fréquence à partir duquel l'effet devient mesurable", source: "Verghese et al., NEJM, 2003" },
      { value: "150 min", label: "d'activité physique modérée par semaine recommandées après 65 ans", source: "OMS, reprise ameli.fr, 2026" },
    ],
    sections: [
      {
        title: "Ce que montrent les études",
        paragraphs: [
          "L'étude de référence reste celle de Verghese et ses collègues, publiée dans le New England Journal of Medicine en 2003 : 469 personnes âgées suivies pendant 21 ans. Les participants pratiquant régulièrement des activités cognitives — lecture, jeux de société, mots croisés, musique — présentaient un risque de démence réduit de 38 %.",
          "Dix ans plus tard, Wilson et ses collègues (Neurology, 2013) ont ajouté une pièce importante : chez 294 sujets suivis six ans puis autopsiés, une activité mentale fréquente ralentissait le déclin cognitif indépendamment des lésions cérébrales visibles. Autrement dit, l'activité ne supprime pas les lésions — elle semble aider le cerveau à mieux fonctionner malgré elles.",
        ],
      },
      {
        title: "Trois conditions, souvent oubliées",
        bullets: [
          "La régularité prime sur l'intensité. Trois séances courtes par semaine valent mieux qu'une longue session mensuelle.",
          "La variété compte. Refaire toujours le même exercice entraîne surtout à cet exercice précis ; la transposition aux gestes du quotidien reste faible.",
          "L'effort doit être réel mais atteignable. Trop facile, l'activité n'apporte rien ; trop difficile, elle décourage et l'on arrête.",
        ],
      },
      {
        title: "Le corps fait partie du cerveau",
        paragraphs: [
          "L'activité physique est l'un des leviers les mieux documentés du vieillissement cognitif. Les recommandations de l'OMS, reprises par l'Assurance Maladie, situent la cible après 65 ans à au moins 150 minutes d'activité d'intensité modérée par semaine — typiquement 30 minutes de marche cinq jours sur sept — complétées par du renforcement musculaire et des exercices d'équilibre au moins deux fois par semaine.",
          "L'équilibre mérite une mention particulière : c'est le principal levier de prévention des chutes, et une chute est souvent le point de bascule vers la perte d'autonomie.",
        ],
      },
      {
        title: "Ce qu'il ne faut pas attendre",
        paragraphs: [
          "Aucune activité cognitive ne prévient la maladie d'Alzheimer, et aucun jeu ne « guérit » un trouble installé. Les résultats évoqués ici sont des associations statistiques observées sur des populations, pas des garanties individuelles. Un programme de stimulation ne remplace jamais un bilan médical lorsque des difficultés apparaissent.",
        ],
      },
    ],
    faq: [
      {
        q: "Combien de temps par jour faut-il consacrer à la stimulation cognitive ?",
        a: "Les études qui mesurent un effet portent sur la fréquence plus que sur la durée : à partir de trois séances par semaine, même courtes (quinze à vingt minutes), l'effet devient mesurable. La régularité sur plusieurs années compte davantage que la durée de chaque séance.",
      },
      {
        q: "Les mots croisés suffisent-ils ?",
        a: "Ils font partie des activités associées à un meilleur vieillissement cognitif, mais la variété améliore les résultats. Alterner lecture, jeux de mémoire, conversation et activités manuelles sollicite des fonctions différentes.",
      },
      {
        q: "La stimulation cognitive peut-elle prévenir la maladie d'Alzheimer ?",
        a: "Non. Les travaux disponibles montrent une association avec un risque réduit et un déclin ralenti à l'échelle d'une population, pas une prévention individuelle. En cas de difficultés de mémoire inhabituelles, consultez votre médecin traitant.",
      },
    ],
    sources: [
      { label: "Verghese J. et al., « Leisure activities and the risk of dementia in the elderly », New England Journal of Medicine, 2003", url: "https://www.nejm.org/doi/full/10.1056/NEJMoa022252" },
      { label: "Wilson R.S. et al., « Life-span cognitive activity, neuropathologic burden, and cognitive aging », Neurology, 2013", url: "https://n.neurology.org/content/81/4/314" },
      { label: "Assurance Maladie — Adultes et seniors : à chaque âge son activité physique (mise à jour 27/08/2026)", url: "https://www.ameli.fr/assure/sante/themes/activite-physique-sante/age-activite-physique" },
    ],
  },,
  {
    slug: "entretenir-sa-memoire",
    emoji: "💭",
    label: "Entretenir sa mémoire",
    teaser:
      "Distinguer l'oubli banal du signe d'alerte, et les méthodes qui tiennent dans la durée.",
    kicker: "Mémoire",
    title: "Entretenir sa mémoire après 60 ans : méthodes et repères",
    intro:
      "Oublier un prénom, chercher ses clés, perdre le fil d'une phrase : ces incidents augmentent avec l'âge sans rien annoncer de grave. Le vrai sujet est ailleurs — savoir ce qui entretient la mémoire au quotidien, et repérer les signaux qui justifient d'en parler à un médecin.",
    keyFigures: [
      { value: "Normal", label: "oublier où l'on a posé un objet, puis le retrouver en refaisant le trajet mentalement", source: "Repère d'usage clinique" },
      { value: "À signaler", label: "oublier une conversation entière, ou répéter la même question dans la journée", source: "Repère d'usage clinique" },
      { value: "≥ 3×/sem.", label: "la fréquence d'activité à partir de laquelle un effet est mesuré", source: "Verghese et al., NEJM, 2003" },
    ],
    sections: [
      {
        title: "Un oubli banal, ou un signe d'alerte ?",
        paragraphs: [
          "La différence tient moins à l'oubli lui-même qu'à ce qui l'entoure. Chercher un prénom que l'on retrouve une heure plus tard relève du fonctionnement ordinaire du rappel. Ne plus reconnaître le contexte — oublier avoir eu la conversation, et pas seulement son contenu — est d'une autre nature.",
        ],
        bullets: [
          "Ce qui reste banal : chercher un mot, égarer un objet, avoir besoin d'une liste, être plus lent qu'avant.",
          "Ce qui mérite un avis médical : répéter la même question dans la même journée, se perdre sur un trajet connu, ne plus savoir utiliser un appareil familier, un changement d'humeur ou de comportement remarqué par l'entourage.",
          "Ce qui doit faire consulter sans attendre : une aggravation rapide sur quelques semaines.",
        ],
      },
      {
        title: "La répétition espacée, la méthode la plus robuste",
        paragraphs: [
          "Revoir une information à intervalles croissants — le lendemain, trois jours plus tard, une semaine, un mois — ancre durablement mieux que de la relire cinq fois d'affilée. Ce principe est l'un des plus solides de la psychologie de la mémoire, et il s'applique aussi bien à un prénom qu'à une date de rendez-vous.",
          "Le corollaire pratique : l'effort de rappel compte plus que la relecture. Se demander « comment s'appelait-il déjà ? » avant de vérifier fait davantage pour la mémoire que de relire la réponse.",
        ],
      },
      {
        title: "Ce qui abîme la mémoire sans être une maladie",
        bullets: [
          "Le manque de sommeil : c'est pendant la nuit que les souvenirs de la journée se consolident.",
          "L'isolement : moins de conversations, c'est moins de sollicitations de la mémoire de travail et du langage.",
          "L'anxiété et la dépression, qui altèrent l'attention — et sans attention, il n'y a pas d'encodage.",
          "Certains médicaments et une audition non corrigée : deux causes fréquentes, réversibles, et trop rarement explorées.",
        ],
      },
      {
        title: "Des habitudes qui tiennent",
        paragraphs: [
          "Une mémoire s'entretient par des gestes ordinaires et répétés plutôt que par des programmes ambitieux abandonnés au bout de trois semaines : raconter sa journée à quelqu'un, lire puis résumer à voix haute, apprendre quelques vers, jouer à plusieurs. Les activités partagées cumulent deux effets — l'exercice cognitif et le lien social.",
        ],
      },
    ],
    faq: [
      {
        q: "Les trous de mémoire après 60 ans sont-ils normaux ?",
        a: "Un ralentissement du rappel est un phénomène ordinaire du vieillissement. Ce qui justifie un avis médical, c'est l'oubli d'événements entiers, la répétition des mêmes questions dans une journée, la désorientation dans un lieu connu, ou une aggravation rapide.",
      },
      {
        q: "Qu'est-ce que la répétition espacée ?",
        a: "C'est le fait de revoir une information à intervalles de plus en plus longs plutôt que de la répéter plusieurs fois de suite. À temps de travail égal, l'ancrage à long terme est nettement meilleur.",
      },
      {
        q: "À qui s'adresser en cas de doute sur sa mémoire ?",
        a: "Au médecin traitant en premier lieu : il écarte les causes réversibles (médicaments, sommeil, audition, thyroïde, dépression) avant d'orienter si besoin vers une consultation mémoire. Un point d'information local dédié aux personnes âgées peut aussi vous orienter.",
      },
    ],
    sources: [
      { label: "Verghese J. et al., New England Journal of Medicine, 2003", url: "https://www.nejm.org/doi/full/10.1056/NEJMoa022252" },
      { label: "Portail national — Points d'information locaux dédiés aux personnes âgées (mise à jour 30/01/2026)", url: "https://www.pour-les-personnes-agees.gouv.fr/preserver-son-autonomie/a-qui-s-adresser/les-points-d-information-locaux-dedies-aux-personnes-agees" },
    ],
  },
  {
    slug: "rompre-isolement",
    emoji: "🤝",
    label: "Rompre l'isolement",
    teaser:
      "750 000 personnes âgées en « mort sociale » en France. Repérer, et savoir vers quoi orienter.",
    kicker: "Lien social",
    title: "Isolement des personnes âgées : comprendre et agir",
    intro:
      "L'isolement des aînés n'est pas un problème de confort : il pèse sur la santé physique et cognitive autant que des facteurs de risque reconnus. En France, il s'aggrave rapidement. Voici les chiffres mesurés, les signes qui doivent alerter, et les dispositifs vers lesquels orienter.",
    keyFigures: [
      { value: "750 000", label: "personnes âgées en situation de « mort sociale » — sans contact avec aucun cercle de sociabilité", source: "3e Baromètre Petits Frères des Pauvres, 2025" },
      { value: "+150 %", label: "d'isolement extrême en moins de dix ans (530 000 en 2021 → 750 000 en 2025)", source: "3e Baromètre Petits Frères des Pauvres, 2025" },
      { value: "5,7 M", label: "de personnes de 60 ans et plus n'ont personne à qui se confier", source: "3e Baromètre Petits Frères des Pauvres, 2025" },
    ],
    sections: [
      {
        title: "Ce que mesure le baromètre 2025",
        paragraphs: [
          "Le 3e Baromètre de l'isolement des personnes âgées, publié le 29 septembre 2025 par les Petits Frères des Pauvres avec CSA Research, porte sur les 60 ans et plus. Il définit la « mort sociale » comme l'absence de contact, ou des contacts quasi inexistants, avec les quatre cercles de sociabilité : famille, amis, voisinage, réseaux associatifs.",
          "Au-delà des 750 000 personnes concernées, l'étude compte 2 millions de personnes coupées à la fois du cercle familial et amical, 2,5 millions qui se sentent seules tous les jours ou presque, et 5 millions en situation d'exclusion numérique. La projection des auteurs atteint 1 million de personnes en mort sociale en 2030.",
        ],
      },
      {
        title: "L'isolement agit sur la cognition",
        paragraphs: [
          "Les travaux sur le lien social convergent avec ceux sur la mémoire. Dans la Bronx Aging Study (Hall et al., Neurology, 2009), les activités partagées entre générations retardaient en moyenne de 1,29 an l'apparition des symptômes cognitifs par rapport aux personnes isolées. Menec (Journals of Gerontology, 2003), sur près de 6 900 Canadiens de 65 ans et plus, associait l'engagement social régulier à une réduction de moitié du risque de dépression tardive.",
        ],
      },
      {
        title: "Les signes qui doivent alerter",
        bullets: [
          "Le refus répété des invitations, puis l'arrêt des sorties.",
          "Le téléphone qui ne sonne plus, ou auquel la personne ne répond plus.",
          "Le relâchement de l'entretien du logement ou de l'apparence.",
          "Les repas sautés, la perte de poids, l'inversion du rythme jour/nuit.",
          "Le renoncement aux soins et aux rendez-vous médicaux.",
        ],
      },
      {
        title: "Vers quoi orienter, concrètement",
        bullets: [
          "Solitud'écoute, la ligne d'écoute gratuite et anonyme des Petits Frères des Pauvres pour les plus de 50 ans : 0 800 47 47 88, tous les jours de 15 h à 20 h, week-ends et jours fériés inclus.",
          "MONALISA (Mobilisation nationale contre l'isolement des âgés) : un réseau d'équipes citoyennes bénévoles — 904 équipes et plus de 9 000 bénévoles en 2024 — dont l'animation est confiée à la CNSA depuis 2020.",
          "Les points d'information locaux dédiés aux personnes âgées, souvent appelés CLIC : accueil, information et orientation de proximité. Un annuaire officiel permet de trouver le sien par commune ou code postal.",
          "En cas de suspicion de maltraitance : le 3133, numéro national gratuit, 7 j/7 de 9 h à 20 h. Il a remplacé le 3977 le 1er mars 2026.",
        ],
      },
    ],
    faq: [
      {
        q: "Combien de personnes âgées sont isolées en France ?",
        a: "Selon le 3e Baromètre des Petits Frères des Pauvres (2025), 750 000 personnes de 60 ans et plus sont en situation de « mort sociale », c'est-à-dire sans contact avec aucun de leurs cercles de sociabilité. Deux millions sont coupées des cercles familial et amical.",
      },
      {
        q: "Existe-t-il une ligne d'écoute pour les personnes âgées seules ?",
        a: "Oui : Solitud'écoute, portée par les Petits Frères des Pauvres, au 0 800 47 47 88. L'appel est gratuit, anonyme et confidentiel, tous les jours de 15 h à 20 h, pour les personnes de plus de 50 ans.",
      },
      {
        q: "Quel numéro appeler en cas de maltraitance d'une personne âgée ?",
        a: "Le 3133, numéro national de lutte contre les maltraitances envers les adultes vulnérables, gratuit, 7 j/7 de 9 h à 20 h. Il remplace le 3977 depuis le 1er mars 2026 et s'accompagne d'un formulaire de signalement en ligne.",
      },
    ],
    sources: [
      { label: "Petits Frères des Pauvres — 3e Baromètre de l'isolement des personnes âgées, 29 septembre 2025", url: "https://www.petitsfreresdespauvres.fr/sinformer/actualites/barometre-2025-les-10-chiffres-cles-de-lisolement-des-aines/" },
      { label: "Petits Frères des Pauvres — Solitud'écoute", url: "https://www.petitsfreresdespauvres.fr/nos-actions/apporter-une-presence/ecoute-anonyme/" },
      { label: "MONALISA — site officiel", url: "https://www.monalisa-asso.fr/" },
      { label: "Portail national — annuaire des points d'information locaux", url: "https://www.pour-les-personnes-agees.gouv.fr/annuaire-points-dinformation" },
      { label: "Ministère des Solidarités — le 3133 et le formulaire de signalement (juin 2026)", url: "https://solidarites.gouv.fr/un-nouveau-dispositif-de-lutte-contre-les-maltraitances-le-numero-3133-et-le-formulaire-de-signalement-en-ligne" },
      { label: "Hall C.B. et al., Neurology, 2009", url: "https://n.neurology.org/content/73/5/356" },
      { label: "Menec V.H., Journals of Gerontology, 2003", url: "https://academic.oup.com/psychsocgerontology/article/58/2/S74/583612" },
    ],
  },
  {
    slug: "aidants-familiaux",
    emoji: "❤️",
    label: "Aidants familiaux",
    teaser:
      "Congé de proche aidant, AJPA, droit au répit : les droits réels, et comment tenir dans la durée.",
    kicker: "Aidants",
    title: "Aidant familial : droits, aides et répit en France",
    intro:
      "Accompagner un parent qui perd son autonomie se fait presque toujours sans l'avoir choisi, et souvent sans connaître ses droits. Trois dispositifs existent en France : un congé, une allocation, et une aide au répit. Voici ce qu'ils couvrent réellement en 2026, et ce qu'ils ne couvrent pas.",
    keyFigures: [
      { value: "5,3 M", label: "de proches aidants apportant une aide à la vie quotidienne (soins, tâches domestiques, mobilité)", source: "DREES, Études et Résultats n° 1377, données 2022, publié juin 2026" },
      { value: "66,64 €", label: "par jour — montant de l'AJPA au 1er janvier 2026", source: "Portail national pour les personnes âgées, 2026" },
      { value: "583,52 €", label: "par an — plafond du droit au répit dans le cadre de l'APA en 2026", source: "Portail national pour les personnes âgées, 15/01/2026" },
    ],
    sections: [
      {
        title: "Combien sont-ils ? Deux chiffres, deux définitions",
        paragraphs: [
          "Les deux chiffres qui circulent ne mesurent pas la même chose, et les confondre fausse le débat. La DREES compte 5,3 millions de proches aidants « à la vie quotidienne » en 2022 — soit 8,9 % des 16 ans et plus — en retenant l'aide régulière aux soins personnels, aux tâches domestiques ou à la mobilité, à l'exclusion du seul soutien moral.",
          "Le chiffre de 9,3 millions, plus souvent cité, correspond à une définition plus large (données 2021) qui inclut le soutien moral et l'aide financière. Fait notable : le nombre d'aidants au sens strict a reculé de 6 % depuis 2008, mais l'aide apportée est devenue plus intense.",
        ],
      },
      {
        title: "Le congé de proche aidant",
        paragraphs: [
          "D'une durée de trois mois renouvelable, il est plafonné à un an sur l'ensemble de la carrière, toutes personnes aidées confondues. Il ne demande aucune condition d'ancienneté, et l'employeur ne peut pas le refuser dès lors que les conditions sont remplies. Il peut être fractionné ou transformé en temps partiel, avec l'accord de l'employeur.",
          "La demande se fait un mois avant, sauf urgence — dégradation soudaine de l'état de santé, situation de crise, cessation brutale de l'hébergement — où il s'applique immédiatement. Point essentiel : ce congé n'est pas rémunéré par l'employeur, sauf accord collectif plus favorable. C'est l'AJPA qui prend le relais.",
        ],
      },
      {
        title: "L'AJPA : l'allocation qui compense la perte de revenu",
        bullets: [
          "Montant : 66,64 € par jour au 1er janvier 2026 (la moitié pour une demi-journée).",
          "Plafond : 66 jours indemnisés par personne aidée, pour un maximum de 4 personnes aidées sur la carrière — soit 264 jours au total.",
          "Versement : par la CAF, ou la MSA pour le régime agricole, sur déclaration mensuelle.",
          "Non cumulable notamment avec l'AJPP, l'indemnisation du congé de solidarité familiale, ou une rémunération comme aidant salarié via l'APA ou la PCH.",
        ],
      },
      {
        title: "Le droit au répit, et les 220 plateformes",
        paragraphs: [
          "Le droit au répit majore le plan d'aide APA jusqu'à 583,52 € par an en 2026. Il suppose que la personne aidée bénéficie de l'APA à domicile, que son plan d'aide atteigne son plafond, et que l'aidant soit considéré comme indispensable — c'est-à-dire qu'il ne puisse être remplacé par une autre personne de l'entourage. Il finance de l'accueil de jour ou de nuit, de l'hébergement temporaire, ou un relais à domicile.",
          "En parallèle, 220 plateformes d'accompagnement et de répit couvrent le territoire. Information, écoute, conseil et orientation y sont gratuits ; certaines prestations de répit peuvent rester partiellement à charge. Elles proposent aussi groupes de parole, formations et séjours.",
        ],
      },
      {
        title: "Ce que la loi de 2024 a changé",
        paragraphs: [
          "La loi n° 2024-317 du 8 avril 2024 portant mesures pour bâtir la société du bien vieillir et de l'autonomie a créé le Service public départemental de l'autonomie, guichet unique d'information et d'accompagnement dans chaque département. Elle a également garanti un droit de visite quotidien en établissement, supprimé l'obligation alimentaire pour les petits-enfants, et posé les bases de la stratégie de lutte contre la maltraitance dont est issu le 3133.",
        ],
      },
      {
        title: "Tenir dans la durée",
        bullets: [
          "Faire reconnaître son statut tôt : beaucoup de droits supposent une démarche administrative qui prend des semaines.",
          "Accepter le répit avant l'épuisement, pas après. Le droit au répit existe précisément pour cela.",
          "Ne pas rester seul face aux décisions : les plateformes de répit et les points d'information locaux sont gratuits.",
          "Surveiller sa propre santé. L'épuisement de l'aidant est la première cause de rupture du maintien à domicile.",
        ],
      },
    ],
    faq: [
      {
        q: "Le congé de proche aidant est-il rémunéré ?",
        a: "Pas par l'employeur, sauf accord collectif plus favorable. La compensation passe par l'AJPA, versée par la CAF ou la MSA, à hauteur de 66,64 € par jour au 1er janvier 2026, dans la limite de 66 jours par personne aidée.",
      },
      {
        q: "Combien de temps peut durer le congé de proche aidant ?",
        a: "Trois mois renouvelables, dans la limite d'un an sur l'ensemble de la carrière, toutes personnes aidées et tous renouvellements confondus. Il peut être fractionné ou pris à temps partiel avec l'accord de l'employeur.",
      },
      {
        q: "Comment trouver une plateforme de répit près de chez soi ?",
        a: "Par l'annuaire officiel du portail national pour les personnes âgées, qui recense à la fois les points d'information locaux et les 220 plateformes d'accompagnement et de répit, avec une recherche par commune ou code postal.",
      },
    ],
    sources: [
      { label: "Service-Public — Congé de proche aidant (vérifié le 15/06/2026)", url: "https://www.service-public.gouv.fr/particuliers/vosdroits/F16920" },
      { label: "Portail national — L'allocation journalière du proche aidant (mise à jour 01/06/2026)", url: "https://www.pour-les-personnes-agees.gouv.fr/solutions-pour-les-aidants/soutien-financier/l-allocation-journaliere-du-proche-aidant-qu-est-ce-que-c-est" },
      { label: "Portail national — L'aide au répit dans le cadre de l'APA (mise à jour 15/01/2026)", url: "https://www.pour-les-personnes-agees.gouv.fr/solutions-pour-les-aidants/soutien-financier/l-aide-au-repit-dans-le-cadre-de-l-apa" },
      { label: "Portail national — Les plateformes d'accompagnement et de répit", url: "https://www.pour-les-personnes-agees.gouv.fr/preserver-son-autonomie/a-qui-s-adresser/les-plateformes-d-accompagnement-et-de-repit" },
      { label: "DREES — Études et Résultats n° 1377, Les proches aidants, juin 2026", url: "https://drees.solidarites-sante.gouv.fr/sites/default/files/2026-06/ER1377_Proches_aidants.pdf" },
      { label: "Légifrance — Loi n° 2024-317 du 8 avril 2024", url: "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049385823" },
    ],
  },
  {
    slug: "activites-ehpad",
    emoji: "🏡",
    label: "Activités en EHPAD",
    teaser:
      "Construire un programme d'animation qui tient : formats, adaptation aux troubles, cadre réglementaire.",
    kicker: "EHPAD",
    title: "Activités en EHPAD : idées d'animation et cadre réglementaire",
    intro:
      "Une animation réussie en EHPAD ne se juge pas au nombre de participants mais à ce qu'elle produit : de la parole, du lien, et un sentiment de compétence retrouvé. Ce dossier réunit les formats qui fonctionnent, la façon de les adapter aux troubles cognitifs, et les repères issus de la loi du 8 avril 2024.",
    keyFigures: [
      { value: "1,29 an", label: "de retard moyen des symptômes cognitifs chez les personnes ayant des activités partagées", source: "Hall et al., Neurology, 2009" },
      { value: "÷ 2", label: "le risque de dépression tardive chez les personnes socialement engagées", source: "Menec, Journals of Gerontology, 2003" },
      { value: "2024", label: "la loi « bien vieillir » garantit un droit de visite quotidien en établissement", source: "Loi n° 2024-317 du 8 avril 2024" },
    ],
    sections: [
      {
        title: "Les formats qui fonctionnent",
        bullets: [
          "Les quiz de réminiscence, appuyés sur les objets, chansons et actualités de la jeunesse des résidents : ils sollicitent la mémoire ancienne, souvent préservée plus longtemps que la mémoire récente.",
          "Les ateliers d'écriture ou de récit de vie, y compris dictés à un tiers, qui laissent une trace transmissible à la famille.",
          "Les activités intergénérationnelles avec des écoles ou des familles : ce sont celles qui produisent le plus d'engagement.",
          "Les activités sensorielles et manuelles — cuisine, jardinage, musique — accessibles même en cas de troubles avancés.",
          "Les formats courts et répétés, plus efficaces qu'un grand événement mensuel.",
        ],
      },
      {
        title: "Adapter sans infantiliser",
        paragraphs: [
          "C'est le point le plus délicat du métier. L'adaptation porte sur le support et le rythme, jamais sur le registre de la relation : on simplifie une consigne, on allonge le temps de réponse, on réduit le nombre de choix — mais on s'adresse à un adulte.",
          "Quelques principes tiennent bien en pratique : viser une réussite dès la première minute, éviter les questions dont l'échec est visible par le groupe, valoriser la contribution plutôt que l'exactitude, et prévoir une sortie possible à tout moment sans que la personne ait à se justifier.",
        ],
      },
      {
        title: "Construire un projet d'animation qui tienne",
        bullets: [
          "Partir des histoires de vie recueillies à l'admission plutôt que d'un catalogue d'activités standard.",
          "Équilibrer sur la semaine : cognitif, corporel, sensoriel, social.",
          "Prévoir explicitement les résidents qui ne viennent jamais en salle commune — l'animation en chambre fait partie du projet.",
          "Associer les familles : elles sont une ressource d'animation, pas seulement un public.",
          "Documenter ce qui marche et ce qui ne marche pas, résident par résident.",
        ],
      },
      {
        title: "Les repères issus de la loi du 8 avril 2024",
        paragraphs: [
          "La loi n° 2024-317 portant mesures pour bâtir la société du bien vieillir et de l'autonomie a introduit plusieurs dispositions qui touchent directement la vie quotidienne en établissement : un droit de visite quotidien garanti aux résidents et la désignation d'une personne de confiance, des indicateurs de qualité et des exigences renforcées en matière de restauration et de nutrition, la possibilité d'un hébergement temporaire de nuit, ainsi que le droit d'accueillir son animal de compagnie sous conditions.",
          "Elle a aussi créé le Service public départemental de l'autonomie, interlocuteur utile pour articuler l'établissement avec les dispositifs du territoire.",
        ],
      },
    ],
    faq: [
      {
        q: "Quelles activités proposer à des résidents ayant des troubles cognitifs avancés ?",
        a: "Les activités sensorielles et de réminiscence restent accessibles très longtemps : musique de leur jeunesse, objets à manipuler, odeurs et goûts, jardinage, gestes de cuisine. L'objectif est l'engagement et le plaisir immédiat, pas la performance ni la mémorisation.",
      },
      {
        q: "À quelle fréquence organiser les animations ?",
        a: "Des formats courts et fréquents produisent de meilleurs résultats qu'un événement long et rare. Un rendez-vous quotidien bref, complété par deux ou trois temps forts hebdomadaires, constitue une base réaliste.",
      },
      {
        q: "Les familles peuvent-elles participer aux animations ?",
        a: "Oui, et c'est souvent ce qui fonctionne le mieux. La loi du 8 avril 2024 garantit par ailleurs un droit de visite quotidien aux résidents, ce qui facilite l'inscription des familles dans la vie de l'établissement.",
      },
    ],
    sources: [
      { label: "Légifrance — Loi n° 2024-317 du 8 avril 2024 portant mesures pour bâtir la société du bien vieillir et de l'autonomie", url: "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000049385823" },
      { label: "Sénat — dossier législatif de la loi bien vieillir", url: "https://www.senat.fr/dossier-legislatif/ppl23-147.html" },
      { label: "Hall C.B. et al., Neurology, 2009", url: "https://n.neurology.org/content/73/5/356" },
      { label: "Menec V.H., Journals of Gerontology, 2003", url: "https://academic.oup.com/psychsocgerontology/article/58/2/S74/583612" },
    ],
  },
];

/** Index par slug — utilisé par la route /bien-vieillir/:slug. */
export const FICHES_BY_SLUG = FICHES.reduce((acc, f) => {
  acc[f.slug] = f;
  return acc;
}, {});

export const FICHE_SLUGS = FICHES.map((f) => f.slug);
