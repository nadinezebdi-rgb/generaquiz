import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { X, Sparkles, Loader2, Heart, Pencil, RefreshCw, Send } from "lucide-react";
import { api } from "@/lib/api";
import { formatError } from "@/lib/api";

/**
 * RewriteAssistantModal — assistance IA respectueuse.
 *
 * L'utilisateur voit son texte source et une proposition reformulée.
 * Il choisit :
 *  - ❤️  Ça me ressemble : la version reformulée remplace l'originale
 *  - ✏️  Modifier : édite manuellement la proposition puis accepte
 *  - 🔄  Reformuler autrement : relance avec un ton "warmer" ou "concise"
 *  - ✖️  Fermer : ne rien enregistrer, texte original inchangé
 *
 * Aucune inventivité : garde-fous appliqués côté serveur (voir livre_ai.py).
 */
export default function RewriteAssistantModal({ entry, onClose, onAccepted }) {
  const [tone, setTone] = useState("natural");
  const [proposal, setProposal] = useState("");
  const [editable, setEditable] = useState("");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  async function fetchRewrite(nextTone = tone) {
    setBusy(true);
    try {
      const { data } = await api.post(`/livre/entries/${entry.id}/rewrite`, {
        entry_id: entry.id, tone: nextTone,
      });
      setProposal(data.rewritten);
      setEditable(data.rewritten);
      setTone(nextTone);
      setEditing(false);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Reformulation indisponible");
    } finally {
      setBusy(false);
    }
  }

  async function acceptRewrite(finalText) {
    setSaving(true);
    try {
      await api.post(`/livre/entries/${entry.id}/accept-rewrite`, { text: finalText });
      toast.success("Souvenir mis à jour ✨");
      onAccepted?.(finalText);
      onClose?.();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Enregistrement impossible");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[60] bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95 }}
          className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
          onClick={(e) => e.stopPropagation()}
          data-testid="rewrite-assistant-modal"
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b-2 border-cream-dark p-5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-terracotta" />
              <h2 className="font-display text-2xl font-extrabold text-navy">Assistance à la rédaction</h2>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-cream-dark rounded-full transition" data-testid="rewrite-close">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-5 space-y-5">
            {/* Votre texte */}
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-navy/60 mb-2">Votre texte</div>
              <div className="bg-cream rounded-2xl border-2 border-cream-dark p-4 text-navy whitespace-pre-wrap" data-testid="rewrite-original">
                {entry.text}
              </div>
            </div>

            {!proposal && (
              <div className="text-center py-4">
                <p className="text-navy/70 mb-4">
                  GénéraQuiz peut relire votre souvenir et corriger l&apos;orthographe, la ponctuation et les tournures.
                  <br />
                  <strong className="text-navy">Rien ne sera ajouté ni inventé.</strong> Votre histoire reste la vôtre.
                </p>
                <button
                  type="button"
                  onClick={() => fetchRewrite("natural")}
                  disabled={busy}
                  data-testid="rewrite-start"
                  className="inline-flex items-center gap-2 bg-terracotta text-white font-bold text-lg px-6 py-3 rounded-full hover:bg-terracotta-dark transition disabled:opacity-50 min-h-[52px]"
                >
                  {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                  {busy ? "Reformulation en cours…" : "Reformuler joliment"}
                </button>
              </div>
            )}

            {/* Proposition */}
            {proposal && (
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-terracotta mb-2 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Voici comment votre souvenir pourrait apparaître dans votre Livre de Vie :
                </div>
                {editing ? (
                  <textarea
                    value={editable}
                    onChange={(e) => setEditable(e.target.value)}
                    rows={7}
                    maxLength={8000}
                    className="w-full bg-cream rounded-2xl border-2 border-terracotta p-4 text-navy focus:outline-none resize-y"
                    data-testid="rewrite-edit-textarea"
                    autoFocus
                  />
                ) : (
                  <div
                    className="bg-terracotta/10 rounded-2xl border-2 border-terracotta/40 p-4 text-navy whitespace-pre-wrap"
                    data-testid="rewrite-proposal"
                  >
                    {editable}
                  </div>
                )}

                {/* Actions */}
                <div className="grid sm:grid-cols-3 gap-2 mt-4">
                  <button
                    type="button"
                    onClick={() => acceptRewrite(editable)}
                    disabled={saving || busy || !editable.trim()}
                    data-testid="rewrite-accept"
                    className="inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-4 py-3 rounded-full hover:bg-terracotta-dark transition disabled:opacity-50 min-h-[52px]"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Heart className="w-4 h-4" />}
                    Ça me ressemble
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing((v) => !v)}
                    disabled={saving || busy}
                    data-testid="rewrite-toggle-edit"
                    className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy text-navy font-bold px-4 py-3 rounded-full hover:bg-navy hover:text-cream transition disabled:opacity-50 min-h-[52px]"
                  >
                    <Pencil className="w-4 h-4" />
                    {editing ? "Voir aperçu" : "Modifier"}
                  </button>
                  <button
                    type="button"
                    onClick={() => fetchRewrite(tone === "warmer" ? "concise" : "warmer")}
                    disabled={busy || saving}
                    data-testid="rewrite-again"
                    className="inline-flex items-center justify-center gap-2 bg-cream text-navy border-2 border-cream-dark font-bold px-4 py-3 rounded-full hover:bg-cream-dark transition disabled:opacity-50 min-h-[52px]"
                  >
                    {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Autrement
                  </button>
                </div>
                <p className="text-xs text-navy/50 mt-3 text-center">
                  {tone === "natural" && "Ton actuel : naturel"}
                  {tone === "warmer" && "Ton actuel : plus chaleureux"}
                  {tone === "concise" && "Ton actuel : plus concis"}
                  {" · "}L&apos;IA ne peut ni inventer ni supprimer un souvenir. Votre texte original est toujours conservé.
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
