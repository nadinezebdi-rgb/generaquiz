import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, BACKEND_URL, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Users, ArrowRight, Loader2, AlertTriangle, Heart, Sparkles } from "lucide-react";

/**
 * CoopChallengeCreate — Setup page for a same-device cooperative challenge.
 *
 * Form fields:
 *   - team_name              (e.g. "Les Aventuriers du Temps")
 *   - 2 players              (name + role: "senior" | "jeune", must differ)
 *   - category_id            (any of the existing 8 categories)
 *   - num_questions          (4–20, default 10)
 *
 * On submit → POST /api/coop-challenges → redirect to the play screen.
 */
const ROLE_LABELS = {
  senior: { label: "Senior", emoji: "👴" },
  jeune: { label: "Jeune", emoji: "🧒" },
};

export default function CoopChallengeCreate() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [teamName, setTeamName] = useState("");
  const [p1Name, setP1Name] = useState("");
  const [p1Role, setP1Role] = useState("senior");
  const [p2Name, setP2Name] = useState("");
  const [p2Role, setP2Role] = useState("jeune");
  const [categoryId, setCategoryId] = useState("");
  const [numQuestions, setNumQuestions] = useState(10);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get("/categories").then((r) => {
      setCategories(r.data);
      if (r.data[0]) setCategoryId(r.data[0].id);
    });
  }, []);

  const sameRole = p1Role === p2Role;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (sameRole) {
      setErr("Les deux joueurs doivent avoir des rôles différents (un Senior + un Jeune).");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post("/coop-challenges", {
        team_name: teamName.trim(),
        category_id: categoryId,
        num_questions: numQuestions,
        players: [
          { name: p1Name.trim(), role: p1Role },
          { name: p2Name.trim(), role: p2Role },
        ],
      });
      navigate(`/app/coop/${data.token}`);
    } catch (e2) {
      setErr(formatError(e2.response?.data?.detail) || "Une erreur est survenue.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-6">
          <div className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-sm mb-3">
            <Heart className="w-4 h-4 fill-current" /> Mode Coopératif
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-navy mb-2">
            Un Senior + un Jeune, <span className="text-terracotta italic">une seule équipe</span>
          </h1>
          <p className="text-lg text-navy/70">
            Vous jouez à 2 sur le même téléphone. Si l&apos;un bloque, il peut demander de l&apos;aide à l&apos;autre — la complicité avant tout !
          </p>
        </div>

        <form
          onSubmit={submit}
          className="bg-white border-2 border-cream-dark rounded-[28px] p-6 md:p-8 space-y-6"
          data-testid="coop-create-form"
        >
          {/* Team name */}
          <div>
            <label className="block text-sm font-bold text-navy mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-mustard-dark" /> Nom de l&apos;équipe
            </label>
            <input
              data-testid="coop-team-name"
              type="text"
              required
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="Les Aventuriers du Temps"
              maxLength={40}
              className="w-full px-4 py-4 text-lg rounded-2xl border-2 border-cream-dark focus:border-navy bg-white min-h-[56px]"
            />
          </div>

          {/* Players */}
          <div className="grid sm:grid-cols-2 gap-4">
            <PlayerCard
              testid="coop-player-1"
              title="Joueur 1"
              name={p1Name}
              role={p1Role}
              onName={setP1Name}
              onRole={setP1Role}
            />
            <PlayerCard
              testid="coop-player-2"
              title="Joueur 2"
              name={p2Name}
              role={p2Role}
              onName={setP2Name}
              onRole={setP2Role}
            />
          </div>

          {sameRole && (
            <div className="bg-bordeaux/10 border-2 border-bordeaux/40 rounded-2xl p-4 text-bordeaux font-medium flex items-center gap-2" data-testid="coop-same-role-warning">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              Les deux joueurs doivent avoir des rôles différents pour profiter du gameplay asymétrique.
            </div>
          )}

          {/* Category */}
          <div>
            <label className="block text-sm font-bold text-navy mb-2">Catégorie</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {categories.map((c) => (
                <button
                  type="button"
                  key={c.id}
                  data-testid={`coop-cat-${c.id}`}
                  onClick={() => setCategoryId(c.id)}
                  className={`flex flex-col items-center gap-2 p-3 rounded-2xl border-2 transition ${
                    categoryId === c.id
                      ? "border-terracotta bg-cream"
                      : "border-cream-dark bg-white hover:border-navy/40"
                  }`}
                >
                  {c.mascot_image && (
                    <img src={`${BACKEND_URL}${c.mascot_image}`} alt="" className="w-12 h-12 rounded-xl object-cover" />
                  )}
                  <span className="text-xs font-bold text-navy text-center leading-tight">{c.title}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Num questions */}
          <div>
            <label className="block text-sm font-bold text-navy mb-2">
              Nombre de questions : <span className="text-terracotta">{numQuestions}</span>
            </label>
            <input
              data-testid="coop-num-questions"
              type="range"
              min={4}
              max={20}
              step={2}
              value={numQuestions}
              onChange={(e) => setNumQuestions(parseInt(e.target.value, 10))}
              className="w-full accent-terracotta"
            />
            <div className="flex justify-between text-xs text-navy/60 mt-1">
              <span>4</span><span>20</span>
            </div>
          </div>

          {err && (
            <div className="bg-[#D9534F]/10 border-2 border-[#D9534F]/40 rounded-xl p-4 text-bordeaux font-medium" data-testid="coop-error">
              {err}
            </div>
          )}

          <motion.button
            type="submit"
            disabled={loading || sameRole || !teamName || !p1Name || !p2Name || !categoryId}
            whileTap={{ scale: 0.98 }}
            data-testid="coop-submit"
            className="w-full inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold text-lg px-6 py-4 rounded-full shadow-warm min-h-[60px] disabled:opacity-60 transition"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Users className="w-5 h-5" />}
            {loading ? "Préparation..." : "Démarrer le défi"}
            {!loading && <ArrowRight className="w-5 h-5" />}
          </motion.button>
        </form>
      </main>
      <Footer />
    </div>
  );
}

function PlayerCard({ testid, title, name, role, onName, onRole }) {
  return (
    <div className="bg-cream border-2 border-cream-dark rounded-2xl p-4">
      <div className="text-xs font-bold uppercase tracking-wider text-navy/60 mb-2">{title}</div>
      <input
        data-testid={`${testid}-name`}
        type="text"
        required
        value={name}
        onChange={(e) => onName(e.target.value)}
        placeholder="Son prénom"
        maxLength={30}
        className="w-full px-3 py-3 rounded-xl border-2 border-cream-dark focus:border-navy bg-white mb-3"
      />
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(ROLE_LABELS).map(([key, val]) => (
          <button
            type="button"
            key={key}
            data-testid={`${testid}-role-${key}`}
            onClick={() => onRole(key)}
            className={`px-3 py-2 rounded-xl text-sm font-bold border-2 transition ${
              role === key
                ? "border-terracotta bg-terracotta text-white"
                : "border-cream-dark bg-white text-navy hover:border-navy/40"
            }`}
          >
            {val.emoji} {val.label}
          </button>
        ))}
      </div>
    </div>
  );
}
