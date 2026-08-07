import { useRef, useState } from "react";
import * as htmlToImage from "html-to-image";
import { Download, Share2, Loader2, Sparkles, HandHelping, Flame, Trophy, Users } from "lucide-react";
import { toast } from "sonner";

/**
 * CoopShareCard — shareable PNG card summarizing a completed coop challenge.
 * Highlights the "Complicité %" metric (a proxy of team cohesion) and the
 * best combo streak achieved by the duo.
 */
const COMPLICITY_TIERS = [
  { min: 95, title: "Fusion Temporelle Parfaite", emoji: "✨🧡" },
  { min: 85, title: "Duo Légendaire",              emoji: "🌟" },
  { min: 70, title: "Complices de Toujours",       emoji: "🤝" },
  { min: 50, title: "Belle Équipe",                emoji: "👍" },
  { min: 0,  title: "Duo en Rodage",               emoji: "🌱" },
];


export default function CoopShareCard({ challenge, complicityPct, tier, onShareClose }) {
  const s = challenge.stats_coop || {};
  const total = challenge.total;
  const totalXp = s.total_xp || 0;
  const correct = s.correct_count || 0;
  const helpsUsed = s.helps_used || 0;
  const helpsOk = s.helps_successful || 0;
  const bestCombo = s.best_combo || 0;

  const ref = useRef(null);
  const [busy, setBusy] = useState(false);

  const p1 = challenge.players?.[0]?.name || "Joueur 1";
  const p2 = challenge.players?.[1]?.name || "Joueur 2";

  const buildBlob = async () => {
    if (!ref.current) return null;
    const dataUrl = await htmlToImage.toPng(ref.current, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: "#F4F1DE",
      skipFonts: true,
      filter: (n) => !n.dataset?.exclude,
    });
    const res = await fetch(dataUrl);
    return res.blob();
  };

  const share = async () => {
    setBusy(true);
    try {
      const blob = await buildBlob();
      const file = new File([blob], `generaquiz-coop-${challenge.token}.png`, { type: "image/png" });
      const text = `🎉 ${p1} et ${p2} ont atteint ${complicityPct}% de complicité sur GénéraQuiz ! ${tier.emoji}`;
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "Notre défi GénéraQuiz", text, url: "https://generaquiz.fr" });
        return;
      }
      try {
        if (navigator.clipboard && window.ClipboardItem) {
          await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
          toast.success("Image copiée ! Collez-la sur WhatsApp.");
          return;
        }
      } catch { /* clipboard blocked */ }
      // Fallback: download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `generaquiz-coop-${challenge.token}.png`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Image téléchargée !");
    } catch (e) {
      if (e.name !== "AbortError") toast.error("Partage impossible");
    } finally {
      setBusy(false);
    }
  };

  const download = async () => {
    setBusy(true);
    try {
      const blob = await buildBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `generaquiz-coop-${challenge.token}.png`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Image téléchargée !");
    } catch {
      toast.error("Téléchargement impossible");
    } finally {
      setBusy(false);
    }
  };

  const whatsapp = () => {
    const text = `🎉 ${p1} et ${p2} ont atteint ${complicityPct}% de complicité sur GénéraQuiz ! ${tier.emoji}\nhttps://generaquiz.fr`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
  };

  return (
    <div className="space-y-4" data-testid="coop-share-wrapper">
      <div
        ref={ref}
        data-testid="coop-share-visual"
        style={{ width: "100%", maxWidth: 540, margin: "0 auto" }}
        className="bg-navy text-cream rounded-[36px] p-8 relative overflow-hidden shadow-warm"
      >
        <div className="absolute -top-16 -right-16 w-72 h-72 rounded-full bg-mustard/25 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-72 h-72 rounded-full bg-terracotta/20 blur-3xl pointer-events-none" />

        <div className="flex items-center justify-between mb-6 relative">
          <div className="inline-flex items-center gap-2 bg-white/10 text-cream font-bold px-3 py-1.5 rounded-full text-xs uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-mustard" /> GénéraQuiz · Duo
          </div>
          <div className="text-xs text-cream/60">
            {new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}
          </div>
        </div>

        <div className="text-center relative mb-6">
          <div className="text-xs font-bold uppercase tracking-widest text-mustard mb-1">Complicité</div>
          <div
            className="font-display font-extrabold text-mustard leading-none mb-2"
            style={{ fontSize: 96 }}
            data-testid="coop-share-complicity"
          >
            {complicityPct}%
          </div>
          <div className="inline-block bg-mustard text-navy font-extrabold text-lg px-4 py-1.5 rounded-full">
            {tier.emoji} {tier.title}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-6 relative">
          <div className="bg-white/10 rounded-2xl p-3 text-center">
            <div className="text-xs uppercase tracking-widest text-cream/70">Bonnes réponses</div>
            <div className="font-display text-2xl font-extrabold text-cream">{correct} / {total}</div>
          </div>
          <div className="bg-white/10 rounded-2xl p-3 text-center">
            <div className="text-xs uppercase tracking-widest text-cream/70">Combo max</div>
            <div className="font-display text-2xl font-extrabold text-cream">🔥 {bestCombo}</div>
          </div>
          <div className="bg-white/10 rounded-2xl p-3 text-center">
            <div className="text-xs uppercase tracking-widest text-cream/70">Aides réussies</div>
            <div className="font-display text-2xl font-extrabold text-cream">{helpsOk} / {helpsUsed}</div>
          </div>
          <div className="bg-white/10 rounded-2xl p-3 text-center">
            <div className="text-xs uppercase tracking-widest text-cream/70">Points</div>
            <div className="font-display text-2xl font-extrabold text-cream">{totalXp}</div>
          </div>
        </div>

        <div className="bg-terracotta/20 border-2 border-terracotta/40 rounded-2xl p-3 text-center relative">
          <div className="text-xs uppercase tracking-widest text-mustard mb-1">Le duo</div>
          <div className="font-display text-lg font-extrabold text-cream">
            {p1} <span className="text-mustard">+</span> {p2}
          </div>
          <div className="text-xs text-cream/70 mt-0.5">
            <em>&laquo; {challenge.team_name} &raquo;</em>
          </div>
        </div>

        <div className="text-center text-cream/60 text-xs mt-6 relative">
          generaquiz.fr · Le jeu qui rapproche les générations
        </div>
      </div>

      <div data-exclude className="grid grid-cols-3 gap-2 max-w-[540px] mx-auto">
        <button
          onClick={share}
          disabled={busy}
          data-testid="coop-share-btn"
          className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-3 py-3 rounded-full shadow-warm min-h-[52px] disabled:opacity-60 transition"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
          Partager
        </button>
        <button
          onClick={whatsapp}
          data-testid="coop-share-whatsapp"
          className="inline-flex items-center justify-center gap-2 bg-[#25D366] hover:bg-[#1EA34F] text-white font-bold px-3 py-3 rounded-full min-h-[52px] transition"
        >
          WhatsApp
        </button>
        <button
          onClick={download}
          disabled={busy}
          data-testid="coop-share-download"
          className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy hover:bg-cream text-navy font-bold px-3 py-3 rounded-full min-h-[52px] disabled:opacity-60 transition"
        >
          <Download className="w-4 h-4" />
          Télécharger
        </button>
      </div>
    </div>
  );
}

/** Helper used both by FinalResults and CoopShareCard so both agree on the tier. */
export function computeComplicity(challenge) {
  const s = challenge.stats_coop || {};
  const total = challenge.total || 0;
  const correct = s.correct_count || 0;
  const helpsOk = s.helps_successful || 0;
  const solo = s.solo_correct_count ?? Math.max(0, correct - helpsOk);
  // Weighted: 100% solo = 100, 100% with help but rescued = ~75, wrong = 0
  const weighted = total > 0 ? Math.round((solo + helpsOk * 0.75) / total * 100) : 0;
  const pct = Math.min(100, Math.max(0, weighted));
  const tier = COMPLICITY_TIERS.find((t) => pct >= t.min) || COMPLICITY_TIERS.at(-1);
  return { pct, tier };
}
