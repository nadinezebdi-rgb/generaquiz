import { useState } from "react";
import { toast } from "sonner";
import { Sparkles, CheckCircle2, Loader2, Mail } from "lucide-react";
import { api, formatError } from "@/lib/api";

const TARGET = 140;
const FEATURED = "bien-vieillir";

export const FillThemesBanner = ({ summary, onLaunched }) => {
  const [busy, setBusy] = useState(false);
  const [sending, setSending] = useState(false);
  if (!summary) return null;

  const incomplete = summary
    .map((c) => ({ ...c, playable: TARGET - (c.missing_for_full_parcours ?? 0) }))
    .filter((c) => c.missing_for_full_parcours > 0)
    .sort((a, b) => (a.category_id === FEATURED ? -1 : b.category_id === FEATURED ? 1 : a.playable - b.playable));

  async function fillAll() {
    if (!window.confirm(
      `Remplir ${incomplete.length} thème(s) jusqu'à ${TARGET} questions ?\n\n` +
      `Ordre : reclassement du stock (0 IA) → vérification du stock existant → génération IA pour le reste. ` +
      `Consomme des crédits IA. 2 thèmes en parallèle, les autres en file.`
    )) return;
    setBusy(true);
    try {
      const { data } = await api.post("/admin/qa/auto-seed");
      const summary = `${data.launched} en cours · ${data.queued} en file · ${data.already_running} déjà en cours`;
      if (data.launched + data.queued === 0) toast.info(`Rien de nouveau à lancer : ${summary}`);
      else toast.success(`Remplissage lancé : ${summary}`);
      onLaunched?.();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Remplissage impossible");
    } finally {
      setBusy(false);
    }
  }

  async function sendReport() {
    setSending(true);
    try {
      const { data } = await api.post("/admin/qa/morning-report/send");
      if (data.sent > 0) toast.success(`Rapport envoyé à ${data.recipients.join(", ")}`);
      else toast.error(`Rapport non envoyé (${data.reason || "aucun destinataire"})`);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Envoi impossible");
    } finally {
      setSending(false);
    }
  }

  const reportBtn = (
    <button
      type="button"
      onClick={sendReport}
      disabled={sending}
      data-testid="admin-qa-send-report-btn"
      className="inline-flex items-center gap-2 bg-white border-2 border-navy/30 text-navy text-sm font-bold px-4 py-2 rounded-full hover:border-navy transition-colors disabled:opacity-60"
    >
      {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />} Recevoir le rapport du matin maintenant
    </button>
  );

  if (incomplete.length === 0) {
    return (
      <div data-testid="admin-qa-fill-banner" className="mb-6 flex items-center justify-between gap-3 flex-wrap bg-emerald-50 border-2 border-emerald-200 rounded-2xl p-4">
        <span className="inline-flex items-center gap-2 font-bold text-emerald-700" data-testid="admin-qa-fill-complete">
          <CheckCircle2 className="w-5 h-5" /> Tous les thèmes sont complets ({TARGET}/{TARGET})
        </span>
        {reportBtn}
      </div>
    );
  }

  return (
    <div data-testid="admin-qa-fill-banner" className="mb-6 bg-white border-2 border-[#6A994E]/50 rounded-2xl p-5 shadow-soft">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div className="min-w-0">
          <h2 className="font-display text-lg font-extrabold text-navy">
            {incomplete.length} thème{incomplete.length > 1 ? "s" : ""} à compléter
          </h2>
          <p className="text-sm text-navy/70">
            Un clic : stock existant reclassé d&apos;abord, puis vérifié par Claude Opus, et l&apos;IA ne génère que ce qui manque. Reprise automatique en cas de coupure. Compteur = questions jouables par palier.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {reportBtn}
          <button
            type="button"
            onClick={fillAll}
            disabled={busy}
            data-testid="admin-qa-fill-all-btn"
            className="inline-flex items-center gap-2 bg-[#6A994E] text-white text-sm font-bold px-5 py-2 rounded-full hover:bg-[#557d3e] shadow-warm transition-colors disabled:opacity-60"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Remplir à {TARGET}
          </button>
        </div>
      </div>
      <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {incomplete.map((c) => (
          <li key={c.category_id} data-testid={`admin-qa-fill-row-${c.category_id}`} className={`rounded-xl px-3 py-2 border ${c.category_id === FEATURED ? "border-[#6A994E] bg-[#6A994E]/10" : "border-cream-dark bg-cream/50"}`}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-bold text-navy truncate">{c.category_title}</span>
              <span className="tabular-nums text-navy/70 text-xs font-bold">{c.playable} / {TARGET}</span>
            </div>
            <div className="mt-1 h-1.5 bg-navy/10 rounded-full overflow-hidden">
              <div className="h-full bg-[#6A994E]" style={{ width: `${Math.round((c.playable / TARGET) * 100)}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
