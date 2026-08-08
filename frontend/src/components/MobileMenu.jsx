import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, X, LogOut, User as UserIcon, Zap, Trophy, Coins } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import SeniorModeToggle from "@/components/SeniorModeToggle";

/**
 * MobileMenu — drawer navigation for viewports < 768px.
 * Mirrors the desktop Navbar links but with tap-friendly rows.
 * Toggled via a hamburger icon.
 */
export default function MobileMenu({ variant = "landing" }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Lock body scroll while the drawer is open
  useEffect(() => {
    if (open) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = prev; };
    }
  }, [open]);

  function close() { setOpen(false); }

  return (
    <div className="lg:hidden">
      <button
        type="button"
        aria-label="Ouvrir le menu"
        aria-expanded={open}
        onClick={() => setOpen(true)}
        data-testid="mobile-menu-open"
        className="inline-flex items-center justify-center p-2 rounded-lg text-navy"
      >
        <Menu className="w-7 h-7" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[60]" data-testid="mobile-menu-panel">
          <button
            type="button"
            aria-label="Fermer le menu"
            onClick={close}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          />
          <nav
            className="absolute top-0 right-0 h-full w-4/5 max-w-xs bg-cream shadow-2xl p-5 flex flex-col overflow-y-auto"
            role="dialog"
            aria-modal="true"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-display text-xl font-extrabold text-navy">Menu</span>
              <button
                type="button"
                aria-label="Fermer le menu"
                onClick={close}
                data-testid="mobile-menu-close"
                className="p-2 rounded-lg text-navy hover:bg-cream-dark"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="border-t border-cream-dark my-2" />

            <div className="flex flex-col gap-0.5">
              {variant === "landing" && (
                <>
                  <MobileLink to="/quiz-du-jour" onClick={close} testid="mobile-nav-daily" accent>Quiz du Jour ✨</MobileLink>
                  <MobileAnchor href="#categories" onClick={close}>Catégories</MobileAnchor>
                  <MobileAnchor href="#demo" onClick={close}>Essai gratuit</MobileAnchor>
                  <MobileAnchor href="#tarifs" onClick={close}>Tarifs</MobileAnchor>
                  <MobileLink to="/pourquoi" onClick={close}>Pourquoi ça marche</MobileLink>
                  <MobileLink to="/ehpad" onClick={close}>Pour les EHPAD</MobileLink>
                </>
              )}

              {user && user !== false ? (
                <>
                  {variant !== "landing" && (
                    <MobileLink to="/quiz-du-jour" onClick={close} accent testid="mobile-nav-daily-auth">Quiz du Jour ✨</MobileLink>
                  )}
                  <MobileLink to="/app/dashboard" onClick={close} testid="mobile-nav-dashboard">Mes quiz</MobileLink>
                  <MobileLink to="/app/atelier" onClick={close} testid="mobile-nav-atelier">Atelier Mémoire</MobileLink>
                  <MobileLink to="/app/charades" onClick={close} testid="mobile-nav-charades">Charades</MobileLink>
                  <MobileLink to="/app/mots-meles" onClick={close} testid="mobile-nav-mots-meles">Mots Mêlés</MobileLink>
                  <MobileLink to="/app/leagues" onClick={close} testid="mobile-nav-leagues" icon={<Trophy className="w-4 h-4" />}>Ligues</MobileLink>
                  <MobileLink to="/app/progression" onClick={close} testid="mobile-nav-progression" icon={<Zap className="w-4 h-4 text-terracotta" />}>
                    Progression · Niv {typeof user.level === "number" ? user.level : 1}
                  </MobileLink>
                  <MobileLink to="/app/challenges" onClick={close} testid="mobile-nav-challenges">Défi famille</MobileLink>
                  <MobileLink to="/app/earn-credits" onClick={close} testid="mobile-nav-earn-credits" icon={<Coins className="w-4 h-4" />} accent>
                    Crédits {typeof user.credits === "number" ? `(${user.credits})` : ""}
                  </MobileLink>
                  <MobileLink to="/app/account" onClick={close} testid="mobile-nav-account">Mon compte</MobileLink>
                  {user.role === "admin" && (
                    <>
                      <div className="mt-2 mb-1 px-3 text-xs uppercase tracking-wider text-navy/50 font-bold">Admin</div>
                      <MobileLink to="/app/admin/analytics" onClick={close} testid="mobile-nav-admin-analytics" accent>Analytics</MobileLink>
                      <MobileLink to="/app/admin/promo" onClick={close} accent>Promos</MobileLink>
                      <MobileLink to="/app/admin/reports" onClick={close} accent>Signalements</MobileLink>
                    </>
                  )}
                </>
              ) : (
                <>
                  <MobileLink to="/login" onClick={close} testid="mobile-nav-login">Connexion</MobileLink>
                  <MobileLink to="/register" onClick={close} testid="mobile-nav-register" accent icon={<UserIcon className="w-4 h-4" />}>Commencer</MobileLink>
                </>
              )}
            </div>

            <div className="mt-auto pt-4 border-t border-cream-dark flex flex-col gap-2">
              <SeniorModeToggle />
              {user && user !== false && (
                <button
                  type="button"
                  data-testid="mobile-nav-logout"
                  onClick={async () => { close(); await logout(); navigate("/"); }}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-full border-2 border-navy text-navy font-bold hover:bg-navy hover:text-white transition"
                >
                  <LogOut className="w-4 h-4" /> Quitter
                </button>
              )}
            </div>
          </nav>
        </div>
      )}
    </div>
  );
}

function MobileLink({ to, onClick, children, testid, accent = false, icon = null }) {
  return (
    <Link
      to={to}
      onClick={onClick}
      data-testid={testid}
      className={`flex items-center gap-2 px-3 py-3 rounded-lg text-base font-semibold transition ${
        accent ? "text-bordeaux hover:bg-cream-dark" : "text-navy hover:bg-cream-dark"
      }`}
    >
      {icon}
      <span>{children}</span>
    </Link>
  );
}

function MobileAnchor({ href, onClick, children }) {
  return (
    <a
      href={href}
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-3 rounded-lg text-base font-semibold text-navy hover:bg-cream-dark transition"
    >
      {children}
    </a>
  );
}
