import { Link } from "react-router-dom";
import { Sparkles, Heart } from "lucide-react";

export default function Footer() {
  return (
    <footer className="bg-navy text-cream mt-20">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <span className="w-10 h-10 rounded-full bg-terracotta flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
            </span>
            <span className="font-display text-2xl font-bold">Quiz d'Antan</span>
          </div>
          <p className="text-cream/80 text-lg max-w-md leading-relaxed">
            La plateforme de jeux de mémoire pensée pour les seniors francophones.
            Réveillez vos souvenirs en vous amusant, seul ou en famille.
          </p>
          <div className="mt-6 inline-flex items-center gap-2 text-sm text-cream/60">
            Fait avec <Heart className="w-4 h-4 text-terracotta fill-terracotta" /> en France
          </div>
        </div>

        <div>
          <h4 className="font-display text-lg font-bold mb-3 text-mustard">Plateforme</h4>
          <ul className="space-y-2 text-cream/80">
            <li><Link to="/" className="hover:text-mustard">Accueil</Link></li>
            <li><Link to="/login" className="hover:text-mustard">Connexion</Link></li>
            <li><Link to="/register" className="hover:text-mustard">Inscription</Link></li>
            <li><a href="#tarifs" className="hover:text-mustard">Tarifs</a></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display text-lg font-bold mb-3 text-mustard">À propos</h4>
          <ul className="space-y-2 text-cream/80">
            <li>contact@quizdantan.fr</li>
            <li>01 23 45 67 89</li>
            <li>Paris, France</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-cream/20 py-5 text-center text-cream/60 text-sm">
        © {new Date().getFullYear()} Quiz d'Antan — Tous droits réservés.
      </div>
    </footer>
  );
}
