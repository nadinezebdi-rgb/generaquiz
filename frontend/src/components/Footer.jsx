import { Link } from "react-router-dom";
import { Heart } from "lucide-react";
import Logo from "@/components/Logo";

export default function Footer() {
  return (
    <footer className="bg-navy text-cream mt-20">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <Logo size="md" showTagline={false} asLink={false} dark={true} />
          <p className="text-cream/80 text-lg max-w-md leading-relaxed mt-5">
            La plateforme de quiz qui rapproche les générations — pour partager des moments
            de mémoire et de culture en famille, entre grands-parents, parents et enfants.
          </p>
          <div className="mt-6 inline-flex items-center gap-2 text-sm text-cream/60">
            Fait avec <Heart className="w-4 h-4 text-terracotta fill-terracotta" /> en France · generaquiz.fr
          </div>
        </div>

        <div>
          <h4 className="font-display text-lg font-bold mb-3 text-mustard">Plateforme</h4>
          <ul className="space-y-2 text-cream/80">
            <li><Link to="/" className="hover:text-mustard">Accueil</Link></li>
            <li><Link to="/quiz-du-jour" className="hover:text-mustard">Quiz du Jour</Link></li>
            <li><Link to="/login" className="hover:text-mustard">Connexion</Link></li>
            <li><Link to="/register" className="hover:text-mustard">Inscription</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display text-lg font-bold mb-3 text-mustard">Informations légales</h4>
          <ul className="space-y-2 text-cream/80">
            <li><Link to="/cgu" data-testid="footer-cgu" className="hover:text-mustard">Conditions d&apos;utilisation</Link></li>
            <li><Link to="/cgv" data-testid="footer-cgv" className="hover:text-mustard">Conditions de vente</Link></li>
            <li><Link to="/confidentialite" data-testid="footer-confidentialite" className="hover:text-mustard">Confidentialité (RGPD)</Link></li>
            <li><a href="mailto:contact@generaquiz.fr" className="hover:text-mustard">contact@generaquiz.fr</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-cream/20 py-5 text-center text-cream/60 text-sm">
        © {new Date().getFullYear()} GénéraQuiz — Tous droits réservés.
      </div>
    </footer>
  );
}
