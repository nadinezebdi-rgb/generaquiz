import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut, User as UserIcon, Coins } from "lucide-react";
import Logo from "@/components/Logo";

export default function Navbar({ variant = "landing" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 bg-bgmain/90 backdrop-blur-md border-b-2 border-cream">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <Logo size="md" showTagline={true} />

        <nav className="hidden md:flex items-center gap-2">
          {variant === "landing" && (
            <>
              <Link to="/quiz-du-jour" data-testid="nav-daily" className="px-4 py-2 text-lg font-semibold text-bordeaux hover:text-terracotta transition">Quiz du Jour ✨</Link>
              <a href="#categories" data-testid="nav-categories" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Catégories</a>
              <a href="#demo" data-testid="nav-demo" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Essai gratuit</a>
              <a href="#tarifs" data-testid="nav-pricing" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Tarifs</a>
            </>
          )}

          {user && user !== false ? (
            <>
              {variant !== "landing" && (
                <Link to="/quiz-du-jour" data-testid="nav-daily-auth" className="px-4 py-2 text-lg font-semibold text-bordeaux hover:text-terracotta transition">Quiz du Jour ✨</Link>
              )}
              <Link to="/app/dashboard" data-testid="nav-dashboard" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Mes quiz</Link>
              <Link to="/app/challenges" data-testid="nav-challenges" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Défi famille</Link>
              <Link to="/app/earn-credits" data-testid="nav-earn-credits" className="px-3 py-2 text-base font-semibold text-bordeaux hover:text-terracotta transition inline-flex items-center gap-1">
                <Coins className="w-4 h-4" /> Crédits
                {typeof user.credits === "number" && (
                  <span className="ml-1 inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-mustard text-navy text-xs font-bold">{user.credits}</span>
                )}
              </Link>
              <Link to="/app/account" data-testid="nav-account" className="px-4 py-2 text-lg font-semibold text-navy hover:text-terracotta transition">Mon compte</Link>
              {user.role === "admin" && (
                <>
                  <Link to="/app/admin/promo" data-testid="nav-admin-promo" className="px-4 py-2 text-lg font-semibold text-bordeaux hover:text-terracotta transition">Promos</Link>
                  <Link to="/app/admin/reports" data-testid="nav-admin-reports" className="px-4 py-2 text-lg font-semibold text-bordeaux hover:text-terracotta transition">Signalements</Link>
                </>
              )}
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
