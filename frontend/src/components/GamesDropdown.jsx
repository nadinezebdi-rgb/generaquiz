import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Gamepad2, Feather, MessageCircle, Search, PenLine } from "lucide-react";

/**
 * GamesDropdown — collapsible "Jeux" trigger in the desktop navbar that groups
 * the 4 games under one clean menu. Keyboard-accessible, closes on outside
 * click and on Escape.
 */

const GAMES = [
  { to: "/app/livre",      icon: Feather,         label: "Mon Livre de Vie", desc: "Vos souvenirs, guidés en 10 chapitres", testid: "nav-game-livre" },
  { to: "/app/charades",     icon: MessageCircle,   label: "Charades",         desc: "Mon premier, mon deuxième…",         testid: "nav-game-charades" },
  { to: "/app/mots-meles",   icon: Search,          label: "Mots Mêlés",       desc: "Grilles thématiques IA",             testid: "nav-game-mots-meles" },
  { to: "/app/mots-fleches", icon: PenLine,         label: "Mots Fléchés",     desc: "5×5 MVP interactif",                 testid: "nav-game-mots-fleches" },
];

export default function GamesDropdown() {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        data-testid="nav-games-trigger"
        className={`inline-flex items-center gap-1 px-3 py-2 text-base font-semibold transition ${
          open ? "text-terracotta" : "text-navy hover:text-terracotta"
        }`}
      >
        <Gamepad2 className="w-4 h-4" />
        Jeux
        <ChevronDown className={`w-4 h-4 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          role="menu"
          data-testid="nav-games-menu"
          className="absolute right-0 top-full mt-2 w-72 bg-white border-2 border-cream-dark rounded-2xl shadow-warm p-2 z-50"
        >
          {GAMES.map((g) => {
            const Icon = g.icon;
            return (
              <Link
                key={g.to}
                to={g.to}
                role="menuitem"
                data-testid={g.testid}
                onClick={() => setOpen(false)}
                className="flex items-start gap-3 p-3 rounded-xl hover:bg-cream transition"
              >
                <div className="w-9 h-9 rounded-lg bg-terracotta/15 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-terracotta" />
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-navy leading-tight">{g.label}</div>
                  <div className="text-xs text-navy/60">{g.desc}</div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
