import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Loader2, ArrowLeft, Check, RotateCcw, Send, PenLine } from "lucide-react";

/**
 * /app/mots-fleches — 5×5 hand-authored crossword MVP.
 *
 * Selection model: click a letter cell to set the cursor. Type A-Z to fill.
 * Backspace clears + moves back. Arrow keys navigate letter cells.
 * "Vérifier" submits the whole board; wrong cells flash red briefly.
 */
export default function MotsFleches() {
  const [grids, setGrids] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/mots-fleches/grids").then((r) => setGrids(r.data)).finally(() => setLoading(false));
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
        onExit={() => {
          setSelectedId(null);
          api.get("/mots-fleches/grids").then((r) => setGrids(r.data));
        }}
      />
    );
  }

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="mots-fleches-page">
        <Link to="/app/dashboard" className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm mb-3">
          <ArrowLeft className="w-4 h-4" /> Mes quiz
        </Link>
        <div className="mb-5">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <PenLine className="w-3.5 h-3.5" /> Grilles 4×4 croisées
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy" data-testid="mots-fleches-title">
            Mots <span className="text-terracotta italic">Fléchés</span>
          </h1>
          <p className="text-navy/70 mt-1">Six grilles thématiques avec vrais croisements (carrés magiques 3×3). +1 pt par lettre correcte, +5 bonus grille complète.</p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          {grids.map((g, i) => (
            <motion.button
              key={g.id}
              type="button"
              onClick={() => setSelectedId(g.id)}
              data-testid={`mots-fleches-grid-${g.id}`}
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
              <div className="text-xs uppercase tracking-wider text-navy/50 mt-0.5">{g.size}×{g.size} · {g.difficulty}</div>
              <div className="text-sm text-navy/70 mt-3">Meilleur score : <strong className="text-navy">{g.best_score}</strong> pts</div>
            </motion.button>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}


function GridPlay({ gridId, onExit }) {
  const [grid, setGrid] = useState(null);
  const [letters, setLetters] = useState([]);  // 2D array of typed chars
  const [cursor, setCursor] = useState(null);  // {r,c}
  const [mistakes, setMistakes] = useState({}); // "r-c" → true briefly
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [liveCheck, setLiveCheck] = useState(true); // Vérifier au fur et à mesure
  const cellRefs = useRef({});
  const checkTimer = useRef(null);

  useEffect(() => {
    api.get(`/mots-fleches/grids/${gridId}`).then((r) => {
      setGrid(r.data);
      setLetters(r.data.cells.map((row) => row.map((c) => c.type === "letter" ? "" : "")));
    });
  }, [gridId]);

  // Debounced live check — appelle /check (no-op DB) 400ms après la dernière frappe
  useEffect(() => {
    if (!liveCheck || !grid) return;
    if (checkTimer.current) clearTimeout(checkTimer.current);
    checkTimer.current = setTimeout(async () => {
      // Ne rien envoyer si aucune lettre saisie
      const hasAny = letters.some((row) => row.some((v) => v));
      if (!hasAny) {
        setMistakes({});
        return;
      }
      try {
        const { data } = await api.post(`/mots-fleches/grids/${gridId}/check`, { letters });
        const m = {};
        for (let r = 0; r < data.mistakes.length; r++) {
          for (let c = 0; c < data.mistakes[r].length; c++) {
            if (data.mistakes[r][c]) m[`${r}-${c}`] = true;
          }
        }
        setMistakes(m);
      } catch (_) { /* silencieux */ }
    }, 400);
    return () => { if (checkTimer.current) clearTimeout(checkTimer.current); };
  }, [letters, liveCheck, grid, gridId]);

  function setLetter(r, c, ch) {
    if (!grid || grid.cells[r][c].type !== "letter") return;
    setLetters((prev) => {
      const next = prev.map((row) => [...row]);
      next[r][c] = ch.toUpperCase().slice(0, 1);
      return next;
    });
    // Efface l'erreur locale de la case dès que le joueur retape (avant debounce)
    setMistakes((prev) => {
      if (!prev[`${r}-${c}`]) return prev;
      const next = { ...prev };
      delete next[`${r}-${c}`];
      return next;
    });
  }

  function moveCursor(dr, dc) {
    if (!cursor || !grid) return;
    let r = cursor.r + dr;
    let c = cursor.c + dc;
    const rows = grid.rows || grid.size;
    const cols = grid.cols || grid.size;
    while (r >= 0 && r < rows && c >= 0 && c < cols) {
      if (grid.cells[r][c].type === "letter") {
        setCursor({ r, c });
        cellRefs.current[`${r}-${c}`]?.focus();
        return;
      }
      r += dr; c += dc;
    }
  }

  async function submit() {
    if (submitting) return;
    setSubmitting(true);
    try {
      const { data } = await api.post(`/mots-fleches/grids/${gridId}/submit`, { letters });
      setResult(data);
      // Show mistakes visually
      const m = {};
      for (let r = 0; r < data.mistakes.length; r++) {
        for (let c = 0; c < data.mistakes[r].length; c++) {
          if (data.mistakes[r][c]) m[`${r}-${c}`] = true;
        }
      }
      setMistakes(m);
      if (data.completed) toast.success(`🏆 Grille complète ! +${data.points_gained} pts`);
      else if (data.points_gained > 0) toast.success(`+${data.points_gained} pts · ${data.correct_cells}/${data.total_cells} bonnes lettres`);
      else toast(`${data.correct_cells}/${data.total_cells} lettres correctes`);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur");
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    if (!grid) return;
    setLetters(grid.cells.map((row) => row.map(() => "")));
    setMistakes({});
    setResult(null);
  }

  const filledCount = useMemo(() => {
    if (!grid) return 0;
    const rows = grid.rows || grid.size;
    const cols = grid.cols || grid.size;
    let n = 0;
    for (let r = 0; r < rows; r++)
      for (let c = 0; c < cols; c++)
        if (grid.cells[r][c].type === "letter" && letters[r]?.[c]) n++;
    return n;
  }, [letters, grid]);

  // Cases appartenant à un mot ENTIÈREMENT correct (ligne ou colonne).
  // Utilisé pour l'effet "Word Complete Celebration" (vert).
  const completedCells = useMemo(() => {
    if (!grid) return {};
    const rows = grid.rows || grid.size;
    const cols = grid.cols || grid.size;
    const out = {};
    // Horizontal words : parcourir chaque ligne
    for (let r = 0; r < rows; r++) {
      const cells = [];
      for (let c = 0; c < cols; c++) {
        if (grid.cells[r][c].type === "letter") cells.push({ r, c });
      }
      if (cells.length === 0) continue;
      const allFilled = cells.every(({ r, c }) => letters[r]?.[c]);
      const noMistake = cells.every(({ r, c }) => !mistakes[`${r}-${c}`]);
      if (allFilled && noMistake) {
        for (const { r, c } of cells) out[`${r}-${c}`] = true;
      }
    }
    // Vertical words : parcourir chaque colonne
    for (let c = 0; c < cols; c++) {
      const cells = [];
      for (let r = 0; r < rows; r++) {
        if (grid.cells[r][c].type === "letter") cells.push({ r, c });
      }
      if (cells.length === 0) continue;
      const allFilled = cells.every(({ r, c }) => letters[r]?.[c]);
      const noMistake = cells.every(({ r, c }) => !mistakes[`${r}-${c}`]);
      if (allFilled && noMistake) {
        for (const { r, c } of cells) out[`${r}-${c}`] = true;
      }
    }
    return out;
  }, [letters, mistakes, grid]);

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

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6" data-testid="mots-fleches-play">
        <button type="button" onClick={onExit} data-testid="mots-fleches-back" className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm mb-3">
          <ArrowLeft className="w-4 h-4" /> Grilles
        </button>

        <div className="flex items-baseline gap-3 flex-wrap mb-4">
          <span className="text-3xl">{grid.emoji}</span>
          <h1 className="font-display text-3xl font-extrabold text-navy" data-testid="mots-fleches-play-title">{grid.theme}</h1>
          <span className="text-sm text-navy/60" data-testid="mots-fleches-filled">{filledCount} lettres saisies</span>
        </div>

        <div
          className="grid gap-[3px] mx-auto max-w-[560px]"
          style={{ gridTemplateColumns: `repeat(${grid.cols || grid.size}, minmax(0, 1fr))` }}
          data-testid="mots-fleches-grid"
        >
          {grid.cells.flatMap((row, r) => row.map((cell, c) => {
            const key = `${r}-${c}`;
            if (cell.type === "block") {
              const isEmpty = !cell.clue_h && !cell.clue_v;
              return (
                <div
                  key={key}
                  data-testid={`mf-cell-block-${r}-${c}`}
                  className={`aspect-square text-cream text-[9px] leading-tight rounded-sm relative overflow-hidden ${
                    isEmpty ? "bg-navy/70" : "bg-navy"
                  }`}
                >
                  {cell.clue_h && (
                    <div className="absolute inset-0 p-1 pr-3 flex flex-col justify-center font-semibold" title="→ à droite">
                      <span>{cell.clue_h}</span>
                      <span aria-hidden="true" className="absolute bottom-0.5 right-0.5 text-mustard text-[13px] leading-none font-bold">▶</span>
                    </div>
                  )}
                  {cell.clue_v && !cell.clue_h && (
                    <div className="absolute inset-0 p-1 pb-3 flex flex-col justify-center font-semibold" title="↓ en bas">
                      <span>{cell.clue_v}</span>
                      <span aria-hidden="true" className="absolute bottom-0.5 right-0.5 text-mustard text-[13px] leading-none font-bold">▼</span>
                    </div>
                  )}
                  {cell.clue_h && cell.clue_v && (
                    /* Both clues share one block — split diagonally with 2 arrows */
                    <div className="absolute inset-0 flex items-end justify-end pr-0.5 pb-0.5">
                      <span aria-hidden="true" className="text-mustard text-[10px] leading-none font-bold">▼</span>
                    </div>
                  )}
                </div>
              );
            }
            const isCursor = cursor && cursor.r === r && cursor.c === c;
            const isMistake = mistakes[key];
            const isCompleted = completedCells[key];
            const val = letters[r]?.[c] ?? "";
            return (
              <input
                key={key}
                ref={(el) => { cellRefs.current[key] = el; }}
                value={val}
                onFocus={() => setCursor({ r, c })}
                onChange={(e) => setLetter(r, c, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Backspace" && !val) {
                    e.preventDefault();
                    moveCursor(0, -1);
                  } else if (e.key === "ArrowRight") { e.preventDefault(); moveCursor(0, 1); }
                  else if (e.key === "ArrowLeft") { e.preventDefault(); moveCursor(0, -1); }
                  else if (e.key === "ArrowDown") { e.preventDefault(); moveCursor(1, 0); }
                  else if (e.key === "ArrowUp") { e.preventDefault(); moveCursor(-1, 0); }
                  else if (/^[a-zA-Z]$/.test(e.key)) {
                    setLetter(r, c, e.key);
                    setTimeout(() => moveCursor(0, 1), 0);
                  }
                }}
                maxLength={1}
                data-testid={`mf-cell-letter-${r}-${c}`}
                className={`aspect-square text-center font-bold uppercase text-lg md:text-xl rounded-sm border-2 focus:outline-none transition ${
                  isMistake
                    ? "bg-[#D9534F]/20 border-[#D9534F] text-[#D9534F]"
                    : isCompleted
                    ? "bg-[#3D9970]/20 border-[#3D9970] text-[#2A7350] shadow-sm"
                    : isCursor
                    ? "bg-mustard/40 border-terracotta text-navy"
                    : "bg-white border-cream-dark text-navy focus:border-terracotta"
                }`}
              />
            );
          }))}
        </div>

        <div className="mt-6 flex justify-center gap-3 flex-wrap items-center">
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-navy select-none cursor-pointer" data-testid="mots-fleches-live-toggle-wrap">
            <input
              type="checkbox"
              checked={liveCheck}
              onChange={(e) => {
                setLiveCheck(e.target.checked);
                if (!e.target.checked) setMistakes({});
              }}
              data-testid="mots-fleches-live-toggle"
              className="w-4 h-4 accent-terracotta"
            />
            Vérifier au fur et à mesure
          </label>
          <button
            type="button"
            onClick={submit}
            disabled={submitting || filledCount === 0}
            data-testid="mots-fleches-submit"
            className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm transition disabled:opacity-50"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Vérifier
          </button>
          <button
            type="button"
            onClick={reset}
            data-testid="mots-fleches-reset"
            className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream font-bold px-4 py-3 rounded-full transition"
          >
            <RotateCcw className="w-4 h-4" /> Vider
          </button>
        </div>

        {result && (
          <div
            className={`mt-4 p-4 rounded-2xl border-2 text-center ${
              result.completed ? "bg-[#3D9970]/10 border-[#3D9970]/40 text-[#2A7350]" : "bg-cream border-cream-dark text-navy"
            }`}
            data-testid="mots-fleches-result"
          >
            {result.completed
              ? <><strong>Bravo !</strong> Grille complète — {result.best_score} pts</>
              : <>{result.correct_cells} / {result.total_cells} lettres correctes ({result.accuracy_pct}%) · meilleur score : {result.best_score}</>}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
