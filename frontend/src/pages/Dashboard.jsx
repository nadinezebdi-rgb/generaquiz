import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ArrowRight, Crown, Trophy, Target, Zap, Sparkles } from "lucide-react";

export default function Dashboard() {
  const { user } = useAuth();
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState(null);
  const [attempts, setAttempts] = useState([]);

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/attempts").then((r) => setAttempts(r.data || [])).catch(() => {});
  }, []);

  const isPremium = user?.plan === "premium";

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header */}
        <div className="bg-gradient-to-br from-navy to-navy-dark text-white rounded-[32px] p-8 md:p-12 mb-10 relative overflow-hidden border-4 border-mustard">
          <div className="absolute -top-12 -right-12 w-72 h-72 rounded-full bg-mustard/20 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-16 -left-16 w-64 h-64 rounded-full bg-terracotta/30 blur-3xl pointer-events-none" />
          <div className="relative grid md:grid-cols-3 gap-6 items-center">
            <div className="md:col-span-2">
              <p className="text-mustard font-bold tracking-wide uppercase text-sm mb-2">
                Bonjour {user?.name || ""} !
              </p>
              <h1 className="font-display text-4xl md:text-5xl font-extrabold mb-4 leading-tight">
                Prêt(e) pour un nouveau quiz ?
              </h1>
              <p className="text-cream/80 text-lg max-w-xl mb-5">
                Choisissez une catégorie ci-dessous et laissez-vous guider par nos six personnages caricaturés.
              </p>
              {!isPremium && (
                <Link
                  to="/app/pricing"
                  data-testid="dashboard-upgrade-cta"
                  className="inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold px-6 py-3 rounded-full transition"
                >
                  <Crown className="w-5 h-5" /> Passer en Premium
                </Link>
              )}
              {isPremium && (
                <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-2 rounded-full">
                  <Crown className="w-5 h-5" /> Membre Premium
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-3">
              <StatBox icon={Trophy} label="Quiz joués" value={stats?.quizzes_played ?? 0} />
              <StatBox icon={Target} label="Précision" value={`${stats?.accuracy_pct ?? 0}%`} />
              <StatBox icon={Zap} label="Bonnes" value={stats?.correct_answers ?? 0} />
            </div>
          </div>
        </div>

        {/* Categories grid */}
        <div className="mb-12">
          <div className="flex items-end justify-between mb-6">
            <h2 className="font-display text-3xl font-extrabold text-navy">Mes catégories</h2>
            <span className="text-navy/60 font-medium">{categories.length} disponibles</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((cat, idx) => (
              <motion.div
                key={cat.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="group bg-white border-2 border-cream-dark rounded-[28px] p-6 hover:border-terracotta hover:-translate-y-1 transition-all shadow-soft hover:shadow-warm relative overflow-hidden"
                data-testid={`dashboard-category-${cat.id}`}
              >
                <div
                  className="absolute -top-12 -right-12 w-48 h-48 rounded-full opacity-15 group-hover:opacity-30 transition"
                  style={{ backgroundColor: cat.color }}
                />
                <div className="relative flex items-start gap-4">
                  <div className="w-24 h-24 shrink-0 rounded-2xl overflow-hidden bg-cream border-2 border-cream-dark">
                    <img src={`${BACKEND_URL}${cat.mascot_image}`} alt={cat.mascot_name} className="w-full h-full object-cover" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-display text-xl font-bold text-navy">{cat.title}</h3>
                    <p className="text-sm text-navy/60 mb-2">avec {cat.mascot_name}</p>
                    <p className="text-navy/80 text-base line-clamp-2">{cat.description}</p>
                  </div>
                </div>
                <div className="relative mt-5 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-navy/60">
                    {cat.count} questions
                  </span>
                  <Link
                    to={`/app/quiz/${cat.id}`}
                    data-testid={`dashboard-play-${cat.id}`}
                    className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-2.5 rounded-full transition shadow-warm"
                  >
                    Jouer <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Recent attempts */}
        <div className="bg-white border-2 border-cream-dark rounded-[28px] p-8">
          <h2 className="font-display text-2xl font-extrabold text-navy mb-5 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-terracotta" /> Mes dernières parties
          </h2>
          {attempts.length === 0 ? (
            <p className="text-navy/60 text-lg">Aucune partie jouée pour le moment. Lancez votre premier quiz ci-dessus !</p>
          ) : (
            <div className="divide-y-2 divide-cream-dark">
              {attempts.slice(0, 10).map((a, i) => {
                const cat = categories.find((c) => c.id === a.category_id);
                const pct = a.total ? Math.round((a.score / a.total) * 100) : 0;
                return (
                  <div key={i} className="py-4 flex items-center justify-between" data-testid={`attempt-row-${i}`}>
                    <div className="flex items-center gap-4">
                      {cat && (
                        <div className="w-12 h-12 rounded-xl overflow-hidden bg-cream border border-cream-dark">
                          <img src={`${BACKEND_URL}${cat.mascot_image}`} alt="" className="w-full h-full object-cover" />
                        </div>
                      )}
                      <div>
                        <div className="font-display text-lg font-bold text-navy">{cat?.title || a.category_id}</div>
                        <div className="text-sm text-navy/60">{new Date(a.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-display text-2xl font-extrabold text-bordeaux">{a.score}/{a.total}</div>
                      <div className="text-sm text-navy/60">{pct}%</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

function StatBox({ icon: Icon, label, value }) {
  return (
    <div className="bg-white/10 backdrop-blur-sm border-2 border-white/20 rounded-2xl p-4 text-center">
      <Icon className="w-6 h-6 mx-auto text-mustard mb-1" strokeWidth={2.5} />
      <div className="font-display text-3xl font-extrabold">{value}</div>
      <div className="text-xs uppercase tracking-wider text-cream/70 mt-1">{label}</div>
    </div>
  );
}
