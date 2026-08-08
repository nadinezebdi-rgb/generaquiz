import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Loader2, ArrowLeft, Trophy, Sparkles, Check, RotateCcw, Search } from "lucide-react";

/**
 * /app/mots-meles — Mots Mêlés word search game.
 *
 * Layout:
 *   1. Grid list (theme cards, click to enter)
 *   2. Grid play (12×12 letter grid + word list on the right)
 *
 * Word selection: click the FIRST letter, then click the LAST letter.
 * The visual highlight covers every cell on the straight line between them.
 * Server validates the line matches a target word — anti-cheat.
 */

export default function MotsMeles() {
  const [grids, setGrids] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    api.get("/mots-meles/grids").then((r) => setGrids(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-5xl mx-auto px-4 py-16 flex justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
        </div>
      </div>
    );
  }

  if (selectedId) {
    return (
      <GridPlay
        gridId={selectedId}
        onExit={(refresh) => {
          setSelectedId(null);
          if (refresh) {
            api.get("/mots-meles/grids").then((r) => setGrids(r.data));
          }
        }}
      />
    );
  }

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="mots-meles-page">
        <Link to="/app/dashboard" className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm mb-3">
          <ArrowLeft className="w-4 h-4" /> Mes quiz
        </Link>
        <div className="mb-6">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <Sparkles className="w-3.5 h-3.5" /> Nouveau jeu
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy" data-testid="mots-meles-title">
            Mots <span className="text-terracotta italic">Mêlés</span>
          </h1>
          <p className="text-navy/70 mt-1">
            Retrouvez les mots cachés dans la grille. +2 points par mot, +10 pour la grille complétée.
          </p>
        </div>

        {grids.length === 0 ? (
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-8 text-center text-navy/60">
            Aucune grille disponible pour l&apos;instant.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-4">
            {grids.map((g, i) => (
              <motion.button
                key={g.id}
                type="button"
                onClick={() => setSelectedId(g.id)}
                data-testid={`mots-meles-grid-${g.id}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                whileHover={{ y: -3 }}
                className="bg-white border-2 border-cream-dark rounded-2xl p-5 text-left hover:border-terracotta transition"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-3xl">{g.emoji}</span>
                  {g.completed && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-[#2A7350] bg-[#3D9970]/15 px-2 py-1 rounded-full">
                      <Check className="w-3 h-3" /> Complète
                    </span>
                  )}
                </div>
                <div className="font-display text-xl font-extrabold text-navy">{g.theme}</div>
                <div className="text-xs uppercase tracking-wider text-navy/50 mt-0.5">
                  {g.size}×{g.size} · {g.difficulty} · {g.source === "mistral" ? "IA" : "sélection"}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-sm text-navy/70">
                    <strong className="text-navy">{g.found_count}</strong> / {g.words_count} mots trouvés
                  </div>
                  <span className="text-sm font-bold text-terracotta">Ouvrir →</span>
                </div>
                <div className="h-1.5 bg-cream-dark rounded-full overflow-hidden mt-2">
                  <div className="h-full bg-terracotta" style={{ width: `${(g.found_count / (g.words_count || 1)) * 100}%` }} />
                </div>
              </motion.button>
            ))}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}


/* ============================================================
 * GridPlay — interactive 12×12 grid + word list
 * ============================================================ */

function cellsOnLine(r0, c0, r1, c1) {
  const dr = r0 === r1 ? 0 : r1 > r0 ? 1 : -1;
  const dc = c0 === c1 ? 0 : c1 > c0 ? 1 : -1;
  const stepsR = Math.abs(r1 - r0);
  const stepsC = Math.abs(c1 - c0);
  if (dr === 0 && dc === 0) return [{ r: r0, c: c0 }];
  if (stepsR !== 0 && stepsC !== 0 && stepsR !== stepsC) return null; // invalid diagonal
  const length = Math.max(stepsR, stepsC) + 1;
  return Array.from({ length }, (_, i) => ({ r: r0 + dr * i, c: c0 + dc * i }));
}

function GridPlay({ gridId, onExit }) {
  const [grid, setGrid] = useState(null);
  const [start, setStart] = useState(null);          // {r, c} — first click
  const [hover, setHover] = useState(null);          // {r, c} — hover to preview
  const [foundCells, setFoundCells] = useState({});  // key "r-c" → true (for permanent highlight)
  const [awardedCells, setAwardedCells] = useState([]); // last-found line for a brief pulse
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/mots-meles/grids/${gridId}`).then((r) => {
      setGrid(r.data);
      // Note: we don't get word positions from the server (anti-cheat) so the
      // "already found" cells will only light up on subsequent finds during this
      // session. That's OK for MVP.
    });
  }, [gridId]);

  const cellClick = useCallback(async (r, c) => {
    if (busy) return;
    if (!start) {
      setStart({ r, c });
      return;
    }
    // Second click: attempt to find word
    const line = cellsOnLine(start.r, start.c, r, c);
    if (!line) {
      toast.error("La sélection doit être en ligne droite ou diagonale");
      setStart(null);
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post(`/mots-meles/grids/${gridId}/find`, {
        row_start: start.r, col_start: start.c, row_end: r, col_end: c,
      });
      if (data.correct && !data.already_found) {
        toast.success(`${data.word} trouvé ! +${data.points_gained} pts`);
        const key = (cell) => `${cell.r}-${cell.c}`;
        const updates = {};
        line.forEach((cell) => { updates[key(cell)] = true; });
        setFoundCells((prev) => ({ ...prev, ...updates }));
        setAwardedCells(line);
        setTimeout(() => setAwardedCells([]), 900);
        // Update grid.words
        setGrid((g) => ({
          ...g,
          words: g.words.map((w) => w.word === data.word ? { ...w, found: true } : w),
        }));
        if (data.completed) {
          toast.success("🏆 Grille terminée ! +10 pts bonus");
        }
      } else if (data.correct && data.already_found) {
        toast(`${data.word} déjà trouvé.`);
      } else {
        // Wrong — brief negative pulse (no toast to keep UX quiet)
      }
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur");
    } finally {
      setStart(null);
      setBusy(false);
    }
  }, [start, busy, gridId]);

  if (!grid) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-5xl mx-auto px-4 py-16 flex justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
        </div>
      </div>
    );
  }

  const previewCells = start && hover ? cellsOnLine(start.r, start.c, hover.r, hover.c) : null;
  const previewSet = new Set((previewCells || []).map((c) => `${c.r}-${c.c}`));
  const awardedSet = new Set(awardedCells.map((c) => `${c.r}-${c.c}`));
  const totalWords = grid.words.length;
  const foundWords = grid.words.filter((w) => w.found).length;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6" data-testid="mots-meles-play">
        <button
          type="button"
          onClick={() => onExit(true)}
          data-testid="mots-meles-back"
          className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm mb-3"
        >
          <ArrowLeft className="w-4 h-4" /> Grilles
        </button>

        <div className="flex items-baseline gap-3 flex-wrap mb-4">
          <span className="text-3xl">{grid.emoji}</span>
          <h1 className="font-display text-3xl font-extrabold text-navy" data-testid="mots-meles-play-title">{grid.theme}</h1>
          <span className="inline-flex items-center gap-1 text-sm font-bold text-terracotta" data-testid="mots-meles-progress">
            <Trophy className="w-4 h-4" /> {foundWords} / {totalWords}
          </span>
        </div>

        <div className="grid lg:grid-cols-[1fr,240px] gap-6">
          {/* GRID */}
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-3 md:p-5" data-testid="mots-meles-grid">
            <div className="text-xs text-navy/60 mb-2 text-center">
              Cliquez la 1ʳᵉ lettre, puis la dernière.
              {start && <span className="text-terracotta font-bold"> Sélectionnez la fin (ou re-cliquez pour annuler).</span>}
            </div>
            <div
              className="grid gap-[2px] sm:gap-[3px] select-none"
              style={{ gridTemplateColumns: `repeat(${grid.size}, minmax(0, 1fr))` }}
              onMouseLeave={() => setHover(null)}
            >
              {grid.grid.flatMap((row, r) => row.map((letter, c) => {
                const k = `${r}-${c}`;
                const isStart = start && start.r === r && start.c === c;
                const inPreview = previewSet.has(k);
                const inFound = foundCells[k];
                const inAwarded = awardedSet.has(k);
                return (
                  <button
                    key={k}
                    type="button"
                    onClick={() => cellClick(r, c)}
                    onMouseEnter={() => setHover({ r, c })}
                    data-testid={`mots-meles-cell-${r}-${c}`}
                    className={`aspect-square flex items-center justify-center rounded-md text-sm md:text-base font-bold uppercase transition ${
                      inAwarded
                        ? "bg-mustard text-navy ring-2 ring-terracotta"
                        : inFound
                        ? "bg-[#3D9970]/30 text-navy"
                        : isStart
                        ? "bg-terracotta text-white"
                        : inPreview
                        ? "bg-terracotta/40 text-navy"
                        : "bg-cream border border-cream-dark text-navy hover:bg-cream-dark"
                    }`}
                  >
                    {letter}
                  </button>
                );
              }))}
            </div>
            {start && (
              <button
                type="button"
                onClick={() => setStart(null)}
                data-testid="mots-meles-cancel-selection"
                className="mt-3 mx-auto inline-flex items-center gap-1 text-sm text-navy/70 hover:text-navy font-bold"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Annuler la sélection
              </button>
            )}
          </div>

          {/* WORD LIST */}
          <aside className="bg-white border-2 border-cream-dark rounded-[24px] p-4 max-h-[60vh] overflow-y-auto" data-testid="mots-meles-words">
            <div className="font-display font-extrabold text-navy mb-2 flex items-center gap-2">
              <Search className="w-4 h-4 text-terracotta" /> Mots à trouver
            </div>
            <ul className="space-y-1.5">
              {grid.words.map((w) => (
                <li
                  key={w.word}
                  data-testid={`mots-meles-word-${w.word}`}
                  className={`text-sm font-bold ${
                    w.found ? "text-[#2A7350] line-through" : "text-navy"
                  }`}
                >
                  {w.found && "✓ "}{w.word}
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}
