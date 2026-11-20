/**
 * useSeo — per-route <head> management without a third-party dependency.
 *
 * GénéraQuiz is a CRA single-page app: every route shares the <title> and the
 * meta tags declared in `public/index.html`. That is fine for the app itself
 * (routes under /app/* are behind auth and are not indexed) but not for the
 * public marketing pages, which need their own title, description, canonical
 * URL and structured data.
 *
 * This hook writes those tags on mount and restores the previous values on
 * unmount, so navigating between routes never leaves a stale title behind.
 *
 * Note on crawlers: Googlebot executes JavaScript and will pick these tags up.
 * Social scrapers (Facebook, LinkedIn, WhatsApp) do NOT — they read the raw
 * HTML. That is what `frontend/scripts/prerender-seo.js` handles at build time,
 * by writing a static HTML file per route with the same tags baked in. The two
 * mechanisms read from the same source of truth: `content/bienVieillirSeo.json`.
 */
import { useEffect } from "react";

const SITE_NAME = "GénéraQuiz";

/** Create-or-update a <meta> tag, keyed by `name` or `property`. */
function setMeta(attr, key, value) {
  if (!value) return null;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  const existed = Boolean(el);
  const previous = existed ? el.getAttribute("content") : null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute("content", value);
  return () => {
    if (existed) el.setAttribute("content", previous);
    else el.remove();
  };
}

/** Create-or-update <link rel="canonical">. */
function setCanonical(href) {
  if (!href) return null;
  let el = document.head.querySelector('link[rel="canonical"]');
  const existed = Boolean(el);
  const previous = existed ? el.getAttribute("href") : null;
  if (!el) {
    el = document.createElement("link");
    el.setAttribute("rel", "canonical");
    document.head.appendChild(el);
  }
  el.setAttribute("href", href);
  return () => {
    if (existed) el.setAttribute("href", previous);
    else el.remove();
  };
}

/** Inject a JSON-LD block. Always removed on unmount — never shared. */
function setJsonLd(data) {
  if (!data) return null;
  const el = document.createElement("script");
  el.type = "application/ld+json";
  el.dataset.seoManaged = "true";
  el.textContent = JSON.stringify(data);
  document.head.appendChild(el);
  return () => el.remove();
}

/**
 * @param {object}  seo
 * @param {string}  seo.title        Full <title> — write it complete, not a suffix.
 * @param {string}  seo.description  Meta description, ~155 chars.
 * @param {string} [seo.canonical]   Absolute URL. Strongly recommended.
 * @param {string} [seo.keywords]
 * @param {string} [seo.image]       Absolute URL to the OG image.
 * @param {object} [seo.jsonLd]      schema.org object (or array of objects).
 * @param {boolean}[seo.noIndex]     Emit robots=noindex for this route.
 */
export function useSeo({ title, description, canonical, keywords, image, jsonLd, noIndex } = {}) {
  // Les appelants passent un littéral d'objet, recréé à chaque rendu. On le
  // sérialise pour obtenir une dépendance stable et statiquement vérifiable,
  // puis on le relit dans l'effet — sinon l'effet se rejouerait à chaque rendu.
  const jsonLdKey = jsonLd ? JSON.stringify(jsonLd) : "";

  useEffect(() => {
    const cleanups = [];
    const previousTitle = document.title;
    if (title) document.title = title;

    cleanups.push(setMeta("name", "description", description));
    cleanups.push(setMeta("name", "keywords", keywords));
    if (noIndex) cleanups.push(setMeta("name", "robots", "noindex, nofollow"));

    cleanups.push(setMeta("property", "og:title", title));
    cleanups.push(setMeta("property", "og:description", description));
    cleanups.push(setMeta("property", "og:type", "article"));
    cleanups.push(setMeta("property", "og:site_name", SITE_NAME));
    cleanups.push(setMeta("property", "og:locale", "fr_FR"));
    cleanups.push(setMeta("property", "og:url", canonical));
    cleanups.push(setMeta("property", "og:image", image));

    cleanups.push(setMeta("name", "twitter:card", image ? "summary_large_image" : "summary"));
    cleanups.push(setMeta("name", "twitter:title", title));
    cleanups.push(setMeta("name", "twitter:description", description));
    cleanups.push(setMeta("name", "twitter:image", image));

    cleanups.push(setCanonical(canonical));
    cleanups.push(setJsonLd(jsonLdKey ? JSON.parse(jsonLdKey) : null));

    return () => {
      document.title = previousTitle;
      cleanups.forEach((fn) => fn && fn());
    };
  }, [title, description, canonical, keywords, image, noIndex, jsonLdKey]);
}

export default useSeo;
