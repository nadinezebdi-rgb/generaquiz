#!/usr/bin/env node
/**
 * Prérendu SEO des pages publiques — exécuté automatiquement après `build`.
 *
 * POURQUOI PAS react-snap : react-snap s'appuie sur Puppeteer et sur
 * `ReactDOM.hydrate`, l'API de React 16. Ce projet est en React 19 (`createRoot`
 * / `hydrateRoot`) et le build tourne chez Emergent, où le téléchargement d'un
 * Chromium headless n'est pas garanti. Le risque de casser le déploiement était
 * supérieur au gain.
 *
 * CE QUE FAIT CE SCRIPT : pour chaque route publique de la rubrique, il écrit
 * `build/<route>/index.html` — une copie de l'index avec le <title>, la meta
 * description, le canonical, les balises Open Graph / Twitter et un JSON-LD
 * injectés en dur. Le corps de page reste rendu côté client, exactement comme
 * aujourd'hui.
 *
 * CE QUE ÇA APPORTE : les robots qui n'exécutent pas JavaScript — Facebook,
 * LinkedIn, WhatsApp, Slack, la plupart des agrégateurs — voient enfin le bon
 * titre et la bonne description. Googlebot, lui, exécute le JS et lisait déjà
 * les balises posées par le hook useSeo.
 *
 * PRÉREQUIS D'HÉBERGEMENT : l'hébergeur doit servir le fichier statique quand
 * il existe, et ne retomber sur `index.html` que sinon (comportement par défaut
 * de la plupart des hébergeurs statiques). Si ce n'est pas le cas, ces fichiers
 * sont simplement ignorés — rien ne casse.
 *
 * Ce script ne fait jamais échouer le build : toute erreur est signalée puis
 * avalée (exit 0).
 */
const fs = require("fs");
const path = require("path");

const BUILD_DIR = path.resolve(__dirname, "..", "build");
const SEO = require("../src/content/bienVieillirSeo.json");

/** Échappe le texte destiné à un attribut HTML. */
function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Toutes les routes à prérendre, dérivées du fichier de métadonnées. */
function routes() {
  return [SEO.hub, ...SEO.fiches].map((m) => ({
    ...m,
    canonical: `${SEO.siteUrl}${m.path}`,
    isHub: m.path === SEO.hub.path,
  }));
}

function headFor(route) {
  const image = SEO.defaultOgImage;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": route.isHub ? "CollectionPage" : "Article",
    headline: route.title,
    description: route.description,
    url: route.canonical,
    inLanguage: "fr-FR",
    isPartOf: { "@type": "WebSite", name: "GénéraQuiz", url: SEO.siteUrl },
  };

  const tags = [
    `<title>${esc(route.title)}</title>`,
    `<meta name="description" content="${esc(route.description)}" />`,
    `<meta name="keywords" content="${esc(route.keywords)}" />`,
    `<link rel="canonical" href="${esc(route.canonical)}" />`,
    `<meta property="og:type" content="${route.isHub ? "website" : "article"}" />`,
    `<meta property="og:site_name" content="GénéraQuiz" />`,
    `<meta property="og:locale" content="fr_FR" />`,
    `<meta property="og:title" content="${esc(route.title)}" />`,
    `<meta property="og:description" content="${esc(route.description)}" />`,
    `<meta property="og:url" content="${esc(route.canonical)}" />`,
    `<meta name="twitter:card" content="${image ? "summary_large_image" : "summary"}" />`,
    `<meta name="twitter:title" content="${esc(route.title)}" />`,
    `<meta name="twitter:description" content="${esc(route.description)}" />`,
    `<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>`,
  ];

  // Une og:image absente vaut mieux qu'une og:image cassée : les réseaux
  // affichent alors leur propre aperçu au lieu d'un cadre vide.
  if (image) {
    tags.push(`<meta property="og:image" content="${esc(image)}" />`);
    tags.push(`<meta name="twitter:image" content="${esc(image)}" />`);
  }

  return tags.join("\n        ");
}

/**
 * Remplace dans le HTML les balises que nous réécrivons, puis injecte le bloc.
 * On retire d'abord le <title> et la meta description d'origine pour ne pas en
 * laisser deux — les robots retiennent en général la première occurrence.
 */
function render(template, route) {
  let html = template
    .replace(/<title>[\s\S]*?<\/title>\s*/i, "")
    .replace(/<meta\s+name="description"[^>]*>\s*/i, "");

  const marker = "</head>";
  const idx = html.toLowerCase().lastIndexOf(marker);
  if (idx === -1) throw new Error("balise </head> introuvable dans build/index.html");

  return `${html.slice(0, idx)}    ${headFor(route)}\n    ${html.slice(idx)}`;
}

function main() {
  const indexPath = path.join(BUILD_DIR, "index.html");
  if (!fs.existsSync(indexPath)) {
    console.warn("[prerender-seo] build/index.html absent — étape ignorée.");
    return;
  }

  const template = fs.readFileSync(indexPath, "utf8");
  let written = 0;

  for (const route of routes()) {
    const outDir = path.join(BUILD_DIR, route.path.replace(/^\//, ""));
    fs.mkdirSync(outDir, { recursive: true });
    fs.writeFileSync(path.join(outDir, "index.html"), render(template, route), "utf8");
    written += 1;
    console.log(`[prerender-seo] ${route.path} -> ${path.relative(BUILD_DIR, outDir)}/index.html`);
  }

  console.log(`[prerender-seo] ${written} page(s) prérendue(s).`);
}

try {
  main();
} catch (err) {
  // Ne jamais faire échouer un déploiement pour une étape d'optimisation.
  console.warn(`[prerender-seo] ignoré : ${err && err.message}`);
}
process.exit(0);
