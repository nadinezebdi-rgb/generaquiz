import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  MessageCircle, ArrowRight, ArrowLeft, Check, X, Lightbulb, Loader2,
  Trophy, RotateCcw,
} from "lucide-react";

/**
 * /app/charades — 13 pre-authored French charades, played one by one.
 * Anti-cheat: the client NEVER sees the answer; each attempt is graded
 * server-side, points are awarded on FIRST correct answer only.
 */

export default function Charades() {
  const [packs, setPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState("classique");
  const [list, setList] = useState(null);          // {charades[], solved_ids[], points_per_correct}
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState("");
  const [showHint, setShowHint] = useState(false);
  const [reveal, setReveal] = useState(null);       // {correct, expected, points_gained, awarded_badges}
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get("/charades/packs").then((r) => setPacks(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setList(null);
    setIdx(0);
    setAnswer("");
    setReveal(null);
    setShowHint(false);
    api.get(`/charades/list?pack=${selectedPack}`).then((r) => setList(r.data)).catch(() => {});
  }, [selectedPack]);

  const current = list?.charades?.[idx];
  const solvedSet = useMemo(() => new Set(list?.solved_ids || []), [list]);
  // Only count the ids that belong to the CURRENT pack — /list already filters by pack,
  // so intersecting with the charades in the response gives the pack-local count.
  const packCharadeIds = useMemo(() => new Set((list?.charades || []).map((c) => c.id)), [list]);
  const solvedCount = list?.solved_ids?.filter((id) => packCharadeIds.has(id)).length || 0;
  const total = list?.charades?.length || 0;

  async function submit() {
    if (!current || !answer.trim()) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/charades/attempt", {
        charade_id: current.id,
        answer: answer.trim(),
      });
      setReveal(data);
      if (data.correct && !data.already_solved) {
        toast.success(`Bravo ! +${data.points_gained} points`);
        // Update local solved set
        setList((l) => ({ ...l, solved_ids: [...l.solved_ids, current.id] }));
      } else if (data.correct && data.already_solved) {
        toast("Bonne réponse — déjà résolue précédemment.");
      }
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur de validation");
    } finally {
      setSubmitting(false);
    }
  }

  function nextCharade() {
    setAnswer("");
    setShowHint(false);
    setReveal(null);
    setIdx((i) => (i + 1) % (list.charades.length || 1));
  }

  function prevCharade() {
    setAnswer("");
    setShowHint(false);
    setReveal(null);
    setIdx((i) => (i - 1 + list.charades.length) % list.charades.length);
  }

  if (!list) {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <div className="max-w-3xl mx-auto px-4 py-16 flex justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-terracotta" />
        </div>
      </div>
    );
  }

  const alreadySolved = solvedSet.has(current.id);
  const progressPct = total ? Math.round((solvedCount / total) * 100) : 0;

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-testid="charades-page">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <Link
            to="/app/dashboard"
            data-testid="charades-back"
            className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Mes quiz
          </Link>
          <div className="flex items-center gap-2 text-sm font-bold text-navy/70">
            <Trophy className="w-4 h-4 text-terracotta" />
            <span data-testid="charades-solved-count">{solvedCount} / {total} résolues</span>
          </div>
        </div>

        <div className="mb-1 flex items-baseline gap-3 flex-wrap">
          <h1 className="font-display text-3xl md:text-4xl font-extrabold text-navy" data-testid="charades-title">
            Charades <span className="text-terracotta italic">françaises</span>
          </h1>
          <span className="text-sm text-navy/60">
            Devinez le mot caché — {list.points_per_correct} points par bonne réponse
          </span>
        </div>

        {/* Pack tabs */}
        {packs.length > 0 && (
          <div className="flex gap-2 my-4 flex-wrap" data-testid="charades-packs">
            {packs.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setSelectedPack(p.id)}
                data-testid={`charades-pack-${p.id}`}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-bold border-2 transition ${
                  selectedPack === p.id
                    ? "bg-navy border-navy text-cream"
                    : "bg-white border-cream-dark text-navy hover:border-terracotta"
                }`}
              >
                <span>{p.emoji}</span>
                <span>{p.label}</span>
                <span className={`text-xs ${selectedPack === p.id ? "text-cream/70" : "text-navy/50"}`}>
                  {p.solved}/{p.total}
                </span>
              </button>
            ))}
          </div>
        )}

        <div className="h-2 bg-cream-dark rounded-full overflow-hidden mb-6">
          <div className="h-full bg-terracotta transition-all" style={{ width: `${progressPct}%` }} data-testid="charades-progress-bar" />
        </div>

        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-5 md:p-8" data-testid="charades-card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <span className="text-xs uppercase tracking-wider font-bold text-navy/60">
              Charade {idx + 1} / {total}
            </span>
            {alreadySolved && (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-[#2A7350] bg-[#3D9970]/15 px-2 py-0.5 rounded-full" data-testid="charades-badge-solved">
                <Check className="w-3.5 h-3.5" /> Déjà résolue
              </span>
            )}
          </div>

          <AnimatePresence mode="wait">
            <motion.ul
              key={current.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              className="space-y-2 mb-6 text-navy"
              data-testid="charades-parts"
            >
              {current.parts.map((p, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-terracotta font-extrabold shrink-0">◆</span>
                  <span className="text-lg leading-relaxed">{p}</span>
                </li>
              ))}
            </motion.ul>
          </AnimatePresence>

          {!reveal && (
            <>
              {showHint && (
                <div className="bg-mustard/25 border-2 border-mustard rounded-xl p-3 mb-4 flex items-start gap-2" data-testid="charades-hint">
                  <Lightbulb className="w-4 h-4 text-mustard-dark shrink-0 mt-0.5" />
                  <span className="text-sm text-navy/80">{current.hint}</span>
                </div>
              )}
              <label className="block text-sm font-bold text-navy mb-2">Votre réponse</label>
              <input
                type="text"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !submitting && submit()}
                placeholder="Un seul mot…"
                autoFocus
                data-testid="charades-answer-input"
                className="w-full px-4 py-3 text-lg rounded-2xl border-2 border-cream-dark focus:border-terracotta bg-white min-h-[52px]"
              />
              <div className="mt-4 flex items-center justify-between flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setShowHint((v) => !v)}
                  data-testid="charades-hint-toggle"
                  className="inline-flex items-center gap-1 text-navy/70 hover:text-navy text-sm font-bold"
                >
                  <Lightbulb className="w-4 h-4" /> {showHint ? "Cacher l'indice" : "Voir l'indice"}
                </button>
                <button
                  type="button"
                  onClick={submit}
                  disabled={submitting || !answer.trim()}
                  data-testid="charades-submit"
                  className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm transition disabled:opacity-50"
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Valider
                </button>
              </div>
            </>
          )}

          {reveal && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`rounded-2xl p-4 md:p-5 border-2 ${
                reveal.correct
                  ? "bg-[#3D9970]/10 border-[#3D9970]/40"
                  : "bg-[#D9534F]/10 border-[#D9534F]/40"
              }`}
              data-testid="charades-reveal"
            >
              <div className="flex items-center gap-2 mb-2">
                {reveal.correct ? (
                  <Check className="w-6 h-6 text-[#2A7350]" />
                ) : (
                  <X className="w-6 h-6 text-[#D9534F]" />
                )}
                <span className={`font-display text-xl font-extrabold ${
                  reveal.correct ? "text-[#2A7350]" : "text-[#D9534F]"
                }`} data-testid="charades-reveal-verdict">
                  {reveal.correct ? "Bravo !" : "Ce n'est pas ça"}
                </span>
              </div>
              <div className="text-navy mb-3">
                La réponse était : <strong data-testid="charades-reveal-answer">{reveal.expected}</strong>
              </div>
              {reveal.points_gained > 0 && (
                <div className="text-terracotta font-bold text-sm mb-3">+{reveal.points_gained} points</div>
              )}
              {reveal.awarded_badges?.length > 0 && (
                <div className="bg-white rounded-xl border-2 border-mustard p-3 mb-3" data-testid="charades-badge-award">
                  <div className="text-xs uppercase tracking-wider font-bold text-mustard-dark mb-1">Badge débloqué</div>
                  {reveal.awarded_badges.map((b) => (
                    <div key={b.id} className="flex items-center gap-2">
                      <span className="text-2xl">{b.emoji}</span>
                      <div>
                        <div className="font-bold text-navy">{b.title}</div>
                        <div className="text-xs text-navy/60">{b.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={nextCharade}
                  data-testid="charades-next"
                  className="inline-flex items-center gap-2 bg-navy hover:bg-navy-dark text-cream font-bold px-5 py-3 rounded-full transition"
                >
                  Charade suivante <ArrowRight className="w-4 h-4" />
                </button>
                {!reveal.correct && (
                  <button
                    type="button"
                    onClick={() => { setReveal(null); setAnswer(""); }}
                    data-testid="charades-retry"
                    className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-cream font-bold px-4 py-3 rounded-full transition"
                  >
                    <RotateCcw className="w-4 h-4" /> Reprendre
                  </button>
                )}
              </div>
            </motion.div>
          )}

          <div className="mt-6 pt-4 border-t border-cream-dark flex items-center justify-between">
            <button
              type="button"
              onClick={prevCharade}
              data-testid="charades-prev"
              className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm"
            >
              <ArrowLeft className="w-4 h-4" /> Précédente
            </button>
            <button
              type="button"
              onClick={nextCharade}
              data-testid="charades-skip"
              className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm"
            >
              Passer <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
