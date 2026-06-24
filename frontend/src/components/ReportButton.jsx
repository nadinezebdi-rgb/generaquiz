/**
 * Composant bouton "Signaler cette question" — discret, ouvre un mini-modal avec choix de raison.
 * Utilisé sur QuizPlayer, ChallengePlay (premium uniquement) et DailyQuiz.
 */
import { useState } from "react";
import { Flag, X } from "lucide-react";
import { api, formatError } from "@/lib/api";
import { toast } from "sonner";

const REASONS = [
  { value: "factually_wrong", label: "Réponse incorrecte" },
  { value: "ambiguous", label: "Question ambiguë / plusieurs bonnes réponses" },
  { value: "duplicate", label: "Question en double" },
  { value: "inappropriate", label: "Contenu inapproprié" },
  { value: "other", label: "Autre" },
];

export default function ReportButton({ questionId, disabled = false }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("factually_wrong");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  if (!questionId) return null;

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/quiz/report", { question_id: questionId, reason, comment });
      toast.success("Merci, votre signalement a été pris en compte !");
      setOpen(false);
      setComment("");
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur lors de l'envoi");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        data-testid="question-report-btn"
        className="inline-flex items-center gap-1.5 text-sm text-navy/50 hover:text-terracotta transition disabled:opacity-40"
        title="Signaler un problème avec cette question"
      >
        <Flag className="w-4 h-4" />
        Signaler
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={() => !busy && setOpen(false)}>
          <div
            data-testid="report-modal"
            className="bg-white border-4 border-navy rounded-3xl p-6 md:p-8 max-w-md w-full shadow-warm"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between mb-5">
              <h3 className="font-display text-2xl font-extrabold text-navy">Signaler cette question</h3>
              <button onClick={() => !busy && setOpen(false)} className="p-1 hover:bg-cream rounded-full" aria-label="Fermer">
                <X className="w-5 h-5 text-navy/60" />
              </button>
            </div>
            <p className="text-base text-navy/70 mb-5">
              Aidez-nous à améliorer GénéraQuiz en nous indiquant ce qui ne va pas avec cette question.
            </p>
            <div className="space-y-2 mb-5">
              {REASONS.map((r) => (
                <label
                  key={r.value}
                  className={`flex items-center gap-3 p-3 rounded-xl border-2 cursor-pointer transition ${
                    reason === r.value ? "border-terracotta bg-terracotta/5" : "border-cream-dark hover:border-navy/30"
                  }`}
                >
                  <input
                    type="radio"
                    name="reason"
                    value={r.value}
                    checked={reason === r.value}
                    onChange={(e) => setReason(e.target.value)}
                    className="accent-terracotta"
                    data-testid={`report-reason-${r.value}`}
                  />
                  <span className="font-medium text-navy">{r.label}</span>
                </label>
              ))}
            </div>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Commentaire (facultatif)"
              maxLength={500}
              data-testid="report-comment"
              className="w-full p-3 border-2 border-cream-dark rounded-xl resize-none focus:border-navy focus:outline-none text-base"
              rows={3}
            />
            <div className="flex flex-col-reverse sm:flex-row gap-3 mt-5">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-cream border-2 border-cream-dark hover:border-navy text-navy font-bold px-5 py-3 rounded-full transition disabled:opacity-50"
              >
                Annuler
              </button>
              <button
                onClick={submit}
                disabled={busy}
                data-testid="report-submit-btn"
                className="flex-1 inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full shadow-warm transition disabled:opacity-60"
              >
                {busy ? "Envoi…" : "Envoyer le signalement"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
