import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Flag, Trash2, Check, ArrowLeft, Loader2 } from "lucide-react";
import Logo from "@/components/Logo";
import { toast } from "sonner";

const REASON_LABELS = {
  factually_wrong: "Réponse incorrecte",
  ambiguous: "Ambiguë",
  duplicate: "Doublon",
  inappropriate: "Inapproprié",
  other: "Autre",
};

export default function AdminReports() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [status, setStatus] = useState("pending");

  useEffect(() => {
    if (user && user.role !== "admin") navigate("/app/dashboard");
  }, [user, navigate]);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get(`/admin/reports?status=${status}`);
      setItems(r.data.items || []);
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [status]);

  const resolve = async (qid, action) => {
    setBusyId(qid);
    try {
      await api.post(`/admin/reports/${qid}/resolve`, { action });
      toast.success(action === "delete" ? "Question supprimée — Mistral régénérera ce soir" : "Signalement écarté");
      await load();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Erreur");
    } finally {
      setBusyId(null);
    }
  };

  if (!user || user.role !== "admin") return null;

  return (
    <div className="min-h-screen paper-bg">
      <header className="bg-white border-b-2 border-cream-dark">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link to="/app/dashboard" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold">
            <ArrowLeft className="w-5 h-5" /> Tableau de bord
          </Link>
          <Logo size="sm" asLink={false} showTagline={false} />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="admin-reports-page">
        <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2 flex items-center gap-3">
          <Flag className="w-8 h-8 text-terracotta" />
          Questions signalées
        </h1>
        <p className="text-lg text-navy/70 mb-6">
          Revue des signalements faits par les joueurs. Supprimer une question libère un emplacement que Mistral remplira au prochain cycle nocturne (03:00 Paris).
        </p>

        <div className="flex gap-2 mb-6">
          {["pending", "resolved", "all"].map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              data-testid={`reports-tab-${s}`}
              className={`px-5 py-2 rounded-full font-bold transition ${
                status === s
                  ? "bg-navy text-white"
                  : "bg-white border-2 border-cream-dark text-navy hover:border-navy"
              }`}
            >
              {s === "pending" ? "En attente" : s === "resolved" ? "Traités" : "Tous"}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-20"><Loader2 className="w-8 h-8 mx-auto animate-spin text-navy" /></div>
        ) : items.length === 0 ? (
          <div className="bg-white border-2 border-cream-dark rounded-3xl p-12 text-center" data-testid="reports-empty">
            <Flag className="w-12 h-12 mx-auto text-navy/30 mb-3" />
            <p className="text-xl font-bold text-navy">Aucun signalement {status === "pending" ? "en attente" : ""} 🎉</p>
            <p className="text-navy/60 mt-2">Vos joueurs sont contents — ou personne n'a encore signalé.</p>
          </div>
        ) : (
          <ul className="space-y-4" data-testid="reports-list">
            {items.map((it) => (
              <li key={it.question_id} className="bg-white border-2 border-cream-dark rounded-3xl p-6">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="bg-terracotta text-white font-bold text-sm px-3 py-1 rounded-full">
                        {it.report_count} signalement{it.report_count > 1 ? "s" : ""}
                      </span>
                      <span className="bg-cream border-2 border-cream-dark text-navy font-semibold text-xs px-3 py-1 rounded-full">
                        {it.category_id}
                      </span>
                      {it.question_id.startsWith("m_") && (
                        <span className="bg-mustard/30 text-navy font-semibold text-xs px-3 py-1 rounded-full">🤖 Mistral</span>
                      )}
                      {!it.question && (
                        <span className="bg-red-100 text-red-800 font-semibold text-xs px-3 py-1 rounded-full">Déjà supprimée</span>
                      )}
                    </div>
                    <p className="font-display text-xl font-bold text-navy mb-2">{it.question_text}</p>
                    {it.question && (
                      <ul className="space-y-1 mb-2">
                        {it.question.options.map((opt, i) => (
                          <li key={i} className={`text-sm ${i === it.question.correct_index ? "font-bold text-[#3D9970]" : "text-navy/70"}`}>
                            {String.fromCharCode(65 + i)}. {opt} {i === it.question.correct_index && "✓"}
                          </li>
                        ))}
                      </ul>
                    )}
                    <div className="flex flex-wrap gap-2 mt-2">
                      {Array.from(new Set(it.reasons)).map((r) => (
                        <span key={r} className="text-xs bg-cream px-2 py-1 rounded-full text-navy/70">
                          {REASON_LABELS[r] || r} ({it.reasons.filter((x) => x === r).length})
                        </span>
                      ))}
                    </div>
                    {it.comments.length > 0 && (
                      <details className="mt-2">
                        <summary className="text-sm text-navy/60 cursor-pointer hover:text-navy">Voir {it.comments.length} commentaire{it.comments.length > 1 ? "s" : ""}</summary>
                        <ul className="mt-2 space-y-1 pl-4">
                          {it.comments.map((c, i) => <li key={i} className="text-sm text-navy/70 italic">"{c}"</li>)}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
                {status === "pending" && (
                  <div className="flex gap-2 pt-3 border-t border-cream-dark">
                    {it.question && (
                      <button
                        onClick={() => resolve(it.question_id, "delete")}
                        disabled={busyId === it.question_id}
                        data-testid={`report-delete-${it.question_id}`}
                        className="inline-flex items-center gap-2 bg-[#D9534F] hover:bg-[#B73B37] disabled:opacity-50 text-white font-bold px-5 py-2 rounded-full transition"
                      >
                        <Trash2 className="w-4 h-4" /> Supprimer la question
                      </button>
                    )}
                    <button
                      onClick={() => resolve(it.question_id, "dismiss")}
                      disabled={busyId === it.question_id}
                      data-testid={`report-dismiss-${it.question_id}`}
                      className="inline-flex items-center gap-2 bg-white border-2 border-navy hover:bg-navy hover:text-white text-navy font-bold px-5 py-2 rounded-full transition"
                    >
                      <Check className="w-4 h-4" /> Écarter
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
