import { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen, ChevronLeft, ChevronRight, X, Sparkles, Download,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

/**
 * FeuilleterModal — mode plein écran « Feuilleter mon Livre de Vie ».
 *
 * L'utilisateur voit son livre comme un vrai livre imprimé :
 *   1. Page de garde (couverture)
 *   2. Pour chaque chapitre : page-titre + une page par souvenir (avec photos)
 *   3. Page de fin (dédicace)
 *
 * Navigation :
 *   - Clavier ← / → / Échap
 *   - Boutons latéraux
 *   - Swipe tactile (framer-motion drag)
 *
 * Empty state : si l'utilisateur n'a encore rien écrit, on l'invite à
 * commencer plutôt que d'afficher un livre vide.
 */
export default function FeuilleterModal({ onClose, onDownloadPdf }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);   // { chapters: [{id,label,emoji,entries:[]}], total_entries }
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [idx, setIdx] = useState(0);
  const [direction, setDirection] = useState(1); // pour l'anim de page

  useEffect(() => {
    let cancelled = false;
    api.get("/livre/entries")
      .then((r) => { if (!cancelled) setData(r.data); })
      .catch((e) => { if (!cancelled) setErr(e?.response?.data?.detail || "Erreur"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  // Construction linéaire des pages à afficher
  const pages = useMemo(() => buildPages(data, user), [data, user]);
  const total = pages.length;
  const clamp = useCallback((n) => Math.max(0, Math.min(total - 1, n)), [total]);
  const go = useCallback((delta) => {
    setDirection(delta > 0 ? 1 : -1);
    setIdx((i) => clamp(i + delta));
  }, [clamp]);
  const jumpTo = useCallback((n) => {
    setDirection(n > idx ? 1 : -1);
    setIdx(clamp(n));
  }, [clamp, idx]);

  // Navigation clavier
  useEffect(() => {
    function onKey(e) {
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); go(1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(-1); }
      else if (e.key === "Escape") { onClose(); }
      else if (e.key === "Home") { jumpTo(0); }
      else if (e.key === "End") { jumpTo(total - 1); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, jumpTo, onClose, total]);

  const page = pages[idx];
  const isEmpty = data && data.total_entries === 0;

  return (
    <div
      className="fixed inset-0 z-[70] bg-navy/90 backdrop-blur-sm flex flex-col"
      data-testid="feuilleter-modal"
    >
      {/* Barre supérieure */}
      <div className="flex items-center justify-between px-4 py-3 bg-navy text-cream border-b border-cream/10">
        <div className="inline-flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-mustard" />
          <span className="font-display text-lg font-extrabold">Mon Livre de Vie</span>
          {!loading && total > 0 && (
            <span className="ml-3 text-xs text-cream/60 font-mono" data-testid="feuilleter-page-counter">
              Page {idx + 1} / {total}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onDownloadPdf && !isEmpty && (
            <button
              type="button"
              onClick={onDownloadPdf}
              data-testid="feuilleter-download-pdf"
              className="inline-flex items-center gap-1 bg-mustard text-navy font-bold text-xs px-3 py-1.5 rounded-full hover:bg-mustard-dark transition"
              title="Télécharger le PDF pour l'imprimer chez vous ou l'offrir"
            >
              <Download className="w-3.5 h-3.5" /> Télécharger le PDF
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            data-testid="feuilleter-close"
            className="p-2 rounded-full hover:bg-cream/10 transition"
            aria-label="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Contenu */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center px-4 py-6">
        {/* Boutons latéraux */}
        {!loading && total > 1 && idx > 0 && (
          <button
            type="button"
            onClick={() => go(-1)}
            data-testid="feuilleter-prev"
            aria-label="Page précédente"
            className="absolute left-2 sm:left-6 top-1/2 -translate-y-1/2 z-10 w-12 h-12 rounded-full bg-white/95 text-navy shadow-lg hover:bg-mustard hover:scale-105 transition flex items-center justify-center"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>
        )}
        {!loading && total > 1 && idx < total - 1 && (
          <button
            type="button"
            onClick={() => go(1)}
            data-testid="feuilleter-next"
            aria-label="Page suivante"
            className="absolute right-2 sm:right-6 top-1/2 -translate-y-1/2 z-10 w-12 h-12 rounded-full bg-white/95 text-navy shadow-lg hover:bg-mustard hover:scale-105 transition flex items-center justify-center"
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        )}

        {loading && (
          <div className="text-cream/70 text-center" data-testid="feuilleter-loading">
            <div className="inline-block w-6 h-6 border-2 border-cream/40 border-t-mustard rounded-full animate-spin mb-3" />
            <p>Ouverture de votre livre…</p>
          </div>
        )}
        {err && !loading && (
          <div className="text-cream/70 text-center" data-testid="feuilleter-error">
            <p>Impossible d&apos;ouvrir votre livre pour l&apos;instant.</p>
            <p className="text-xs mt-2 text-cream/50">{String(err).slice(0, 200)}</p>
          </div>
        )}
        {isEmpty && !loading && !err && (
          <EmptyBook onClose={onClose} />
        )}

        {!loading && !err && !isEmpty && page && (
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={idx}
              custom={direction}
              variants={pageVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.35, ease: "easeInOut" }}
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.2}
              onDragEnd={(_e, info) => {
                if (info.offset.x < -60) go(1);
                else if (info.offset.x > 60) go(-1);
              }}
              className="w-full max-w-2xl h-full max-h-[80vh] flex items-stretch justify-center"
            >
              <PageFrame>
                <PageContent page={page} />
              </PageFrame>
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Table des matières horizontale */}
      {!loading && !err && !isEmpty && total > 1 && (
        <div className="px-4 pb-4 pt-2 bg-navy text-cream/80 overflow-x-auto">
          <div className="flex gap-1 justify-center min-w-max" data-testid="feuilleter-toc">
            {pages.map((p, i) => (
              <button
                key={i}
                type="button"
                onClick={() => jumpTo(i)}
                data-testid={`feuilleter-toc-${i}`}
                title={p.label || `Page ${i + 1}`}
                className={`h-2 rounded-full transition-all ${
                  i === idx ? "w-8 bg-mustard" : "w-2 bg-cream/30 hover:bg-cream/60"
                }`}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Construction des pages
// ---------------------------------------------------------------------------
function buildPages(data, user) {
  if (!data || !data.chapters) return [];
  const pages = [];
  const author = user?.name || "Vous";
  const year = new Date().getFullYear();

  // Page 0 : couverture
  pages.push({ type: "cover", author, year, label: "Couverture" });

  for (const ch of data.chapters) {
    if (!ch.entries || ch.entries.length === 0) continue;
    // Page titre du chapitre
    pages.push({
      type: "chapter",
      chapter_id: ch.id,
      order: ch.order,
      label: ch.label,
      emoji: ch.emoji,
      count: ch.entries.length,
    });
    // 1 entrée = 1 page (mémoire modeste, lecture confortable)
    for (const e of ch.entries) {
      pages.push({
        type: "entry",
        chapter_label: ch.label,
        chapter_emoji: ch.emoji,
        order: ch.order,
        label: `${ch.label} — souvenir`,
        entry: e,
      });
    }
  }

  // Page finale
  pages.push({ type: "end", author, year, label: "Fin" });
  return pages;
}

// ---------------------------------------------------------------------------
// Composants
// ---------------------------------------------------------------------------
function PageFrame({ children }) {
  return (
    <div className="relative bg-cream text-navy w-full h-full rounded-lg shadow-2xl overflow-hidden flex flex-col paper-texture">
      {/* Reliure gauche */}
      <div className="absolute inset-y-0 left-0 w-2 bg-gradient-to-r from-black/25 via-black/10 to-transparent pointer-events-none" />
      {/* Tranche haut/bas */}
      <div className="absolute inset-x-0 top-0 h-2 bg-gradient-to-b from-black/10 to-transparent pointer-events-none" />
      <div className="absolute inset-x-0 bottom-0 h-2 bg-gradient-to-t from-black/10 to-transparent pointer-events-none" />
      <div className="flex-1 overflow-y-auto p-8 sm:p-12">{children}</div>
    </div>
  );
}

function PageContent({ page }) {
  if (page.type === "cover")   return <CoverPage page={page} />;
  if (page.type === "chapter") return <ChapterPage page={page} />;
  if (page.type === "entry")   return <EntryPage page={page} />;
  if (page.type === "end")     return <EndPage page={page} />;
  return null;
}

function CoverPage({ page }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center" data-testid="feuilleter-page-cover">
      <Sparkles className="w-10 h-10 text-terracotta mb-6" />
      <div className="text-xs uppercase tracking-[0.3em] text-navy/60 mb-3">Mon Livre de Vie</div>
      <h1 className="font-display text-5xl sm:text-6xl font-extrabold text-navy leading-tight mb-6">
        Mes souvenirs.<br />
        <span className="text-terracotta italic">Mon histoire.</span>
      </h1>
      <div className="w-24 h-1 bg-mustard rounded-full my-6" />
      <p className="text-lg text-navy/70 italic">Écrit par</p>
      <p className="font-display text-2xl font-bold text-navy mt-1">{page.author}</p>
      <p className="text-sm text-navy/50 mt-8">{page.year}</p>
    </div>
  );
}

function ChapterPage({ page }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center" data-testid={`feuilleter-page-chapter-${page.chapter_id}`}>
      <div className="text-xs uppercase tracking-[0.3em] text-navy/50 mb-4">Chapitre {page.order}</div>
      <div className="text-6xl mb-4">{page.emoji}</div>
      <h2 className="font-display text-4xl sm:text-5xl font-extrabold text-navy mb-4">
        {page.label}
      </h2>
      <div className="w-16 h-0.5 bg-terracotta rounded-full my-4" />
      <p className="text-navy/60 text-sm">
        {page.count} souvenir{page.count > 1 ? "s" : ""} dans ce chapitre
      </p>
    </div>
  );
}

function EntryPage({ page }) {
  const { entry, chapter_emoji, chapter_label, order } = page;
  const backend = process.env.REACT_APP_BACKEND_URL;
  const authorNote = entry.mode === "delegated" && entry.delegated_author_name
    ? `Raconté par ${entry.delegated_author_name}` : null;
  return (
    <div className="h-full flex flex-col" data-testid={`feuilleter-page-entry-${entry.id || ""}`}>
      <div className="flex items-center justify-between text-xs text-navy/50 uppercase tracking-widest mb-6">
        <span>{chapter_emoji} {chapter_label}</span>
        <span>Chap. {order}</span>
      </div>
      {entry.prompt_text && (
        <div className="mb-5 border-l-4 border-terracotta pl-4">
          <div className="text-[10px] uppercase tracking-widest text-terracotta font-bold mb-1">La question</div>
          <p className="font-display text-lg text-navy/80 italic">« {entry.prompt_text} »</p>
        </div>
      )}
      {entry.text && (
        <div className="prose prose-navy max-w-none flex-1">
          <p className="font-serif text-lg leading-relaxed text-navy whitespace-pre-wrap first-letter:font-display first-letter:text-5xl first-letter:font-extrabold first-letter:text-terracotta first-letter:mr-1 first-letter:float-left first-letter:leading-none">
            {entry.text}
          </p>
        </div>
      )}
      {(!entry.text && entry.audio_b64) && (
        <div className="flex-1 flex flex-col items-center justify-center">
          <p className="text-navy/60 italic mb-3">Souvenir audio (transcription à venir)</p>
          <audio controls src={`data:audio/webm;base64,${entry.audio_b64}`} className="w-full max-w-md" />
        </div>
      )}
      {entry.photos && entry.photos.length > 0 && (
        <div className={`mt-5 grid gap-3 ${entry.photos.length === 1 ? "grid-cols-1" : "grid-cols-2 sm:grid-cols-3"}`}>
          {entry.photos.map((p, i) => (
            <figure key={i} className="rounded-lg overflow-hidden border-2 border-navy/10 bg-white">
              <img
                src={p.b64 ? `data:image/jpeg;base64,${p.b64}` : `${backend}${p.url || ""}`}
                alt={p.caption || ""}
                className="w-full aspect-square object-cover"
                loading="lazy"
              />
              {p.caption && (
                <figcaption className="text-xs italic text-navy/60 p-2 text-center">{p.caption}</figcaption>
              )}
            </figure>
          ))}
        </div>
      )}
      <div className="mt-6 text-xs text-navy/50 flex items-center justify-between">
        {authorNote && <span>{authorNote}</span>}
        {entry.created_at && (
          <span className="ml-auto">
            {new Date(entry.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
          </span>
        )}
      </div>
    </div>
  );
}

function EndPage({ page }) {
  return (
    <div className="h-full flex flex-col items-center justify-center text-center" data-testid="feuilleter-page-end">
      <div className="text-6xl mb-4">🌳</div>
      <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-navy mb-3">
        À suivre…
      </h2>
      <p className="text-navy/70 max-w-md text-lg leading-relaxed mb-6">
        Chaque souvenir est une racine. Ce livre continue de grandir à mesure
        que vous écrivez.
      </p>
      <p className="text-sm text-navy/50 italic">— {page.author}, {page.year}</p>
      <div className="w-24 h-1 bg-mustard rounded-full mt-6" />
    </div>
  );
}

function EmptyBook({ onClose }) {
  return (
    <div className="max-w-md bg-cream rounded-3xl p-8 text-center shadow-2xl" data-testid="feuilleter-empty">
      <BookOpen className="w-14 h-14 text-terracotta mx-auto mb-4" />
      <h3 className="font-display text-2xl font-extrabold text-navy mb-3">
        Votre livre est encore vierge
      </h3>
      <p className="text-navy/70 mb-5">
        Répondez à votre première question pour ouvrir la première page — le
        reste viendra tout naturellement.
      </p>
      <button
        type="button"
        onClick={onClose}
        data-testid="feuilleter-empty-close"
        className="bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark transition"
      >
        Commencer à écrire
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animations
// ---------------------------------------------------------------------------
const pageVariants = {
  enter: (direction) => ({
    x: direction > 0 ? 100 : -100,
    opacity: 0,
    rotateY: direction > 0 ? -8 : 8,
  }),
  center: { x: 0, opacity: 1, rotateY: 0 },
  exit: (direction) => ({
    x: direction > 0 ? -100 : 100,
    opacity: 0,
    rotateY: direction > 0 ? 8 : -8,
  }),
};
