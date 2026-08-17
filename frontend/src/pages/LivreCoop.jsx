import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import axios from "axios";
import { formatError } from "@/lib/api";
import { BookOpen, Users, Send, Loader2, Heart, ChevronRight } from "lucide-react";

/**
 * LivreCoop — page publique (pas d'auth) pour rejoindre une session
 * partagée du Livre de Vie. Le petit-enfant entre son prénom, voit le
 * chapitre choisi par le grand-parent, et peut ajouter des souvenirs qui
 * apparaissent en temps quasi-réel dans le Livre du grand-parent.
 *
 * Sync : polling toutes les 4 s + heartbeat pour la présence.
 */

const backend = process.env.REACT_APP_BACKEND_URL;
const POLL_MS = 4000;
const NAME_KEY = "livre-coop-guest-name";

export default function LivreCoop() {
  const { code } = useParams();
  const upperCode = (code || "").toUpperCase();
  const [guestName, setGuestName] = useState(() => localStorage.getItem(NAME_KEY) || "");
  const [joined, setJoined] = useState(false);
  const [state, setState] = useState(null); // {owner_name, chapter, entries, participants}
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef(null);

  const fetchState = useCallback(async () => {
    try {
      const r = await axios.get(`${backend}/api/livre/coop/${upperCode}/state`);
      setState(r.data);
      setError("");
    } catch (e) {
      const detail = e.response?.data?.detail || "Session introuvable";
      setError(detail);
    }
  }, [upperCode]);

  const heartbeat = useCallback(async () => {
    if (!guestName) return;
    try {
      await axios.post(`${backend}/api/livre/coop/${upperCode}/heartbeat`, { guest_name: guestName });
    } catch (err) {
      console.debug("Heartbeat failed:", err);
    }
  }, [guestName, upperCode]);

  async function handleJoin(e) {
    e.preventDefault();
    const name = guestName.trim();
    if (!name) return;
    try {
      const r = await axios.post(`${backend}/api/livre/coop/join`, {
        code: upperCode, guest_name: name,
      });
      localStorage.setItem(NAME_KEY, name);
      setState((s) => ({
        ...(s || {}),
        participants: r.data.session.participants,
      }));
      setJoined(true);
      await fetchState();
      toast.success(`Bienvenue ${name} ! ✨`);
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Impossible de rejoindre");
      setError(err.response?.data?.detail || "");
    }
  }

  async function submitEntry(e) {
    e.preventDefault();
    if (!selectedPrompt || !text.trim()) return;
    setSending(true);
    try {
      await axios.post(`${backend}/api/livre/coop/${upperCode}/entry`, {
        prompt_id: selectedPrompt.id,
        guest_name: guestName,
        text: text.trim(),
      });
      setText("");
      setSelectedPrompt(null);
      toast.success("Souvenir ajouté au Livre 📖");
      await fetchState();
    } catch (err) {
      toast.error(formatError(err.response?.data?.detail) || "Envoi impossible");
    } finally {
      setSending(false);
    }
  }

  // Initial load (state visible même avant join)
  useEffect(() => { fetchState(); }, [fetchState]);

  // Polling + heartbeat une fois rejoint
  useEffect(() => {
    if (!joined) return undefined;
    pollRef.current = setInterval(() => { fetchState(); heartbeat(); }, POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [joined, fetchState, heartbeat]);

  // ==== Écran d'erreur ====
  if (error && !state) {
    return (
      <ErrorLayout title="Session introuvable" message={error} />
    );
  }

  // ==== Écran de bienvenue / saisie du prénom ====
  if (!joined || !state) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl border-2 border-cream-dark shadow-warm max-w-md w-full p-8"
          data-testid="coop-join-card"
        >
          <div className="flex items-center gap-2 text-terracotta font-bold text-sm mb-4">
            <BookOpen className="w-4 h-4" /> Livre de Vie · Session partagée
          </div>
          <h1 className="font-display text-3xl font-extrabold text-navy leading-tight mb-2">
            {state?.owner_name ? (
              <>Rejoignez <span className="text-terracotta italic">{state.owner_name}</span></>
            ) : (
              <>Bienvenue !</>
            )}
          </h1>
          <p className="text-navy/70 mb-6">
            {state?.chapter?.label
              ? <>Vous allez écrire ensemble le chapitre <b>{state.chapter.emoji} {state.chapter.label}</b>. Entrez votre prénom pour rejoindre.</>
              : <>Chargement de la session {upperCode}…</>}
          </p>
          <form onSubmit={handleJoin} className="space-y-4">
            <input
              type="text"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Votre prénom (ex : Louise)"
              className="w-full px-4 py-3 rounded-full border-2 border-cream-dark focus:border-terracotta focus:outline-none text-navy font-semibold"
              data-testid="coop-join-name"
              maxLength={60}
              required
              autoFocus
            />
            <button
              type="submit"
              disabled={!guestName.trim() || !state}
              data-testid="coop-join-submit"
              className="w-full inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition disabled:opacity-50"
            >
              Rejoindre <ChevronRight className="w-4 h-4" />
            </button>
          </form>
          <div className="text-xs text-navy/50 mt-4 text-center">
            Code de session : <span className="font-mono font-bold text-navy">{upperCode}</span>
          </div>
        </motion.div>
      </div>
    );
  }

  // ==== Écran principal (rejoint) ====
  const { owner_name, chapter, entries, participants } = state;
  const entriesByPrompt = (entries || []).reduce((acc, e) => {
    (acc[e.prompt_id] = acc[e.prompt_id] || []).push(e);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-cream text-navy">
      <header className="bg-white border-b-2 border-cream-dark px-4 py-4 sticky top-0 z-30" data-testid="coop-header">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
          <div>
            <div className="text-xs text-terracotta font-bold uppercase tracking-wider">
              Session partagée avec {owner_name}
            </div>
            <h1 className="font-display text-2xl font-extrabold">
              {chapter.emoji} {chapter.label}
            </h1>
          </div>
          <Participants list={participants} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 pb-40">
        <p className="text-navy/70 mb-6">{chapter.description}</p>

        <div className="space-y-3" data-testid="coop-prompts-list">
          {chapter.prompts.map((p) => {
            const written = entriesByPrompt[p.id] || [];
            return (
              <div key={p.id} className="bg-white rounded-2xl border-2 border-cream-dark p-4 shadow-warm">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-semibold flex-1">{p.text}</p>
                  <button
                    type="button"
                    onClick={() => { setSelectedPrompt(p); setText(""); }}
                    data-testid={`coop-answer-${p.id}`}
                    className="shrink-0 inline-flex items-center gap-1 bg-terracotta text-white text-sm font-bold px-3 py-2 rounded-full hover:bg-terracotta-dark transition"
                  >
                    <Send className="w-3.5 h-3.5" /> Raconter
                  </button>
                </div>
                {written.length > 0 && (
                  <div className="mt-3 space-y-2">
                    <AnimatePresence initial={false}>
                      {written.map((e) => (
                        <motion.div
                          key={e.id}
                          initial={{ opacity: 0, y: 6 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="bg-cream rounded-xl p-3 border border-cream-dark"
                          data-testid={`coop-entry-${e.id}`}
                        >
                          <div className="text-xs text-navy/60 mb-1 flex items-center gap-1">
                            <Heart className="w-3 h-3 text-terracotta" />
                            {e.mode === "delegated" && e.delegated_author_name
                              ? <>Raconté par <b>{e.delegated_author_name}</b></>
                              : <>Raconté par <b>{owner_name}</b></>}
                            <span>·</span>
                            <span>{new Date(e.created_at).toLocaleDateString("fr-FR")}</span>
                          </div>
                          {e.text && <p className="text-sm whitespace-pre-wrap">{e.text}</p>}
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>

      {/* Composeur en pied de page */}
      <AnimatePresence>
        {selectedPrompt && (
          <motion.form
            initial={{ y: 200 }} animate={{ y: 0 }} exit={{ y: 200 }}
            onSubmit={submitEntry}
            className="fixed bottom-0 inset-x-0 bg-white border-t-4 border-terracotta shadow-2xl p-4 z-40"
            data-testid="coop-composer"
          >
            <div className="max-w-4xl mx-auto">
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-sm font-bold text-navy flex-1">
                  <span className="text-terracotta">✍️</span> {selectedPrompt.text}
                </p>
                <button type="button" onClick={() => { setSelectedPrompt(null); setText(""); }} className="text-navy/50 hover:text-navy text-sm">Annuler</button>
              </div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={`Racontez ce que ${owner_name} vous a dit…`}
                rows={3}
                maxLength={8000}
                autoFocus
                data-testid="coop-composer-text"
                className="w-full px-3 py-2 rounded-xl border-2 border-cream-dark focus:border-terracotta focus:outline-none resize-none text-navy"
              />
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-navy/50">{text.length}/8000</span>
                <button
                  type="submit"
                  disabled={sending || !text.trim()}
                  data-testid="coop-composer-send"
                  className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Envoyer
                </button>
              </div>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}

function Participants({ list }) {
  const now = Date.now();
  return (
    <div className="flex items-center gap-2" data-testid="coop-participants">
      <Users className="w-4 h-4 text-navy/60" />
      <div className="flex -space-x-2">
        {(list || []).map((p) => {
          const online = p.last_seen && (now - new Date(p.last_seen).getTime()) < 15000;
          return (
            <div
              key={p.name}
              title={`${p.name}${p.is_owner ? " (auteur du Livre)" : ""}${online ? " · en ligne" : ""}`}
              className={`w-9 h-9 rounded-full border-2 flex items-center justify-center font-bold text-xs uppercase ${
                p.is_owner ? "bg-terracotta text-white border-white" : "bg-navy text-cream border-white"
              }`}
            >
              {p.name.slice(0, 2)}
              {online && <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border border-white" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ErrorLayout({ title, message }) {
  return (
    <div className="min-h-screen bg-cream flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border-2 border-cream-dark p-8 max-w-md text-center">
        <h1 className="font-display text-2xl font-bold text-navy mb-2">{title}</h1>
        <p className="text-navy/70 mb-4">{message}</p>
        <Link to="/" className="inline-block bg-navy text-cream font-bold px-5 py-2 rounded-full hover:bg-navy-dark">Retour à l&apos;accueil</Link>
      </div>
    </div>
  );
}
