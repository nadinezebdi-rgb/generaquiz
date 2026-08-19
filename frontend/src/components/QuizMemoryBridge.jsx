import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { BookOpen, Send, Loader2, Check } from "lucide-react";
import { api, formatError } from "@/lib/api";

/**
 * QuizMemoryBridge — encart "💭 Ce moment vous rappelle un souvenir ?"
 *
 * Injecté sous le feedback d'une question de quiz quand celle-ci a un
 * `discussion_prompt`. Ouvre une petite zone de saisie. Sur envoi, crée
 * une entrée dans le Livre de Vie via /api/livre/from-quiz. La catégorie
 * du quiz est mappée automatiquement vers le bon chapitre côté backend.
 *
 * Non intrusive : entièrement fermable, aucun blocage du flow de quiz.
 */
export default function QuizMemoryBridge({ question, categorySlug }) {
  const [expanded, setExpanded] = useState(false);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null); // {chapter_label}

  if (!question?.discussion_prompt) return null;

  async function submit() {
    if (!text.trim()) return;
    setSaving(true);
    try {
      const { data } = await api.post("/livre/from-quiz", {
        quiz_question_id: question.id,
        category_slug: categorySlug,
        question_text: question.discussion_prompt,
        memory_text: text.trim(),
      });
      setSaved({ chapter_label: data.chapter_label });
      toast.success(`Ajouté à votre Livre de Vie · ${data.chapter_label}`);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Enregistrement impossible");
    } finally {
      setSaving(false);
    }
  }

  // Confirmation après enregistrement
  if (saved) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
        className="mt-4 bg-terracotta/10 border-l-4 border-terracotta rounded-r-lg p-3"
        data-testid="quiz-memory-bridge-saved"
      >
        <p className="text-sm font-bold text-terracotta uppercase tracking-wider flex items-center gap-1">
          <Check className="w-4 h-4" /> Souvenir ajouté à votre Livre de Vie
        </p>
        <p className="text-navy/80 text-sm mt-1">
          Chapitre : <strong>{saved.chapter_label}</strong>
        </p>
      </motion.div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      {!expanded ? (
        <motion.button
          key="collapsed"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          type="button"
          onClick={() => setExpanded(true)}
          data-testid="quiz-memory-bridge-open"
          className="mt-4 w-full flex items-center gap-3 bg-cream border-2 border-cream-dark hover:border-terracotta hover:bg-terracotta/5 transition rounded-2xl p-3 text-left"
        >
          <div className="bg-terracotta/20 text-terracotta rounded-xl w-11 h-11 flex items-center justify-center shrink-0">
            <BookOpen className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-terracotta uppercase tracking-wider mb-0.5">
              💭 Ce moment vous rappelle un souvenir ?
            </p>
            <p className="text-sm text-navy/80 truncate">
              Ajoutez-le à votre Livre de Vie
            </p>
          </div>
        </motion.button>
      ) : (
        <motion.div
          key="expanded"
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          className="mt-4 bg-white border-2 border-terracotta rounded-2xl p-4"
          data-testid="quiz-memory-bridge-form"
        >
          <p className="text-sm font-bold text-terracotta uppercase tracking-wider mb-2">
            💭 Votre souvenir
          </p>
          <p className="text-navy italic mb-3 text-sm">« {question.discussion_prompt} »</p>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            maxLength={4000}
            placeholder="Racontez-le en quelques phrases, à votre rythme…"
            autoFocus
            className="w-full bg-cream rounded-xl border-2 border-cream-dark focus:border-terracotta focus:outline-none p-3 text-navy resize-y text-base"
            data-testid="quiz-memory-bridge-textarea"
          />
          <div className="flex items-center justify-between gap-2 mt-3">
            <button
              type="button"
              onClick={() => { setExpanded(false); setText(""); }}
              className="text-sm text-navy/60 hover:text-navy font-semibold"
              data-testid="quiz-memory-bridge-cancel"
            >
              Pas maintenant
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={saving || !text.trim()}
              data-testid="quiz-memory-bridge-save"
              className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2.5 rounded-full hover:bg-terracotta-dark transition disabled:opacity-50 min-h-[44px]"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Ajouter à mon Livre
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
