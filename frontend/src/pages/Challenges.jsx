import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api, BACKEND_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Plus, Users, Crown, ArrowRight, Trophy, Clock, Share2 } from "lucide-react";

export default function Challenges() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/challenges/mine").then((r) => setItems(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const isPremium = user?.plan === "premium";

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <div className="inline-flex items-center gap-2 bg-mustard text-navy font-bold px-3 py-1 rounded-full text-sm mb-3">
              <Users className="w-4 h-4" /> Défi Famille
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">
              Vos défis en cours
            </h1>
            <p className="text-lg text-navy/70 max-w-2xl">
              Créez un quiz, partagez le lien à vos petits-enfants par message ou email,
              et comparez les scores en direct.
            </p>
          </div>
          {isPremium ? (
            <Link
              to="/app/challenges/new"
              data-testid="challenges-new-btn"
              className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-4 rounded-full shadow-warm transition self-start md:self-auto"
            >
              <Plus className="w-5 h-5" /> Nouveau défi
            </Link>
          ) : (
            <Link
              to="/app/pricing"
              data-testid="challenges-upgrade-cta"
              className="inline-flex items-center gap-2 bg-mustard hover:bg-mustard-dark text-navy font-bold px-6 py-4 rounded-full transition"
            >
              <Crown className="w-5 h-5" /> Débloquer avec Premium
            </Link>
          )}
        </div>

        {!isPremium && (
          <div className="bg-mustard/25 border-2 border-mustard-dark rounded-3xl p-6 md:p-8 mb-8" data-testid="challenges-locked">
            <div className="flex flex-col md:flex-row items-start gap-5">
              <div className="w-14 h-14 rounded-2xl bg-mustard flex items-center justify-center shrink-0">
                <Crown className="w-7 h-7 text-navy" strokeWidth={2.5} />
              </div>
              <div className="flex-1">
                <h2 className="font-display text-2xl font-bold text-navy mb-2">Réservé aux Premium</h2>
                <p className="text-navy/80 text-lg leading-relaxed">
                  Le Défi Famille est l'occasion parfaite d'appeler vos petits-enfants pour leur lancer un quiz !
                  Cette fonctionnalité est incluse dans l'abonnement Premium.
                </p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-navy/60 text-lg">Chargement...</div>
        ) : items.length === 0 ? (
          <div className="bg-white border-2 border-cream-dark rounded-[28px] p-10 text-center" data-testid="challenges-empty">
            <Users className="w-14 h-14 mx-auto text-terracotta/60 mb-4" strokeWidth={2} />
            <h3 className="font-display text-2xl font-bold text-navy mb-2">Aucun défi pour le moment</h3>
            <p className="text-navy/70 mb-6">Lancez votre premier défi à votre famille en quelques secondes.</p>
            {isPremium && (
              <Link
                to="/app/challenges/new"
                className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-6 py-3 rounded-full shadow-warm"
              >
                <Plus className="w-5 h-5" /> Créer mon premier défi
              </Link>
            )}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {items.map((c, idx) => (
              <motion.div
                key={c.token}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                className="bg-white border-2 border-cream-dark rounded-[24px] p-6 hover:border-terracotta hover:-translate-y-0.5 transition"
                data-testid={`challenge-card-${c.token}`}
              >
                <div className="flex items-start gap-4 mb-4">
                  {c.category_mascot_image && (
                    <div className="w-16 h-16 rounded-2xl overflow-hidden bg-cream border-2 border-cream-dark shrink-0">
                      <img src={`${BACKEND_URL}${c.category_mascot_image}`} alt="" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-display text-xl font-bold text-navy truncate">{c.category_title || c.category_id}</h3>
                    <div className="flex items-center gap-3 text-sm text-navy/60 mt-1">
                      <span>{c.total_questions} questions</span>
                      <span>·</span>
                      <span>{new Date(c.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between bg-cream rounded-2xl px-4 py-3 mb-4">
                  <div className="flex items-center gap-2 text-navy">
                    <Users className="w-5 h-5 text-terracotta" />
                    <span className="font-bold">
                      {c.participants?.length || 0} participant{(c.participants?.length || 0) > 1 ? "s" : ""}
                    </span>
                  </div>
                  {c.participants?.length > 0 && (
                    <div className="flex items-center gap-1 text-navy">
                      <Trophy className="w-5 h-5 text-mustard-dark" />
                      <span className="font-bold">{c.participants[0].name}</span>
                      <span className="text-sm">({c.participants[0].score}/{c.participants[0].total})</span>
                    </div>
                  )}
                </div>

                <Link
                  to={`/app/challenges/${c.token}`}
                  data-testid={`challenge-open-${c.token}`}
                  className="w-full inline-flex items-center justify-center gap-2 bg-navy hover:bg-navy-dark text-white font-bold px-5 py-3 rounded-full transition"
                >
                  <Share2 className="w-4 h-4" /> Voir & partager <ArrowRight className="w-4 h-4" />
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
