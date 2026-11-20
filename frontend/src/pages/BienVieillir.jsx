/**
 * /bien-vieillir — page pilier de la rubrique.
 *
 * Publique, indexable. Le <head> est écrit par useSeo au montage et par le
 * script de prérendu au build (frontend/scripts/prerender-seo.js) : les deux
 * lisent content/bienVieillirSeo.json.
 */
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import RoutineHebdo from "@/components/bien-vieillir/RoutineHebdo";
import useSeo from "@/lib/seo";
import { HUB, FICHES } from "@/content/bienVieillir";
import seo from "@/content/bienVieillirSeo.json";

export default function BienVieillir() {
  const meta = seo.hub;
  const canonical = `${seo.siteUrl}${meta.path}`;

  useSeo({
    title: meta.title,
    description: meta.description,
    keywords: meta.keywords,
    canonical,
    image: seo.defaultOgImage,
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: HUB.title,
      description: meta.description,
      url: canonical,
      inLanguage: "fr-FR",
      isPartOf: { "@type": "WebSite", name: "GénéraQuiz", url: seo.siteUrl },
      hasPart: FICHES.map((f) => ({
        "@type": "Article",
        headline: f.title,
        url: `${seo.siteUrl}/bien-vieillir/${f.slug}`,
      })),
    },
  });

  return (
    <div className="min-h-screen paper-bg">
      <Navbar />

      <header className="mx-auto max-w-4xl px-6 pb-6 pt-14 text-center lg:px-8">
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 rounded-full bg-mustard/30 px-4 py-1.5 text-sm font-bold uppercase tracking-wide text-bordeaux"
        >
          <span aria-hidden="true">{HUB.emoji}</span> {HUB.kicker}
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mt-5 font-display text-4xl font-extrabold leading-tight text-navy sm:text-5xl"
        >
          {HUB.title}
        </motion.h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-navy/75">{HUB.intro}</p>
      </header>

      <main className="mx-auto max-w-5xl px-6 pb-20 lg:px-8">
        <nav aria-label="Les dossiers de la rubrique" className="mt-10">
          <h2 className="sr-only">Les cinq dossiers</h2>
          <ul className="grid gap-5 sm:grid-cols-2">
            {FICHES.map((fiche, i) => (
              <motion.li
                key={fiche.slug}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ delay: i * 0.05 }}
                className={i === 0 ? "sm:col-span-2" : undefined}
              >
                <Link
                  to={`/bien-vieillir/${fiche.slug}`}
                  data-testid={`bv-card-${fiche.slug}`}
                  className="group flex h-full flex-col rounded-3xl border-2 border-cream-dark bg-white p-6 shadow-warm transition hover:-translate-y-0.5 hover:border-terracotta"
                >
                  <span className="text-3xl" aria-hidden="true">
                    {fiche.emoji}
                  </span>
                  <h3 className="mt-3 font-display text-xl font-extrabold text-navy group-hover:text-terracotta sm:text-2xl">
                    {fiche.title}
                  </h3>
                  <p className="mt-2 flex-1 leading-relaxed text-navy/70">{fiche.teaser}</p>
                  <span className="mt-4 inline-flex items-center gap-1.5 font-bold text-terracotta">
                    Lire le dossier
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" aria-hidden="true" />
                  </span>
                </Link>
              </motion.li>
            ))}
          </ul>
        </nav>

        <div className="mt-14">
          <RoutineHebdo />
        </div>

        <aside className="mt-14 rounded-3xl bg-navy px-6 py-10 text-center text-cream sm:px-10">
          <Sparkles className="mx-auto h-8 w-8 text-mustard" aria-hidden="true" />
          <h2 className="mt-4 font-display text-2xl font-extrabold sm:text-3xl">
            La stimulation cognitive, en jouant à plusieurs
          </h2>
          <p className="mx-auto mt-3 max-w-xl leading-relaxed text-cream/80">
            GénéraQuiz applique ces principes : des quiz de mémoire à partager entre générations,
            un mode coopératif, et un rythme régulier plutôt que des sessions marathon.
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link
              to="/quiz-du-jour"
              data-testid="bv-cta-daily"
              className="rounded-full bg-terracotta px-6 py-3 font-bold text-white transition hover:bg-terracotta-dark"
            >
              Essayer le Quiz du Jour
            </Link>
            <Link
              to="/pourquoi"
              data-testid="bv-cta-pourquoi"
              className="rounded-full border-2 border-cream px-6 py-3 font-bold text-cream transition hover:bg-cream hover:text-navy"
            >
              Pourquoi ça marche
            </Link>
          </div>
        </aside>

        <p className="mt-10 rounded-2xl border border-cream-dark bg-cream/60 px-5 py-4 text-sm leading-relaxed text-navy/70">
          {HUB.disclaimer}
        </p>
      </main>

      <Footer />
    </div>
  );
}
