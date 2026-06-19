/**
 * Composant générique pour les pages légales (CGU, CGV, Confidentialité).
 * Conserve un look cohérent avec le reste de l'app (paper-bg + bordures).
 */
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Logo from "@/components/Logo";
import Footer from "@/components/Footer";

export default function LegalLayout({ title, lastUpdated, children, testId }) {
  return (
    <div className="min-h-screen paper-bg flex flex-col">
      <header className="bg-white border-b-2 border-cream-dark">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link to="/" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold text-lg">
            <ArrowLeft className="w-5 h-5" /> Retour à l&apos;accueil
          </Link>
          <Logo size="sm" asLink={false} showTagline={false} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex-1 w-full" data-testid={testId}>
        <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">{title}</h1>
        {lastUpdated && (
          <p className="text-base text-navy/60 mb-10">
            Dernière mise à jour : <strong>{lastUpdated}</strong>
          </p>
        )}
        <article className="prose-legal text-navy text-lg leading-relaxed space-y-6">
          {children}
        </article>
      </main>

      <Footer />
    </div>
  );
}
