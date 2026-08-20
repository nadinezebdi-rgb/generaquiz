import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  ShieldCheck, Filter, Check, X, Wand2, Trash2, RefreshCcw, AlertTriangle, Loader2, ChevronLeft, Search, PlayCircle, CheckSquare, Square,
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
  const [searchQ, setSearchQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionOn, setActionOn] = useState(null); // question id being acted on
  const [jobs, setJobs] = useState([]);
  const [queue, setQueue] = useState(null);
  const [rerunning, setRerunning] = useState(null); // category_id being rerun
  const [selected, setSelected] = useState(() => new Set()); // ids selectionnés pour bulk
  const [bulkBusy, setBulkBusy] = useState(false);

  const loadSummary = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/qa/summary");
      setSummary(data);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Chargement résumé impossible");
    }
  }, []);

  const loadJobs = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/qa/jobs", { params: { limit: 10 } });
      setJobs(data);
    } catch (err) {
      console.debug("Load jobs failed:", err);
    }
  }, []);

  const loadQueue = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/qa/queue");
      setQueue(data);
    } catch (err) {
      console.debug("Load queue failed:", err);
    }
  }, []);

  const loadItems = useCallback(async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/admin/qa/questions", {
        params: {
          category_id: selectedCat || undefined,
          quality,
          q: debouncedQ || undefined,
          limit: 50,
          offset: 0,
        },
      });
      setItems(data.questions);
      setTotal(data.total);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Chargement questions impossible");
    } finally {
      setBusy(false);
    }
  }, [selectedCat, quality, debouncedQ]);

  // Debounce the search input (400ms) to avoid spamming the API
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(searchQ.trim()), 400);
    return () => clearTimeout(t);
  }, [searchQ]);

  useEffect(() => { loadSummary(); loadJobs(); loadQueue(); }, [loadSummary, loadJobs, loadQueue]);
  useEffect(() => { loadItems(); }, [loadItems]);
  // Reset selection quand les items visibles changent (filtre/search/catégorie)
  useEffect(() => { setSelected(new Set()); }, [selectedCat, quality, debouncedQ]);

  // Auto-refresh jobs + queue + summary while a job is running or queued
  useEffect(() => {
    const anyActive = jobs.some((j) => j.status === "running") || (queue?.queued_count ?? 0) > 0;
    if (!anyActive) return undefined;
    const iv = setInterval(() => { loadJobs(); loadQueue(); loadSummary(); }, 8000);
    return () => clearInterval(iv);
  }, [jobs, queue, loadJobs, loadQueue, loadSummary]);

  async function doAction(q, endpoint, extraBody = {}) {
    setActionOn(q.id);
    try {
      await api.post(`/admin/qa/${q.id}/${endpoint}`, { reason: "", ...extraBody });
      toast.success("OK ✓");
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

  async function cancelJob(jobId, categoryTitle) {
    if (!window.confirm(`Annuler le job en cours pour "${categoryTitle}" ?`)) return;
    try {
      const { data } = await api.post(`/admin/qa/jobs/${jobId}/cancel`);
      toast.success(data.was === "queued" ? "Job retiré de la file" : "Job en cours interrompu");
      loadJobs();
      loadQueue();
      loadSummary();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible d'annuler le job");
    }
  }

  async function rerunCategory(categoryId, categoryTitle) {
    if (!window.confirm(
      `Relancer le fact-check pour "${categoryTitle}" ?\n\n` +
      `Ceci va appeler Claude Opus 4.8 sur chaque question de la catégorie ` +
      `(~10 min, ~0,30€ de crédits Emergent LLM Key).`
    )) return;
    setRerunning(categoryId);
    try {
      const { data } = await api.post(`/admin/qa/rerun/${categoryId}`);
      toast.success(`Job démarré : ${data.job.id.slice(0, 8)}`);
      loadJobs();
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail;
      if (status === 409) toast.warning(msg || "Job déjà en cours");
      else toast.error(formatError(msg) || "Impossible de lancer le job");
    } finally {
      setRerunning(null);
    }
  }

  async function topupCategory(categoryId, categoryTitle, missing) {
    if (!window.confirm(
      `Compléter le parcours "${categoryTitle}" à 140 questions (7 paliers × 20) ?\n\n` +
      `Il manque ${missing} question(s). Chacune sera générée par Claude Sonnet puis ` +
      `vérifiée par Claude Opus 4.8. Coût estimé : ~${(missing * 0.03).toFixed(2)}€.`
    )) return;
    setRerunning(categoryId);
    try {
      const { data } = await api.post(`/admin/qa/topup/${categoryId}`);
      toast.success(`Top-up démarré : ${data.job.id.slice(0, 8)}`);
      loadJobs();
    } catch (e) {
      const status = e.response?.status;
      const msg = e.response?.data?.detail;
      if (status === 409) toast.warning(msg || "Job déjà en cours");
      else toast.error(formatError(msg) || "Impossible de lancer le top-up");
    } finally {
      setRerunning(null);
    }
  }

  // ---- Sélection multi + actions bulk ----
  function toggleSelect(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }
  function selectAllVisible() {
    setSelected(new Set(items.map((q) => q.id)));
  }
  function clearSelection() {
    setSelected(new Set());
  }

  async function bulkAction(endpoint, verbLabel) {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    const confirmMsg = endpoint === "delete"
      ? `Supprimer définitivement ${ids.length} question(s) ? Aucun retour arrière possible.`
      : `${verbLabel} ${ids.length} question(s) ?`;
    if (!window.confirm(confirmMsg)) return;
    setBulkBusy(true);
    try {
      const { data } = await api.post(`/admin/qa/bulk/${endpoint}`, { ids });
      const count = data.modified ?? data.deleted ?? 0;
      toast.success(`${count} question(s) traitée(s)`);
      setItems((prev) => prev.filter((q) => !selected.has(q.id)));
      setTotal((n) => n - count);
      clearSelection();
      loadSummary();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Action groupée impossible");
    } finally {
      setBulkBusy(false);
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

        {/* ==================== QUEUE ==================== */}
        {queue && (queue.running_count > 0 || queue.queued_count > 0) && (
          <section className="mb-8" data-testid="admin-qa-queue">
            <div className="bg-white border-2 border-terracotta/40 rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-display text-lg font-extrabold text-navy inline-flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-terracotta" /> File d&apos;attente
                </h2>
                <span className="text-xs text-navy/60">
                  {queue.running_count}/{queue.max_concurrent} en cours · {queue.queued_count} en attente
                </span>
              </div>
              <ul className="space-y-2">
                {queue.running.map((j) => (
                  <QueueRow key={j.id} job={j} kind="running" onCancel={cancelJob} />
                ))}
                {queue.queued.map((j) => (
                  <QueueRow key={j.id} job={j} kind="queued" onCancel={cancelJob} />
                ))}
              </ul>
            </div>
          </section>
        )}

        {/* ==================== SUMMARY ==================== */}
        <section className="mb-10" data-testid="admin-qa-summary">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-navy/60">Résumé par catégorie</h2>
            {jobs.some((j) => j.status === "running") && (
              <span className="inline-flex items-center gap-1 bg-terracotta/15 text-terracotta text-xs font-bold px-2.5 py-1 rounded-full" data-testid="admin-qa-jobs-running">
                <Loader2 className="w-3 h-3 animate-spin" /> {jobs.filter((j) => j.status === "running").length} audit(s) en cours
              </span>
            )}
          </div>
          {!summary ? (
            <div className="text-navy/50">Chargement…</div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {summary.map((s) => {
                const runningJob = jobs.find((j) => j.category_id === s.category_id && (j.status === "running" || j.status === "queued"));
                const isRunning = !!runningJob || rerunning === s.category_id;
                return (
                  <motion.div
                    key={s.category_id}
                    initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    className={`bg-white rounded-2xl border-2 p-4 transition ${
                      selectedCat === s.category_id
                        ? "border-terracotta shadow-warm"
                        : "border-cream-dark hover:border-navy/40"
                    }`}
                    data-testid={`admin-qa-cat-${s.category_id}`}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedCat(s.category_id === selectedCat ? "" : s.category_id)}
                      className="text-left w-full mb-2"
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

                      {/* Paliers 1..7 — barre 20 questions par palier */}
                      {s.paliers && (
                        <div className="mt-3 pt-3 border-t border-cream-dark" data-testid={`admin-qa-paliers-${s.category_id}`}>
                          <div className="flex items-center justify-between text-xs mb-1.5">
                            <span className="font-bold text-navy/70">Parcours (7 × 20 = 140)</span>
                            <span className={`font-bold ${s.missing_for_full_parcours === 0 ? "text-[#2A7350]" : "text-terracotta"}`}>
                              {s.missing_for_full_parcours === 0
                                ? "✓ complet"
                                : `manque ${s.missing_for_full_parcours}`}
                            </span>
                          </div>
                          <div className="flex gap-1">
                            {s.paliers.map((p) => {
                              const pct = Math.min(100, (p.count / p.target) * 100);
                              const full = p.count >= p.target;
                              return (
                                <div key={p.palier} className="flex-1" title={`Palier ${p.palier} : ${p.count}/${p.target}`}>
                                  <div className="h-6 rounded bg-cream-dark overflow-hidden relative">
                                    <div
                                      className={`h-full transition-all ${full ? "bg-[#3D9970]" : p.count === 0 ? "bg-cream" : "bg-mustard"}`}
                                      style={{ width: `${pct}%` }}
                                    />
                                    <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-navy">
                                      {p.palier}
                                    </div>
                                  </div>
                                  <div className="text-[9px] text-navy/50 text-center mt-0.5">{p.count}</div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </button>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); rerunCategory(s.category_id, s.category_title); }}
                        disabled={isRunning}
                        data-testid={`admin-qa-rerun-${s.category_id}`}
                        className="inline-flex items-center justify-center gap-1.5 bg-navy text-cream text-xs font-bold uppercase tracking-wider px-2 py-1.5 rounded-full hover:bg-navy-dark transition disabled:opacity-60"
                        title="Fact-check via Opus 4.8 + régénère les questions flaguées"
                      >
                        {isRunning ? (
                          <><Loader2 className="w-3.5 h-3.5 animate-spin" /> En cours…</>
                        ) : (
                          <><PlayCircle className="w-3.5 h-3.5" /> Régénérer</>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); topupCategory(s.category_id, s.category_title, s.missing_for_full_parcours); }}
                        disabled={isRunning || s.missing_for_full_parcours === 0}
                        data-testid={`admin-qa-topup-${s.category_id}`}
                        className="inline-flex items-center justify-center gap-1.5 bg-terracotta text-white text-xs font-bold uppercase tracking-wider px-2 py-1.5 rounded-full hover:bg-terracotta-dark transition disabled:opacity-40 disabled:cursor-not-allowed"
                        title="Génère les questions manquantes (Sonnet + Opus fact-check)"
                      >
                        {s.missing_for_full_parcours === 0 ? (
                          <><Check className="w-3.5 h-3.5" /> Complet</>
                        ) : (
                          <><Wand2 className="w-3.5 h-3.5" /> Compléter à 140</>
                        )}
                      </button>
                    </div>
                    {runningJob && (runningJob.status === "running" || runningJob.status === "queued") && (
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); cancelJob(runningJob.id, s.category_title); }}
                        data-testid={`admin-qa-cancel-${s.category_id}`}
                        className="mt-2 w-full inline-flex items-center justify-center gap-1.5 bg-white border-2 border-bordeaux text-bordeaux text-xs font-bold uppercase tracking-wider px-2 py-1.5 rounded-full hover:bg-bordeaux hover:text-white transition"
                      >
                        <X className="w-3.5 h-3.5" />
                        {runningJob.status === "queued" ? "Retirer de la file" : "Annuler"}
                      </button>
                    )}
                    {runningJob?.log_tail && (
                      <pre className="mt-2 bg-cream text-[10px] font-mono text-navy/70 rounded-md p-2 max-h-20 overflow-y-auto whitespace-pre-wrap">
                        {runningJob.log_tail}
                      </pre>
                    )}
                  </motion.div>
                );
              })}
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
            <div className="relative flex-1 min-w-[220px]">
              <Search className="w-4 h-4 text-navy/40 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="Chercher un mot-clé (question, option, commentaire)…"
                data-testid="admin-qa-search"
                className="w-full pl-9 pr-9 py-1.5 rounded-full border-2 border-cream-dark focus:border-terracotta focus:outline-none text-sm bg-white"
              />
              {searchQ && (
                <button
                  type="button"
                  onClick={() => setSearchQ("")}
                  data-testid="admin-qa-search-clear"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-navy/40 hover:text-navy p-1"
                  aria-label="Effacer la recherche"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
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
              onClick={() => { loadSummary(); loadItems(); loadJobs(); }}
              className="inline-flex items-center gap-1 text-sm text-navy hover:text-terracotta font-semibold"
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
            <>
              {/* Select all + bulk actions bar */}
              <div className="flex items-center gap-2 mb-3 px-2">
                <button
                  type="button"
                  onClick={selected.size === items.length ? clearSelection : selectAllVisible}
                  data-testid="admin-qa-select-all"
                  className="inline-flex items-center gap-1.5 text-sm text-navy/70 hover:text-terracotta font-semibold"
                >
                  {selected.size === items.length && items.length > 0
                    ? <CheckSquare className="w-4 h-4 text-terracotta" />
                    : <Square className="w-4 h-4" />}
                  {selected.size === items.length && items.length > 0
                    ? "Tout désélectionner"
                    : `Tout sélectionner (${items.length})`}
                </button>
              </div>

              <div className="space-y-3" data-testid="admin-qa-list">
                {items.map((q) => (
                  <QuestionCard
                    key={q.id}
                    q={q}
                    actionOn={actionOn}
                    onAction={doAction}
                    onDelete={doDelete}
                    isSelected={selected.has(q.id)}
                    onToggleSelect={toggleSelect}
                  />
                ))}
              </div>
            </>
          )}

          {/* Sticky bulk action bar */}
          {selected.size > 0 && (
            <motion.div
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-navy text-cream rounded-full shadow-2xl px-5 py-3 flex items-center gap-3 z-40 border-2 border-terracotta"
              data-testid="admin-qa-bulk-bar"
            >
              <span className="font-bold" data-testid="admin-qa-bulk-count">
                {selected.size} sélectionnée{selected.size > 1 ? "s" : ""}
              </span>
              <div className="h-6 w-px bg-cream/30" />
              <button
                type="button"
                onClick={() => bulkAction("approve", "Approuver")}
                disabled={bulkBusy}
                data-testid="admin-qa-bulk-approve"
                className="inline-flex items-center gap-1.5 bg-[#3D9970] hover:bg-[#2A7350] font-bold px-3 py-1.5 rounded-full transition disabled:opacity-50 text-sm"
              >
                {bulkBusy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                Approuver
              </button>
              {quality !== "flagged" && (
                <button
                  type="button"
                  onClick={() => bulkAction("flag", "Flagger")}
                  disabled={bulkBusy}
                  data-testid="admin-qa-bulk-flag"
                  className="inline-flex items-center gap-1.5 bg-mustard-dark hover:opacity-90 font-bold px-3 py-1.5 rounded-full transition disabled:opacity-50 text-sm"
                >
                  <X className="w-3.5 h-3.5" /> Flagger
                </button>
              )}
              <button
                type="button"
                onClick={() => bulkAction("delete", "Supprimer")}
                disabled={bulkBusy}
                data-testid="admin-qa-bulk-delete"
                className="inline-flex items-center gap-1.5 bg-terracotta hover:bg-terracotta-dark font-bold px-3 py-1.5 rounded-full transition disabled:opacity-50 text-sm"
              >
                <Trash2 className="w-3.5 h-3.5" /> Supprimer
              </button>
              <button
                type="button"
                onClick={clearSelection}
                data-testid="admin-qa-bulk-clear"
                className="text-cream/70 hover:text-cream text-sm ml-1"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}

function QuestionCard({ q, actionOn, onAction, onDelete, isSelected, onToggleSelect }) {
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
      className={`bg-white rounded-2xl border-2 p-4 transition ${
        isSelected ? "border-terracotta ring-2 ring-terracotta/20 shadow-warm" : "border-cream-dark"
      }`}
      data-testid={`admin-qa-item-${q.id}`}
    >
      <div className="flex items-start gap-3 mb-2">
        <button
          type="button"
          onClick={() => onToggleSelect?.(q.id)}
          data-testid={`admin-qa-select-${q.id}`}
          className="mt-0.5 p-1 hover:bg-cream rounded transition"
          aria-label={isSelected ? "Désélectionner" : "Sélectionner"}
        >
          {isSelected
            ? <CheckSquare className="w-5 h-5 text-terracotta" />
            : <Square className="w-5 h-5 text-navy/40" />}
        </button>
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

function fmtDur(sec) {
  if (sec == null || sec <= 0) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  if (m === 0) return `${s}s`;
  return `${m}min${s > 0 ? ` ${s}s` : ""}`;
}

function QueueRow({ job, kind, onCancel }) {
  const isRunning = kind === "running";
  return (
    <li
      data-testid={`admin-qa-queue-${kind}-${job.category_id}`}
      className={`flex items-center gap-3 p-3 rounded-xl border-2 ${
        isRunning ? "bg-terracotta/5 border-terracotta/30" : "bg-cream border-cream-dark"
      }`}
    >
      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold shrink-0 ${
        isRunning ? "bg-terracotta text-white" : "bg-navy/10 text-navy/70"
      }`}>
        {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : job.position}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-bold text-navy truncate">
          {job.category_title || job.category_id}
          <span className="ml-2 text-[10px] uppercase font-bold tracking-widest text-navy/50">
            {job.kind}
          </span>
        </div>
        <div className="text-xs text-navy/60">
          {isRunning ? (
            <>
              en cours depuis <strong>{fmtDur(job.elapsed_sec)}</strong>
              {" · fin estimée dans "}<strong>{fmtDur(job.remaining_sec)}</strong>
            </>
          ) : (
            <>
              position {job.position} · démarrage estimé dans <strong>{fmtDur(job.wait_before_start_sec)}</strong>
              {" · durée typique "}<strong>{fmtDur(job.expected_sec)}</strong>
            </>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={() => onCancel(job.id, job.category_title || job.category_id)}
        data-testid={`admin-qa-queue-cancel-${job.id}`}
        className="inline-flex items-center gap-1 bg-white border-2 border-bordeaux text-bordeaux text-xs font-bold px-3 py-1.5 rounded-full hover:bg-bordeaux hover:text-white transition"
      >
        <X className="w-3.5 h-3.5" /> Annuler
      </button>
    </li>
  );
}

