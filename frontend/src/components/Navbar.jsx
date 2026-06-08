import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Sparkles, LogOut, User as UserIcon } from "lucide-react";

export default function Navbar({ variant = "landing" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 bg-bgmain/90 backdrop-blur-md border-b-2 border-cream">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <Link
          to="/"
          data-testid="navbar-logo"
          className="flex items-center gap-3 group"
        >
          <span className="w-11 h-11 rounded-full bg-terracotta flex items-center justify-center shadow-warm group-hover:scale-105 transition-transform">
            <Sparkles className="w-6 h-6 text-white" strokeWidth={2.5} />
          </span>
          <div className="leading-tight">
            <div className="font-display text-2xl font-bold text-navy">Quiz d'Antan</div>
            <div className="text-xs text-navy/60 font-medium tracking-wide">Mémoire & souvenirs</div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-2">
          {variant === "landing" && (
            <>
              <a href="#categories" data-testid="nav-categories" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Catégories</a>
              <a href="#demo" data-testid="nav-demo" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Essai gratuit</a>
              <a href="#tarifs" data-testid="nav-pricing" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Tarifs</a>
            </>
          )}

          {user && user !== false ? (
            <>
              <Link to="/app/dashboard" data-testid="nav-dashboard" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Mes quiz</Link>
              <button
                data-testid="nav-logout"
                onClick={async () => { await logout(); navigate("/"); }}
                className="ml-2 inline-flex items-center gap-2 px-5 py-3 rounded-full border-2 border-navy text-navy font-bold hover:bg-navy hover:text-white transition"
              >
                <LogOut className="w-4 h-4" /> Quitter
              </button>
            </>
          ) : (
            <>
              <Link to="/login" data-testid="nav-login" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Connexion</Link>
              <Link
                to="/register"
                data-testid="nav-register"
                className="ml-2 inline-flex items-center gap-2 px-5 py-3 rounded-full bg-terracotta text-white font-bold hover:bg-terracotta-dark transition shadow-warm"
              >
                <UserIcon className="w-4 h-4" /> Commencer
              </Link>
            </>
          )}
        </nav>

        {/* Mobile: simple CTA */}
        <div className="md:hidden">
          {user && user !== false ? (
            <Link to="/app/dashboard" className="px-4 py-2 rounded-full bg-terracotta text-white font-bold text-sm">Mes quiz</Link>
          ) : (
            <Link to="/register" className="px-4 py-2 rounded-full bg-terracotta text-white font-bold text-sm">Commencer</Link>
          )}
        </div>
      </div>
    </header>
  );
}
