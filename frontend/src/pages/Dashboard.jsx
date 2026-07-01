import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import StreakSaverModal from "@/components/StreakSaverModal";
import { ArrowRight, Crown, Trophy, Target, Zap, Sparkles, Calendar, Flame } from "lucide-react";

/**
 * Returns true if the user's streak is "at risk" — they had a streak of ≥2,
 * their last play was the day before yesterday (Paris-aware via local-date
 * approximation), and they haven't played today. Matches the server-side
 * eligibility check in POST /api/gamification/streak-saver.
 */
function streakAtRisk(user) {
  if (!user) return false;
  if ((user.streak_current || 0) < 2) return false;
  const last = user.streak_last_date;
  if (!last) return false;
  // Compute "day before yesterday" YYYY-MM-DD in browser local time.
  // Server canonical TZ is Europe/Paris — close enough for the trigger heuristic.
  const dby = new Date();
  dby.setDate(dby.getDate() - 2);
  const key = dby.toISOString().slice(0, 10);
  return last === key;
}

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [daily, setDaily] = useState(null);
  const [showSaver, setShowSaver] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data)).catch(() => {});
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {});
    api.get("/attempts").then((r) => setAttempts(r.data || [])).catch(() => {});
    api.get("/daily/leaderboard").then((r) => setDaily(r.data)).catch(() => {});
  }, []);

  // Auto-open the streak saver when the criteria matches and the user
  // hasn't manually dismissed it this session.
  useEffect(() => {
    if (!dismissed && streakAtRisk(user)) {
      setShowSaver(true);
    }
  }, [user, dismissed]);

  const handleSaved = async () => {
    await refresh();
    setShowSaver(false);
  };
  const handleClose = () => {
    setShowSaver(false);
    setDismissed(true);  // Don't auto-reopen for this session
  };

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
                <div className="flex flex-wrap gap-3">
                  <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-4 py-2 rounded-full">
                    <Crown className="w-5 h-5" /> Membre Premium
                  </div>
                  <Link
                    to="/app/challenges/new"
                    data-testid="dashboard-new-challenge"
                    className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-5 py-2 rounded-full shadow-warm transition"
                  >
                    Lancer un défi famille <ArrowRight className="w-4 h-4" />
                  </Link>
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

        {/* Quiz du Jour widget with streak */}
        <div className="mb-10 bg-gradient-to-br from-bordeaux to-navy text-white rounded-[28px] p-6 md:p-8 border-4 border-mustard shadow-warm" data-testid="dashboard-daily-widget">
          <div className="flex flex-col md:flex-row items-start md:items-center gap-5">
            <div className="bg-mustard text-navy rounded-2xl p-3 shrink-0">
              <Calendar className="w-8 h-8" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                <span className="text-mustard font-bold tracking-wide uppercase text-xs">Quiz du Jour</span>
                {user?.streak_current > 0 && (
                  <span
                    data-testid="dashboard-streak-badge"
                    className="inline-flex items-center gap-1.5 bg-terracotta text-white font-bold px-3 py-1 rounded-full text-xs"
                    title={`Meilleure série : ${user.streak_best} jours`}
                  >
                    <Flame className="w-3.5 h-3.5" fill="currentColor" /> {user.streak_current} jour{user.streak_current > 1 ? "s" : ""} d&apos;affilée
                  </span>
                )}
              </div>
              <h3 className="font-display text-2xl md:text-3xl font-extrabold mb-1.5">
                {daily?.my_entry
                  ? `Score du jour : ${daily.my_entry.score}/${daily.my_entry.total} (rang #${daily.my_rank})`
                  : "5 questions, 1 classement, 0 excuse !"}
              </h3>
              <p className="text-cream/80 text-base">
                {daily?.my_entry
                  ? `${daily.total_players} joueur${daily.total_players > 1 ? "s ont" : " a"} déjà joué aujourd'hui. Revenez demain pour de nouvelles questions !`
                  : (user?.streak_current >= 2
                      ? `Ne cassez pas votre série de ${user.streak_current} jours !`
                      : "Jouez le Quiz du Jour et lancez votre série quotidienne.")}
              </p>
            </div>
            <Link
              to="/quiz-du-jour"
              data-testid="dashboard-daily-cta"
              className="inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold px-6 py-3 rounded-full transition shrink-0"
            >
              {daily?.my_entry ? "Voir le classement" : "Jouer maintenant"} <ArrowRight className="w-4 h-4" />
            </Link>
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

      {showSaver && (
        <StreakSaverModal user={user} onClose={handleClose} onSaved={handleSaved} />
      )}

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
