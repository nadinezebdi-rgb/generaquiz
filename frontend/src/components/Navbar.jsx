import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut, User as UserIcon, Coins, Trophy, Zap } from "lucide-react";
import Logo from "@/components/Logo";
import SeniorModeToggle from "@/components/SeniorModeToggle";
import MobileMenu from "@/components/MobileMenu";
import GamesDropdown from "@/components/GamesDropdown";
import AdminDropdown from "@/components/AdminDropdown";

export default function Navbar({ variant = "landing" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 bg-bgmain/90 backdrop-blur-md border-b-2 border-cream">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <Logo size="md" showTagline={true} />

        <nav className="hidden min-[1400px]:flex items-center gap-1">
          {variant === "landing" && (
            <>
              <Link to="/quiz-du-jour" data-testid="nav-daily" className="px-3 py-2 text-base font-semibold text-bordeaux hover:text-terracotta transition whitespace-nowrap">Quiz du Jour ✨</Link>
              <a href="#categories" data-testid="nav-categories" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Catégories</a>
              <a href="#demo" data-testid="nav-demo" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Essai gratuit</a>
              <a href="#tarifs" data-testid="nav-pricing" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Tarifs</a>
            </>
          )}

          {user && user !== false ? (
            <>
              {variant !== "landing" && (
                <Link to="/quiz-du-jour" data-testid="nav-daily-auth" className="px-3 py-2 text-base font-semibold text-bordeaux hover:text-terracotta transition whitespace-nowrap">Quiz du Jour ✨</Link>
              )}
              <Link to="/app/dashboard" data-testid="nav-dashboard" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Mes quiz</Link>
              <GamesDropdown />
              <Link to="/app/leagues" data-testid="nav-leagues" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition inline-flex items-center gap-1 whitespace-nowrap">
                <Trophy className="w-4 h-4" /> Ligues
              </Link>
              <Link to="/app/progression" data-testid="nav-progression" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition inline-flex items-center gap-1 whitespace-nowrap">
                <Zap className="w-4 h-4 text-terracotta" /> Niv {typeof user.level === "number" ? user.level : 1}
              </Link>
              <Link to="/app/earn-credits" data-testid="nav-earn-credits" className="px-3 py-2 text-base font-semibold text-bordeaux hover:text-terracotta transition inline-flex items-center gap-1 whitespace-nowrap">
                <Coins className="w-4 h-4" /> Crédits
                {typeof user.credits === "number" && (
                  <span className="ml-1 inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-mustard text-navy text-xs font-bold">{user.credits}</span>
                )}
              </Link>
              <Link to="/app/account" data-testid="nav-account" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Mon compte</Link>
              {user.role === "admin" && <AdminDropdown />}
              <button
                data-testid="nav-logout"
                onClick={async () => { await logout(); navigate("/"); }}
                className="ml-1 inline-flex items-center gap-1 px-4 py-2 rounded-full border-2 border-navy text-navy font-bold hover:bg-navy hover:text-white transition whitespace-nowrap"
              >
                <LogOut className="w-4 h-4" /> Quitter
              </button>
              <SeniorModeToggle compact />
            </>
          ) : (
            <>
              <Link to="/login" data-testid="nav-login" className="px-3 py-2 text-base font-semibold text-navy hover:text-terracotta transition whitespace-nowrap">Connexion</Link>
              <Link
                to="/register"
                data-testid="nav-register"
                className="ml-1 inline-flex items-center gap-1 px-4 py-2 rounded-full bg-terracotta text-white font-bold hover:bg-terracotta-dark transition shadow-warm whitespace-nowrap"
              >
                <UserIcon className="w-4 h-4" /> Commencer
              </Link>
              <SeniorModeToggle compact />
            </>
          )}
        </nav>

        {/* Mobile: full drawer menu (< md) */}
        <MobileMenu variant={variant} />
      </div>
    </header>
  );
}
