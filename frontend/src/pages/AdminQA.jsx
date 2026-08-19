import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  ShieldCheck, Filter, Check, X, Wand2, Trash2, RefreshCcw, AlertTriangle, Loader2, ChevronLeft,
} from "lucide-react";
import { Link } from "react-router-dom";

/**
 * AdminQA — dashboard de modération qualité IA.
 *
 * Deux zones :
 *  1. Résumé par catégorie (verified / flagged / unchecked / playable %)
 *  2. Liste des questions filtrables + actions (approuver, appliquer la correction,
 *     re-flagger, supprimer)
 *
 * Toutes les actions sont côté serveur avec vérification de rôle admin.
 */

export default function AdminQA() {
  const [summary, setSummary] = useState(null);
  const [selectedCat, setSelectedCat] = useState("");
  const [quality, setQuality] = useState("flagged");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionOn, setActionOn] = useState(null); // question id being acted on

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/qa/summary");
      setSummary(data);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Chargement résumé impossible");
    }
  }, []);

  const loadItems = useCallback(async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/admin/qa/questions", {
        params: { category_id: selectedCat || undefined, quality, limit: 50, offset: 0 },
      });
      setItems(data.questions);
      setTotal(data.total);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Chargement questions impossible");
    } finally {
      setBusy(false);
    }
  }, [selectedCat, quality]);

  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadItems(); }, [loadItems]);

  async function doAction(q, endpoint, extraBody = {}) {
    setActionOn(q.id);
    try {
      await api.post(`/admin/qa/${q.id}/${endpoint}`, { reason: "", ...extraBody });
      toast.success("OK ✓");
      // Retire l'item localement + refresh du résumé
      setItems((prev) => prev.filter((x) => x.id !== q.id));
      setTotal((n) => n - 1);
      loadSummary();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Action impossible");
    } finally {
      setActionOn(null);
    }
  }

  async function doDelete(q) {
    if (!window.confirm(`Supprimer définitivement cette question ?\n\n"${q.question.slice(0, 100)}"`)) return;
    setActionOn(q.id);
    try {
      await api.delete(`/admin/qa/${q.id}`);
      toast.success("Question supprimée");
      setItems((prev) => prev.filter((x) => x.id !== q.id));
      setTotal((n) => n - 1);
      loadSummary();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Suppression impossible");
    } finally {
      setActionOn(null);
    }
  }

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link to="/app/admin" className="inline-flex items-center gap-1 text-sm text-navy/60 hover:text-navy mb-4">
          <ChevronLeft className="w-4 h-4" /> Admin
        </Link>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 rounded-2xl bg-bordeaux text-cream flex items-center justify-center">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h1 className="font-display text-3xl md:text-4xl font-extrabold" data-testid="admin-qa-title">
            Qualité IA · Modération
          </h1>
        </div>
        <p className="text-navy/70 mb-8">
          Questions vérifiées automatiquement par Claude Opus 4.8. Les questions <strong>flagged</strong> sont automatiquement exclues du tirage.
        </p>

        {/* ==================== SUMMARY ==================== */}
        <section className="mb-10" data-testid="admin-qa-summary">
          <h2 className="text-sm font-bold uppercase tracking-wider text-navy/60 mb-3">Résumé par catégorie</h2>
          {!summary ? (
            <div className="text-navy/50">Chargement…</div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {summary.map((s) => (
                <motion.button
                  key={s.category_id}
                  onClick={() => setSelectedCat(s.category_id === selectedCat ? "" : s.category_id)}
                  data-testid={`admin-qa-cat-${s.category_id}`}
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`text-left bg-white rounded-2xl border-2 p-4 transition ${
                    selectedCat === s.category_id
                      ? "border-terracotta shadow-warm"
                      : "border-cream-dark hover:border-navy/40"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-display text-lg font-extrabold">{s.category_title}</h3>
                    <span className="font-mono text-sm text-navy/60">{s.total} q.</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-cream-dark overflow-hidden flex mb-2">
                    <div className="h-full bg-[#3D9970]" style={{ width: `${(s.verified / s.total) * 100 || 0}%` }} />
                    <div className="h-full bg-cream" style={{ width: `${(s.unchecked / s.total) * 100 || 0}%` }} />
                    <div className="h-full bg-terracotta" style={{ width: `${(s.flagged / s.total) * 100 || 0}%` }} />
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-[#2A7350] font-bold">✓ {s.verified}</span>
                    <span className="text-navy/50">? {s.unchecked}</span>
                    <span className="text-terracotta font-bold">⚠ {s.flagged}</span>
                    <span className="ml-auto text-navy/60">{s.playable_pct}% jouable</span>
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </section>

        {/* ==================== FILTERS ==================== */}
        <section>
          <div className="flex flex-wrap items-center gap-3 mb-4 bg-white p-3 rounded-2xl border-2 border-cream-dark">
            <span className="inline-flex items-center gap-1 text-sm text-navy/60 font-semibold">
              <Filter className="w-4 h-4" /> Filtres
            </span>
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              data-testid="admin-qa-quality-select"
              className="rounded-full border-2 border-cream-dark px-3 py-1.5 text-sm font-semibold bg-white"
            >
              <option value="flagged">Flagged (à modérer)</option>
              <option value="verified">Verified</option>
              <option value="unchecked">Non vérifiées</option>
              <option value="all">Toutes</option>
            </select>
            {selectedCat && (
              <button
                type="button"
                onClick={() => setSelectedCat("")}
                className="inline-flex items-center gap-1 text-sm text-terracotta font-bold"
              >
                × {selectedCat}
              </button>
            )}
            <button
              type="button"
              onClick={() => { loadSummary(); loadItems(); }}
              className="ml-auto inline-flex items-center gap-1 text-sm text-navy hover:text-terracotta font-semibold"
              data-testid="admin-qa-refresh"
            >
              <RefreshCcw className="w-4 h-4" /> Rafraîchir
            </button>
            <span className="font-mono text-sm text-navy/60" data-testid="admin-qa-total">
              {total} résultat{total > 1 ? "s" : ""}
            </span>
          </div>

          {/* ==================== ITEMS LIST ==================== */}
          {busy ? (
            <div className="flex items-center gap-2 text-navy/60 py-8 justify-center">
              <Loader2 className="w-5 h-5 animate-spin" /> Chargement…
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-10 text-navy/50" data-testid="admin-qa-empty">
              Aucune question à ce filtre.
            </div>
          ) : (
            <div className="space-y-3" data-testid="admin-qa-list">
              {items.map((q) => (
                <QuestionCard key={q.id} q={q} actionOn={actionOn} onAction={doAction} onDelete={doDelete} />
              ))}
            </div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}

function QuestionCard({ q, actionOn, onAction, onDelete }) {
  const fc = q.fact_check || {};
  const verdict = fc.verdict || "?";
  const conf = fc.confidence ?? "?";
  const isBusy = actionOn === q.id;

  const verdictColor = {
    correct: "bg-[#3D9970]/15 text-[#2A7350]",
    doubtful: "bg-mustard/25 text-mustard-dark",
    wrong: "bg-terracotta/20 text-terracotta",
    error: "bg-navy/10 text-navy/60",
  }[verdict] || "bg-navy/10 text-navy/60";

  return (
    <div
      className="bg-white rounded-2xl border-2 border-cream-dark p-4"
      data-testid={`admin-qa-item-${q.id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <p className="font-semibold text-navy flex-1">{q.question}</p>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold uppercase ${verdictColor}`}>
            {verdict}
          </span>
          <span className="text-xs text-navy/60 font-mono">{conf}</span>
        </div>
      </div>

      <ul className="grid sm:grid-cols-2 gap-1.5 mb-2 text-sm">
        {q.options?.map((opt, i) => (
          <li
            key={i}
            className={`flex items-start gap-1.5 rounded-lg px-2 py-1 ${
              i === q.correct_index ? "bg-[#3D9970]/10 border border-[#3D9970]/30 font-semibold" : "text-navy/70"
            }`}
          >
            <span className="font-mono text-xs mt-0.5">{String.fromCharCode(65 + i)}.</span>
            <span>{opt}</span>
          </li>
        ))}
      </ul>

      {fc.comment && (
        <div className="flex items-start gap-2 bg-cream rounded-lg p-2 mb-2 text-sm">
          <AlertTriangle className="w-4 h-4 text-mustard-dark mt-0.5 shrink-0" />
          <div>
            <span className="font-bold text-navy">Fact-check :</span> {fc.comment}
            {fc.correction && (
              <div className="mt-1 text-[#2A7350]">
                <strong>Correction proposée :</strong> {fc.correction}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={isBusy}
          onClick={() => onAction(q, "approve")}
          data-testid={`admin-qa-approve-${q.id}`}
          className="inline-flex items-center gap-1 bg-[#3D9970] text-white font-bold px-3 py-1.5 rounded-full hover:bg-[#2A7350] transition text-sm disabled:opacity-50"
        >
          {isBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
          Approuver
        </button>
        {fc.correction && (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onAction(q, "apply-correction")}
            data-testid={`admin-qa-apply-${q.id}`}
            className="inline-flex items-center gap-1 bg-terracotta text-white font-bold px-3 py-1.5 rounded-full hover:bg-terracotta-dark transition text-sm disabled:opacity-50"
          >
            <Wand2 className="w-3.5 h-3.5" />
            Appliquer la correction
          </button>
        )}
        {q.quality !== "flagged" && (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => onAction(q, "flag")}
            data-testid={`admin-qa-flag-${q.id}`}
            className="inline-flex items-center gap-1 bg-white border-2 border-mustard-dark text-mustard-dark font-bold px-3 py-1.5 rounded-full hover:bg-mustard/10 transition text-sm disabled:opacity-50"
          >
            <X className="w-3.5 h-3.5" />
            Flagger
          </button>
        )}
        <button
          type="button"
          disabled={isBusy}
          onClick={() => onDelete(q)}
          data-testid={`admin-qa-delete-${q.id}`}
          className="inline-flex items-center gap-1 ml-auto bg-white border-2 border-cream-dark text-navy/60 hover:text-terracotta hover:border-terracotta font-bold px-3 py-1.5 rounded-full transition text-sm disabled:opacity-50"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Supprimer
        </button>
      </div>

      {fc.checker_model && (
        <p className="text-[10px] text-navy/40 mt-2 uppercase tracking-wider">
          Vérifié par {fc.checker_model}
        </p>
      )}
    </div>
  );
}
