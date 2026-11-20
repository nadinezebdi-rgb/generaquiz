/**
 * /bien-vieillir/:slug — gabarit unique des cinq dossiers.
 *
 * Un seul composant piloté par le contenu (content/bienVieillir.js) plutôt que
 * cinq pages quasi identiques : le jour où le gabarit évolue, il n'y a qu'un
 * endroit à modifier. Les slugs sont validés contre la liste connue ; tout
 * autre slug renvoie vers le hub (pas de page vide indexable).
 */
import { Link, Navigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, ExternalLink } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import RoutineHebdo from "@/components/bien-vieillir/RoutineHebdo";
import useSeo from "@/lib/seo";
import { FICHES, FICHES_BY_SLUG, HUB } from "@/content/bienVieillir";
import seo from "@/content/bienVieillirSeo.json";

function Section({ section }) {
  return (
    <section className="mt-10">
      <h2 className="font-display text-2xl font-extrabold text-navy sm:text-3xl">{section.title}</h2>
      {section.paragraphs?.map((p, i) => (
        <p key={i} className="mt-4 text-lg leading-relaxed text-navy/80">
          {p}
        </p>
      ))}
      {section.bullets && (
        <ul className="mt-4 space-y-3">
          {section.bullets.map((b, i) => (
            <li key={i} className="flex gap-3 text-lg leading-relaxed text-navy/80">
              <span className="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-terracotta" aria-hidden="true" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function FicheBienVieillir() {
  const { slug } = useParams();
  const fiche = FICHES_BY_SLUG[slug];
  const meta = seo.fiches.find((f) => f.slug === slug);

  // Hooks avant tout retour conditionnel : useSeo tolère des valeurs vides.
  const canonical = meta ? `${seo.siteUrl}${meta.path}` : undefined;
  useSeo(
    meta
      ? {
          title: meta.title,
          description: meta.description,
          keywords: meta.keywords,
          canonical,
          image: seo.defaultOgImage,
          jsonLd: [
            {
              "@context": "https://schema.org",
              "@type": "Article",
              headline: fiche?.title,
              description: meta.description,
              url: canonical,
              inLanguage: "fr-FR",
              isPartOf: { "@type": "WebSite", name: "GénéraQuiz", url: seo.siteUrl },
              publisher: { "@type": "Organization", name: "GénéraQuiz", url: seo.siteUrl },
            },
            {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: (fiche?.faq || []).map((item) => ({
                "@type": "Question",
                name: item.q,
                acceptedAnswer: { "@type": "Answer", text: item.a },
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "BreadcrumbList",
              itemListElement: [
                { "@type": "ListItem", position: 1, name: "Accueil", item: seo.siteUrl },
                { "@type": "ListItem", position: 2, name: "Bien vieillir", item: `${seo.siteUrl}/bien-vieillir` },
                { "@type": "ListItem", position: 3, name: fiche?.label, item: canonical },
              ],
            },
          ],
        }
      : {},
  );

  if (!fiche || !meta) return <Navigate to="/bien-vieillir" replace />;

  const others = FICHES.filter((f) => f.slug !== slug);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />

      <article className="mx-auto max-w-3xl px-6 pb-20 pt-10 lg:px-8">
        <nav aria-label="Fil d'Ariane" className="text-sm text-navy/60">
          <Link to="/bien-vieillir" className="inline-flex items-center gap-1.5 font-semibold hover:text-terracotta">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Bien vieillir
          </Link>
        </nav>

        <header className="mt-6">
          <p className="inline-flex items-center gap-2 rounded-full bg-mustard/30 px-4 py-1.5 text-sm font-bold uppercase tracking-wide text-bordeaux">
            <span aria-hidden="true">{fiche.emoji}</span> {fiche.kicker}
          </p>
          <h1 className="mt-5 font-display text-4xl font-extrabold leading-tight text-navy sm:text-5xl">
            {fiche.title}
          </h1>
          <p className="mt-5 text-xl leading-relaxed text-navy/75">{fiche.intro}</p>
        </header>

        {fiche.keyFigures?.length > 0 && (
          <section aria-label="Chiffres clés" className="mt-10 grid gap-4 sm:grid-cols-3">
            {fiche.keyFigures.map((f, i) => (
              <div key={i} className="rounded-2xl border-2 border-cream-dark bg-white p-5 shadow-warm">
                <p className="font-display text-3xl font-extrabold text-terracotta">{f.value}</p>
                <p className="mt-2 text-sm leading-relaxed text-navy/80">{f.label}</p>
                <p className="mt-2 text-xs italic text-navy/50">{f.source}</p>
              </div>
            ))}
          </section>
        )}

        {fiche.sections.map((section, i) => (
          <Section key={i} section={section} />
        ))}

        {fiche.faq?.length > 0 && (
          <section className="mt-14">
            <h2 className="font-display text-2xl font-extrabold text-navy sm:text-3xl">
              Questions fréquentes
            </h2>
            <dl className="mt-5 space-y-4">
              {fiche.faq.map((item, i) => (
                <div key={i} className="rounded-2xl border-2 border-cream-dark bg-white p-5">
                  <dt className="font-display text-lg font-bold text-navy">{item.q}</dt>
                  <dd className="mt-2 leading-relaxed text-navy/75">{item.a}</dd>
                </div>
              ))}
            </dl>
          </section>
        )}

        <section className="mt-14">
          <h2 className="font-display text-xl font-extrabold text-navy">Sources</h2>
          <ul className="mt-4 space-y-2.5">
            {fiche.sources.map((s, i) => (
              <li key={i} className="text-sm leading-relaxed">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer nofollow"
                  className="inline-flex items-start gap-1.5 text-navy/70 underline decoration-navy/30 underline-offset-2 hover:text-terracotta"
                >
                  <span>{s.label}</span>
                  <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-5 rounded-2xl border border-cream-dark bg-cream/60 px-5 py-4 text-sm leading-relaxed text-navy/70">
            {HUB.disclaimer}
          </p>
        </section>

        <div className="mt-14">
          <RoutineHebdo />
        </div>

        <nav aria-label="Autres dossiers" className="mt-14">
          <h2 className="font-display text-xl font-extrabold text-navy">À lire aussi</h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {others.map((f) => (
              <li key={f.slug}>
                <Link
                  to={`/bien-vieillir/${f.slug}`}
                  data-testid={`bv-related-${f.slug}`}
                  className="group flex h-full items-start gap-3 rounded-2xl border-2 border-cream-dark bg-white p-4 transition hover:border-terracotta"
                >
                  <span className="text-2xl" aria-hidden="true">
                    {f.emoji}
                  </span>
                  <span>
                    <span className="block font-bold text-navy group-hover:text-terracotta">{f.label}</span>
                    <span className="mt-0.5 block text-sm text-navy/60">{f.teaser}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          <Link
            to="/bien-vieillir"
            className="mt-6 inline-flex items-center gap-1.5 font-bold text-terracotta hover:underline"
          >
            Revenir à la rubrique Bien vieillir
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </nav>
      </article>

      <Footer />
    </div>
  );
}
