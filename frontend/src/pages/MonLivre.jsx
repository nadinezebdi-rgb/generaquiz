import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  BookOpen, ArrowLeft, Mic, MicOff, Pen, Users, Camera,
  Send, Loader2, Sparkles, Inbox, Heart, X, ChevronRight,
} from "lucide-react";

/**
 * Mon Livre de Vie — refonte de l'Atelier Mémoire.
 *
 * Expérience :
 *   1. Écran d'accueil : jauge de progression + 10 chapitres cliquables
 *   2. Vue chapitre : liste des prompts + entrées déjà écrites
 *   3. Modal de saisie : 3 modes (✍️ texte / 🎙️ audio / 👨‍👩‍👧 délégué) + photos
 *   4. Onglet Famille : questions reçues (inbox), envoyées, et envoi d'une nouvelle
 *
 * Toujours privé par défaut. Aucun score : la progression est chaleureuse et non punitive.
 */

export default function MonLivre() {
  const [tab, setTab] = useState("livre"); // "livre" | "famille"
  const [chapters, setChapters] = useState([]);
  const [covers, setCovers] = useState({});     // {chapter_id: url}
  const [progress, setProgress] = useState({ total_entries: 0, total_prompts: 50, progress_pct: 0 });
  const [openChapter, setOpenChapter] = useState(null); // full chapter with prompts+entries
  const [openPrompt, setOpenPrompt] = useState(null);   // {chapter_id, prompt_id, prompt_text}

  useEffect(() => { refresh(); }, []);

  async function refresh() {
    try {
      const [chRes, entriesRes, coversRes] = await Promise.all([
        api.get("/livre/chapters"),
        api.get("/livre/entries"),
        api.get("/livre/covers"),
      ]);
      setChapters(chRes.data);
      setCovers(coversRes.data || {});
      setProgress({
        total_entries: entriesRes.data.total_entries,
        total_prompts: entriesRes.data.total_prompts,
        progress_pct: entriesRes.data.progress_pct,
      });
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible de charger votre Livre");
    }
  }

  async function openChapterFn(chapterId) {
    try {
      const { data } = await api.get(`/livre/chapters/${chapterId}`);
      setOpenChapter(data);
    } catch (e) {
      toast.error("Impossible d'ouvrir le chapitre");
    }
  }

  async function downloadPdf() {
    try {
      const res = await api.get("/livre/export/pdf", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `mon-livre-de-vie-${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => window.URL.revokeObjectURL(url), 5000);
      toast.success("PDF téléchargé 📕");
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Aucun souvenir à exporter pour l'instant");
    }
  }

  return (
    <div className="min-h-screen bg-cream text-navy">
      <Navbar />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-8">
          <span className="inline-flex items-center gap-2 bg-bordeaux text-cream font-bold px-3 py-1 rounded-full text-xs uppercase tracking-wider mb-3">
            <BookOpen className="w-3.5 h-3.5" /> Mon Livre de Vie
          </span>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold" data-testid="livre-title">
            📖 Mon <span className="text-terracotta italic">Livre de Vie</span>
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <p className="text-navy/70 max-w-2xl flex-1">
              Mes souvenirs. Mon histoire. Pour ceux que j&apos;aime. Répondez à une question, un souvenir à la fois — tout reste <b>privé par défaut</b>.
            </p>
            <a
              href={`${process.env.REACT_APP_BACKEND_URL}/api/livre/export/pdf`}
              target="_blank"
              rel="noreferrer"
              data-testid="livre-export-pdf"
              className="hidden md:inline-flex items-center gap-2 bg-navy text-cream text-sm font-bold px-4 py-2 rounded-full hover:bg-navy-dark transition shrink-0"
              onClick={(e) => {
                // Passe le JWT via un fetch-then-download côté client car <a> ne peut pas envoyer les cookies+headers axios
                e.preventDefault();
                downloadPdf();
              }}
            >
              📕 Télécharger mon Livre en PDF
            </a>
          </div>
        </header>

        <div className="mb-6 flex gap-2 border-b-2 border-cream-dark" data-testid="livre-tabs">
          <TabBtn active={tab === "livre"} onClick={() => setTab("livre")} testid="livre-tab-livre">
            <BookOpen className="w-4 h-4" /> Mon livre
          </TabBtn>
          <TabBtn active={tab === "famille"} onClick={() => setTab("famille")} testid="livre-tab-famille">
            <Users className="w-4 h-4" /> Ma famille
          </TabBtn>
        </div>

        {tab === "livre" ? (
          <>
            <ProgressBar progress={progress} />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-6">
              {chapters.map((c) => (
                <ChapterTile key={c.id} chapter={c} coverUrl={covers[c.id]} onClick={() => openChapterFn(c.id)} />
              ))}
            </div>
          </>
        ) : (
          <FamilyTab />
        )}
      </main>
      <Footer />

      {openChapter && !openPrompt && (
        <ChapterModal
          chapter={openChapter}
          onClose={() => { setOpenChapter(null); refresh(); }}
          onPromptClick={(p) => setOpenPrompt({ chapter_id: openChapter.id, prompt_id: p.id, prompt_text: p.text })}
        />
      )}
      {openPrompt && (
        <EntryModal
          chapterId={openPrompt.chapter_id}
          promptId={openPrompt.prompt_id}
          promptText={openPrompt.prompt_text}
          onClose={() => setOpenPrompt(null)}
          onSaved={() => { setOpenPrompt(null); if (openChapter) openChapterFn(openChapter.id); refresh(); }}
        />
      )}
    </div>
  );
}

// -------------------------------------------------------------------------- //
//  Sous-composants                                                            //
// -------------------------------------------------------------------------- //

function TabBtn({ active, onClick, children, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      className={`inline-flex items-center gap-2 px-4 py-2 font-bold text-sm border-b-4 -mb-0.5 transition ${
        active ? "border-terracotta text-terracotta" : "border-transparent text-navy/60 hover:text-navy"
      }`}
    >{children}</button>
  );
}

function ProgressBar({ progress }) {
  const { total_entries, total_prompts, progress_pct } = progress;
  const message = total_entries === 0
    ? "Prenez le temps d'un souvenir — chaque question compte."
    : total_entries < 5
      ? `Votre livre commence à prendre vie — ${total_entries} souvenir${total_entries > 1 ? "s" : ""} déjà consigné${total_entries > 1 ? "s" : ""} 🌱`
      : total_entries < 20
        ? `Votre livre grandit joliment — ${total_entries} souvenirs 🌿`
        : `Quel beau livre ! ${total_entries} souvenirs déjà partagés avec vous-même 🌳`;
  return (
    <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm" data-testid="livre-progress-card">
      <div className="flex items-center justify-between mb-2">
        <div className="font-bold text-navy inline-flex items-center gap-2"><Sparkles className="w-4 h-4 text-terracotta" /> Votre progression</div>
        <span className="text-sm text-navy/60">{total_entries} / {total_prompts} questions</span>
      </div>
      <div className="w-full h-3 bg-cream-dark rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress_pct}%` }}
          transition={{ duration: 0.6 }}
          className="h-full bg-gradient-to-r from-terracotta to-mustard"
        />
      </div>
      <p className="text-sm text-navy/70 mt-3">{message}</p>
    </div>
  );
}

function ChapterTile({ chapter, coverUrl, onClick }) {
  const pct = chapter.n_prompts > 0 ? Math.round((chapter.n_written / chapter.n_prompts) * 100) : 0;
  const backend = process.env.REACT_APP_BACKEND_URL;
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`livre-chapter-${chapter.id}`}
      className="text-left bg-white rounded-2xl border-2 border-cream-dark hover:border-terracotta shadow-warm transition group overflow-hidden"
    >
      {coverUrl ? (
        <div className="aspect-[4/2] bg-cream-dark overflow-hidden">
          <img
            src={`${backend}${coverUrl}`}
            alt={`Couverture ${chapter.label}`}
            className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
            loading="lazy"
          />
        </div>
      ) : null}
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="text-3xl mb-1">{chapter.emoji}</div>
            <div className="font-display text-xl font-bold text-navy group-hover:text-terracotta transition">
              {chapter.label}
            </div>
          </div>
          <span className="text-xs text-navy/50 font-mono">{chapter.order}/10</span>
        </div>
        <p className="text-sm text-navy/70 mb-4 min-h-[40px]">{chapter.description}</p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-navy/60">{chapter.n_written}/{chapter.n_prompts} souvenirs</span>
          <div className="w-24 h-2 bg-cream-dark rounded-full overflow-hidden">
            <div className="h-full bg-terracotta" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
    </button>
  );
}

function ChapterModal({ chapter, onClose, onPromptClick }) {
  const entriesByPrompt = useMemo(() => {
    const map = {};
    for (const e of chapter.entries || []) {
      (map[e.prompt_id] = map[e.prompt_id] || []).push(e);
    }
    return map;
  }, [chapter]);

  return (
    <div className="fixed inset-0 z-50 bg-navy/50 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-cream rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()} data-testid="livre-chapter-modal">
        <div className="sticky top-0 bg-cream border-b-2 border-cream-dark p-5 flex items-center justify-between">
          <div>
            <div className="text-3xl">{chapter.emoji}</div>
            <h2 className="font-display text-2xl font-bold text-navy">{chapter.label}</h2>
            <p className="text-sm text-navy/70">{chapter.description}</p>
          </div>
          <button onClick={onClose} data-testid="livre-chapter-close" className="p-2 hover:bg-cream-dark rounded-full transition">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          {chapter.prompts.map((p) => {
            const written = entriesByPrompt[p.id] || [];
            return (
              <div key={p.id} className="bg-white rounded-xl border-2 border-cream-dark p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="font-semibold text-navy">{p.text}</p>
                    {written.length > 0 && (
                      <div className="mt-2 space-y-2">
                        {written.map((e, i) => <EntryPreview key={i} entry={e} />)}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => onPromptClick(p)}
                    data-testid={`livre-prompt-answer-${p.id}`}
                    className="shrink-0 inline-flex items-center gap-1 bg-terracotta text-white text-sm font-bold px-3 py-2 rounded-full hover:bg-terracotta-dark transition"
                  >
                    {written.length > 0 ? "Ajouter" : "Répondre"} <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function EntryPreview({ entry }) {
  const badge = { text: "✍️ écrit", audio: "🎙️ audio", delegated: `👨‍👩‍👧 raconté` }[entry.mode] || "";
  const author = entry.mode === "delegated" && entry.delegated_author_name
    ? ` par ${entry.delegated_author_name}` : "";
  return (
    <div className="bg-cream rounded-lg p-3 border border-cream-dark">
      <div className="text-xs text-navy/50 mb-1">{badge}{author} · {new Date(entry.created_at).toLocaleDateString("fr-FR")}</div>
      {entry.text && <p className="text-sm text-navy whitespace-pre-wrap">{entry.text.slice(0, 220)}{entry.text.length > 220 ? "…" : ""}</p>}
      {entry.audio_b64 && <audio controls src={`data:audio/webm;base64,${entry.audio_b64}`} className="w-full mt-2" />}
      {entry.photos?.length > 0 && (
        <div className="flex gap-2 mt-2">
          {entry.photos.map((p, i) => (
            <img key={i} src={`data:image/jpeg;base64,${p.b64}`} alt={p.caption || ""} className="w-16 h-16 object-cover rounded-md" />
          ))}
        </div>
      )}
    </div>
  );
}

function EntryModal({ chapterId, promptId, promptText, onClose, onSaved }) {
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [audioB64, setAudioB64] = useState(null);
  const [photos, setPhotos] = useState([]); // [{b64, caption, who, where, when}]
  const [delegatedName, setDelegatedName] = useState("");
  const [saving, setSaving] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  async function transcribeAudio() {
    if (!audioB64) return;
    setTranscribing(true);
    try {
      const { data } = await api.post("/livre/transcribe", { audio_b64: audioB64 });
      setText(data.transcript || "");
      toast.success("Transcription terminée ✨");
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Transcription impossible");
    } finally { setTranscribing(false); }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data); };
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        // Limite à ~60 s → ~1 Mo
        if (blob.size > 1_800_000) {
          toast.error("Enregistrement trop long (max 60 s environ)");
          return;
        }
        const reader = new FileReader();
        reader.onloadend = () => setAudioB64(reader.result.split(",")[1]);
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecorderRef.current = mr;
      mr.start();
      setRecording(true);
      // Auto-stop après 60 s
      setTimeout(() => { if (mr.state === "recording") mr.stop(); setRecording(false); }, 60_000);
    } catch (e) {
      toast.error("Impossible d'accéder au microphone. Vérifiez les autorisations.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  }

  function addPhoto(file) {
    if (photos.length >= 3) { toast.error("3 photos maximum par souvenir"); return; }
    if (file.size > 1_800_000) { toast.error("Photo trop lourde (max ~1.8 Mo)"); return; }
    const reader = new FileReader();
    reader.onloadend = () => {
      setPhotos((prev) => [...prev, { b64: reader.result.split(",")[1], caption: "", who: "", where: "", when: "" }]);
    };
    reader.readAsDataURL(file);
  }

  async function save() {
    if (mode === "text" && !text.trim()) { toast.error("Écrivez quelque chose avant d'enregistrer"); return; }
    if (mode === "audio" && !audioB64) { toast.error("Enregistrez d'abord un message audio"); return; }
    setSaving(true);
    try {
      await api.post("/livre/entries", {
        chapter_id: chapterId,
        prompt_id: promptId,
        mode,
        text,
        audio_b64: mode === "audio" ? audioB64 : null,
        photos,
        delegated_author_name: mode === "delegated" ? delegatedName : "",
        visibility: "private",
      });
      toast.success("Souvenir enregistré 🌱");
      onSaved();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible d'enregistrer");
    } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-[60] bg-navy/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()} data-testid="livre-entry-modal">
        <div className="sticky top-0 bg-white border-b-2 border-cream-dark p-5 flex items-center justify-between">
          <h3 className="font-bold text-navy text-lg pr-4">{promptText}</h3>
          <button onClick={onClose} data-testid="livre-entry-close" className="p-2 hover:bg-cream rounded-full">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex gap-2 flex-wrap" data-testid="livre-entry-mode-picker">
            <ModeBtn active={mode === "text"} onClick={() => setMode("text")} testid="mode-text">
              <Pen className="w-4 h-4" /> ✍️ J&apos;écris
            </ModeBtn>
            <ModeBtn active={mode === "audio"} onClick={() => setMode("audio")} testid="mode-audio">
              <Mic className="w-4 h-4" /> 🎙️ J&apos;enregistre
            </ModeBtn>
            <ModeBtn active={mode === "delegated"} onClick={() => setMode("delegated")} testid="mode-delegated">
              <Users className="w-4 h-4" /> 👨‍👩‍👧 On me raconte
            </ModeBtn>
          </div>

          {mode === "text" && (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Racontez-nous… (prenez votre temps, personne ne vous corrigera)"
              className="w-full min-h-[180px] p-4 rounded-xl border-2 border-cream-dark bg-cream focus:border-terracotta outline-none text-navy resize-y text-base"
              maxLength={8000}
              data-testid="livre-entry-text"
            />
          )}

          {mode === "audio" && (
            <div className="bg-cream rounded-xl p-6 text-center">
              {!audioB64 ? (
                <>
                  <button
                    type="button"
                    onClick={recording ? stopRecording : startRecording}
                    data-testid="livre-entry-record"
                    className={`w-28 h-28 rounded-full flex items-center justify-center mx-auto text-white transition shadow-lg ${
                      recording ? "bg-red-500 animate-pulse" : "bg-terracotta hover:bg-terracotta-dark"
                    }`}
                  >
                    {recording ? <MicOff className="w-10 h-10" /> : <Mic className="w-10 h-10" />}
                  </button>
                  <p className="mt-4 text-sm text-navy/70">
                    {recording ? "Enregistrement en cours… (touchez pour arrêter, max 60 s)" : "Touchez pour parler"}
                  </p>
                </>
              ) : (
                <>
                  <audio controls src={`data:audio/webm;base64,${audioB64}`} className="w-full" data-testid="livre-entry-audio-preview" />
                  <div className="mt-3 flex gap-2 justify-center flex-wrap">
                    <button
                      type="button"
                      onClick={() => setAudioB64(null)}
                      data-testid="livre-entry-audio-redo"
                      className="text-sm font-bold text-bordeaux hover:underline"
                    >
                      Réenregistrer
                    </button>
                    <button
                      type="button"
                      onClick={transcribeAudio}
                      disabled={transcribing}
                      data-testid="livre-entry-transcribe"
                      className="text-sm font-bold inline-flex items-center gap-1 bg-navy text-cream px-3 py-1.5 rounded-full hover:bg-navy-dark disabled:opacity-50"
                    >
                      {transcribing ? <Loader2 className="w-3 h-3 animate-spin" /> : "✨"} Transcrire en texte
                    </button>
                  </div>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Transcription automatique ou légende (modifiable)"
                    className="w-full mt-3 p-3 rounded-lg border-2 border-cream-dark bg-white outline-none text-navy text-sm"
                    rows={4}
                    data-testid="livre-entry-audio-transcript"
                  />
                </>
              )}
            </div>
          )}

          {mode === "delegated" && (
            <div className="space-y-3">
              <input
                type="text"
                value={delegatedName}
                onChange={(e) => setDelegatedName(e.target.value)}
                placeholder="Qui vous a aidé à écrire ce souvenir ? (ex : Emma, ma petite-fille)"
                className="w-full p-3 rounded-xl border-2 border-cream-dark bg-cream focus:border-terracotta outline-none text-navy"
                maxLength={60}
                data-testid="livre-entry-delegated-name"
              />
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Écrivez le souvenir tel qu'il vous a été raconté…"
                className="w-full min-h-[160px] p-4 rounded-xl border-2 border-cream-dark bg-cream focus:border-terracotta outline-none text-navy resize-y text-base"
                maxLength={8000}
                data-testid="livre-entry-delegated-text"
              />
            </div>
          )}

          <PhotosPicker photos={photos} setPhotos={setPhotos} addPhoto={addPhoto} />

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-full border-2 border-navy text-navy font-bold hover:bg-navy hover:text-white transition"
            >Annuler</button>
            <button
              type="button"
              onClick={save}
              disabled={saving}
              data-testid="livre-entry-save"
              className="inline-flex items-center gap-2 bg-terracotta text-white font-bold px-6 py-2 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition shadow-warm"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Heart className="w-4 h-4" />}
              Consigner ce souvenir
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModeBtn({ active, onClick, children, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={`livre-${testid}`}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-full font-bold text-sm border-2 transition ${
        active
          ? "bg-terracotta text-white border-terracotta"
          : "bg-white text-navy border-cream-dark hover:border-terracotta"
      }`}
    >{children}</button>
  );
}

function PhotosPicker({ photos, setPhotos, addPhoto }) {
  const fileRef = useRef(null);
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-bold text-navy inline-flex items-center gap-1"><Camera className="w-4 h-4" /> Photos (optionnel, 3 max)</span>
        {photos.length < 3 && (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            data-testid="livre-entry-add-photo"
            className="text-xs font-bold text-terracotta hover:underline"
          >+ Ajouter</button>
        )}
        <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => { if (e.target.files[0]) addPhoto(e.target.files[0]); e.target.value = ""; }} />
      </div>
      {photos.length > 0 && (
        <div className="flex gap-3 flex-wrap">
          {photos.map((p, i) => (
            <div key={i} className="relative">
              <img src={`data:image/jpeg;base64,${p.b64}`} alt="" className="w-24 h-24 object-cover rounded-lg border-2 border-cream-dark" />
              <button
                type="button"
                onClick={() => setPhotos((prev) => prev.filter((_, j) => j !== i))}
                className="absolute -top-2 -right-2 w-6 h-6 bg-bordeaux text-white rounded-full flex items-center justify-center hover:bg-red-700"
                data-testid={`livre-photo-remove-${i}`}
              ><X className="w-3 h-3" /></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------------------- //
//  Onglet Famille                                                             //
// -------------------------------------------------------------------------- //

function FamilyTab() {
  const [inbox, setInbox] = useState([]);
  const [sent, setSent] = useState([]);
  const [members, setMembers] = useState([]);
  const [toEmail, setToEmail] = useState("");
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitePerm, setInvitePerm] = useState("view");

  useEffect(() => { refresh(); }, []);

  async function refresh() {
    try {
      const [i, s, m] = await Promise.all([
        api.get("/livre/family/questions/inbox"),
        api.get("/livre/family/questions/sent"),
        api.get("/livre/family/members"),
      ]);
      setInbox(i.data); setSent(s.data); setMembers(m.data);
    } catch (e) { /* silencieux */ }
  }

  async function sendQuestion() {
    if (!toEmail.trim() || question.length < 5) { toast.error("E-mail et question requis"); return; }
    setSending(true);
    try {
      await api.post("/livre/family/questions", { to_email: toEmail.trim(), question: question.trim() });
      toast.success("Question envoyée ! Elle attend une réponse.");
      setToEmail(""); setQuestion(""); refresh();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible d'envoyer");
    } finally { setSending(false); }
  }

  async function invite() {
    if (!inviteEmail.trim()) return;
    try {
      await api.post("/livre/family/invite", { invitee_email: inviteEmail.trim(), permission: invitePerm });
      toast.success("Invitation créée");
      setInviteEmail(""); refresh();
    } catch (e) {
      toast.error(formatError(e.response?.data?.detail) || "Impossible d'inviter");
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-6" data-testid="livre-family-tab">
      {/* Colonne gauche — questions */}
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm">
          <h3 className="font-display text-xl font-bold text-navy mb-3 inline-flex items-center gap-2">
            <Send className="w-5 h-5 text-terracotta" /> Poser une question à un proche
          </h3>
          <p className="text-sm text-navy/70 mb-3">
            Envoyez une petite question à votre grand-père, grand-mère, parent — leur réponse rejoindra leur Livre de Vie.
          </p>
          <input
            type="email"
            value={toEmail}
            onChange={(e) => setToEmail(e.target.value)}
            placeholder="E-mail du proche (compte GénéraQuiz existant)"
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none mb-2"
            data-testid="family-question-email"
          />
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ex : Raconte-moi ta première voiture — comment était-elle ?"
            maxLength={300}
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none min-h-[80px]"
            data-testid="family-question-text"
          />
          <button
            type="button"
            onClick={sendQuestion}
            disabled={sending}
            data-testid="family-question-send"
            className="mt-2 inline-flex items-center gap-2 bg-terracotta text-white font-bold px-5 py-2 rounded-full hover:bg-terracotta-dark disabled:opacity-50 transition"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Envoyer
          </button>
        </div>

        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm" data-testid="family-inbox">
          <h3 className="font-display text-xl font-bold text-navy mb-3 inline-flex items-center gap-2">
            <Inbox className="w-5 h-5 text-terracotta" /> Questions reçues ({inbox.length})
          </h3>
          {inbox.length === 0 ? (
            <p className="text-sm text-navy/60">Aucune question pour l&apos;instant.</p>
          ) : (
            <ul className="space-y-2">
              {inbox.map((q) => (
                <li key={q.id} className="bg-cream rounded-lg p-3 border border-cream-dark">
                  <div className="text-xs text-navy/50 mb-1">De {q.from_user_name} · {new Date(q.created_at).toLocaleDateString("fr-FR")} · {q.status === "answered" ? "✅ répondu" : "⏳ en attente"}</div>
                  <p className="text-sm text-navy">{q.question}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm">
          <h3 className="font-display text-xl font-bold text-navy mb-3">📤 Envoyées ({sent.length})</h3>
          {sent.length === 0 ? (
            <p className="text-sm text-navy/60">Aucune question envoyée.</p>
          ) : (
            <ul className="space-y-2">
              {sent.slice(0, 5).map((q) => (
                <li key={q.id} className="bg-cream rounded-lg p-3 border border-cream-dark text-sm">
                  <span className="text-navy/50 text-xs">{new Date(q.created_at).toLocaleDateString("fr-FR")} · {q.status === "answered" ? "✅" : "⏳"} </span>
                  {q.question}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Colonne droite — invitations et permissions */}
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm" data-testid="family-invite-card">
          <h3 className="font-display text-xl font-bold text-navy mb-3 inline-flex items-center gap-2">
            <Users className="w-5 h-5 text-terracotta" /> Inviter un proche
          </h3>
          <p className="text-sm text-navy/70 mb-3">
            Ajoutez un membre de la famille avec un niveau de permission. Votre livre reste privé sauf autorisation explicite.
          </p>
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="E-mail du proche"
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none mb-2"
            data-testid="family-invite-email"
          />
          <select
            value={invitePerm}
            onChange={(e) => setInvitePerm(e.target.value)}
            className="w-full p-3 rounded-lg border-2 border-cream-dark focus:border-terracotta outline-none mb-2 bg-white"
            data-testid="family-invite-permission"
          >
            <option value="view">Consulter (lecture seule)</option>
            <option value="comment">Consulter + commenter</option>
            <option value="contribute">Consulter + ajouter des souvenirs</option>
            <option value="manage">Gérer (comme moi)</option>
          </select>
          <button
            type="button"
            onClick={invite}
            data-testid="family-invite-send"
            className="inline-flex items-center gap-2 bg-navy text-cream font-bold px-5 py-2 rounded-full hover:bg-navy-dark transition"
          >
            <Send className="w-4 h-4" /> Inviter
          </button>
        </div>

        <div className="bg-white rounded-2xl border-2 border-cream-dark p-5 shadow-warm">
          <h3 className="font-display text-xl font-bold text-navy mb-3">👥 Mon cercle ({members.length})</h3>
          {members.length === 0 ? (
            <p className="text-sm text-navy/60">Vous n&apos;avez encore invité personne.</p>
          ) : (
            <ul className="space-y-2">
              {members.map((m) => (
                <li key={m.id} className="bg-cream rounded-lg p-3 border border-cream-dark flex items-center justify-between text-sm">
                  <div>
                    <div className="font-bold text-navy">{m.invitee_email}</div>
                    <div className="text-xs text-navy/60">{m.permission} · {m.status}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
