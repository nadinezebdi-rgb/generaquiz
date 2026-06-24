import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import { ArrowLeft, Sparkles, Users, Loader2, Crown } from "lucide-react";

export default function ChallengeNew() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [categoryId, setCategoryId] = useState("");
  const [num, setNum] = useState(5);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
  }, []);

  if (user && user.plan !== "premium") {
    return (
      <div className="min-h-screen paper-bg">
        <Navbar variant="app" />
        <main className="max-w-2xl mx-auto px-4 py-16 text-center">
          <Crown className="w-16 h-16 text-mustard mx-auto mb-4" strokeWidth={2} />
          <h1 className="font-display text-3xl font-extrabold text-navy mb-3">Réservé aux Premium</h1>
          <p className="text-navy/70 text-lg mb-7">Le mode Défi Famille est inclus dans l'abonnement Premium.</p>
          <Link to="/app/pricing" className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm">
            Voir les tarifs
          </Link>
        </main>
      </div>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const { data } = await api.post("/challenges", { category_id: categoryId, num_questions: Number(num) });
      navigate(`/app/challenges/${data.token}`);
    } catch (e2) {
      setErr(e2.response?.data?.detail || "Erreur");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <Link to="/app/challenges" className="inline-flex items-center gap-2 text-navy hover:text-terracotta font-bold mb-6">
          <ArrowLeft className="w-5 h-5" /> Mes défis
        </Link>

        <div className="bg-white border-4 border-navy rounded-[32px] p-8 md:p-10 shadow-warm">
          <div className="flex items-center gap-3 mb-6">
            <span className="w-12 h-12 rounded-full bg-terracotta flex items-center justify-center">
              <Users className="w-6 h-6 text-white" strokeWidth={2.5} />
            </span>
            <div>
              <h1 className="font-display text-3xl font-extrabold text-navy">Nouveau défi famille</h1>
              <p className="text-navy/60">Choisissez le thème et le nombre de questions.</p>
            </div>
          </div>

          <form onSubmit={submit} className="space-y-6">
            <div>
              <label className="block font-bold text-navy mb-3 text-lg">Catégorie</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {categories.map((cat) => (
                  <button
                    type="button"
                    key={cat.id}
                    onClick={() => setCategoryId(cat.id)}
                    data-testid={`new-challenge-cat-${cat.id}`}
                    className={`flex items-center gap-3 p-4 rounded-2xl border-2 text-left transition ${
                      categoryId === cat.id
                        ? "bg-terracotta/10 border-terracotta"
                        : "bg-white border-cream-dark hover:border-terracotta/50"
                    }`}
                  >
                    {cat.mascot_image && (
                      <div className="w-12 h-12 rounded-xl overflow-hidden bg-cream border border-cream-dark shrink-0">
                        <img src={`${BACKEND_URL}${cat.mascot_image}`} alt="" className="w-full h-full object-cover" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-display text-lg font-bold text-navy truncate">{cat.title}</div>
                      <div className="text-xs text-navy/60">{cat.mascot_name}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block font-bold text-navy mb-3 text-lg">Nombre de questions</label>
              <div className="flex gap-3">
                {[3, 5, 7, 10].map((n) => (
                  <button
                    type="button"
                    key={n}
                    onClick={() => setNum(n)}
                    data-testid={`new-challenge-num-${n}`}
                    className={`flex-1 py-4 rounded-2xl border-2 font-display text-2xl font-extrabold transition ${
                      num === n
                        ? "bg-navy text-white border-navy"
                        : "bg-white text-navy border-cream-dark hover:border-navy/50"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            {err && (
              <div className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-navy font-medium" data-testid="new-challenge-error">
                {err}
              </div>
            )}

            <button
              type="submit"
              data-testid="new-challenge-submit"
              disabled={!categoryId || loading}
              className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-6 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-50 transition"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
              {loading ? "Création..." : "Créer le défi & obtenir le lien"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
