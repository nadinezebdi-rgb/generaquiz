import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Feather, Loader2, BookOpen, ArrowLeft } from "lucide-react";

/**
 * AtelierEntries — the user's private "carnet de souvenirs".
 * Sessions grouped by date, most recent first. Read-only for MVP.
 */
export default function AtelierEntries() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/atelier/entries").then((r) => setSessions(r.data)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <Link
          to="/app/atelier"
          data-testid="atelier-entries-back"
          className="inline-flex items-center gap-1 text-navy/70 hover:text-navy font-bold text-sm mb-4"
        >
          <ArrowLeft className="w-4 h-4" /> Nouvel atelier
        </Link>
        <h1 className="font-display text-4xl font-extrabold text-navy mb-2" data-testid="atelier-entries-title">
          Mon carnet de <span className="text-terracotta italic">souvenirs</span>
        </h1>
        <p className="text-navy/70 mb-6">
          Chaque atelier terminé est ici, dans l&apos;ordre où vous l&apos;avez écrit.
        </p>

        {loading && (
          <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-terracotta" /></div>
        )}

        {!loading && sessions.length === 0 && (
          <div className="bg-white border-2 border-cream-dark rounded-[24px] p-8 text-center" data-testid="atelier-entries-empty">
            <div className="w-14 h-14 mx-auto rounded-full bg-terracotta/15 flex items-center justify-center mb-3">
              <Feather className="w-6 h-6 text-terracotta" />
            </div>
            <div className="font-display text-2xl font-extrabold text-navy mb-1">Votre carnet est encore vide.</div>
            <p className="text-navy/70 mb-4">Commencez par un premier atelier — 5 questions, quelques minutes.</p>
            <Link
              to="/app/atelier"
              className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-3 rounded-full transition"
            >
              <BookOpen className="w-4 h-4" /> Écrire un premier souvenir
            </Link>
          </div>
        )}

        <div className="space-y-4">
          {sessions.map((s, i) => (
            <motion.div
              key={s.session_id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              data-testid={`atelier-session-${s.session_id}`}
              className="bg-white border-2 border-cream-dark rounded-[24px] p-5 md:p-6"
            >
              <div className="flex items-center gap-3 mb-3 flex-wrap">
                <span className="text-3xl">{s.theme_emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-xl font-extrabold text-navy">{s.theme_label}</div>
                  <div className="text-xs text-navy/60">
                    {new Date(s.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
                  </div>
                </div>
                <span className="text-xs bg-terracotta/15 text-terracotta font-bold px-2 py-1 rounded-full">
                  {s.entries.length} souvenir(s)
                </span>
              </div>
              <div className="space-y-3 border-t border-cream-dark pt-3">
                {s.entries.map((e) => (
                  <div key={e.prompt_id}>
                    <div className="text-sm font-bold text-navy/70 mb-1">— {e.prompt_text}</div>
                    <div className="text-navy whitespace-pre-wrap">{e.answer}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}
