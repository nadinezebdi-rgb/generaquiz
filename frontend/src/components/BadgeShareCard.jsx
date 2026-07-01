import { useRef, useState } from "react";
import * as htmlToImage from "html-to-image";
import { Download, Share2, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

/**
 * BadgeShareCard — visual card + share actions for a single unlocked badge.
 *
 * Reuses the same html-to-image PNG generation pipeline as ScoreCard.
 * Props:
 *   badge:      { id, title, desc, emoji, tier }
 *   playerName: string
 *   earnedAt?:  ISO date string
 *   shareUrl?:  string (defaults to window.origin)
 */
const TIER_STYLES = {
  bronze:  { bg: "#B87333", ring: "#8A5527" },
  argent:  { bg: "#9CA3AF", ring: "#6B7280" },
  or:      { bg: "#D4A24A", ring: "#8C6520" },
  diamant: { bg: "#3FB8AF", ring: "#2A8B86" },
};

export default function BadgeShareCard({ badge, playerName, earnedAt, shareUrl }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);

  const tier = TIER_STYLES[badge?.tier] || TIER_STYLES.bronze;
  const firstName = (playerName || "Un joueur").split(" ")[0];
  const shareText = `🎉 ${firstName} a débloqué le badge « ${badge.title} » ${badge.emoji} sur GénéraQuiz ! Venez me défier.`;

  const buildBlob = async () => {
    if (!ref.current) return null;
    const dataUrl = await htmlToImage.toPng(ref.current, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: "#F4F1DE",
      skipFonts: true,
      filter: (node) => !node.dataset?.exclude,
    });
    const res = await fetch(dataUrl);
    return res.blob();
  };

  const download = async () => {
    setBusy(true);
    try {
      const blob = await buildBlob();
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `generaquiz-badge-${badge.id}.png`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Image enregistrée !");
    } catch (e) {
      console.error(e);
      toast.error("Impossible de générer l'image");
    } finally {
      setBusy(false);
    }
  };

  const share = async () => {
    setBusy(true);
    try {
      const blob = await buildBlob();
      if (!blob) return;
      const file = new File([blob], `generaquiz-badge-${badge.id}.png`, { type: "image/png" });
      const url = shareUrl || window.location.origin;
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "Mon exploit GénéraQuiz", text: shareText, url });
        return;
      }
      try {
        if (navigator.clipboard && window.ClipboardItem) {
          await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
          toast.success("Image copiée ! Collez-la dans WhatsApp ou Messenger.");
          return;
        }
      } catch { /* clipboard refused */ }
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = dlUrl;
      a.download = `generaquiz-badge-${badge.id}.png`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(dlUrl);
      toast.success("Image téléchargée. Partagez-la depuis votre galerie !");
    } catch (e) {
      if (e.name !== "AbortError") {
        console.error(e);
        toast.error("Partage impossible — image téléchargée à la place");
      }
    } finally {
      setBusy(false);
    }
  };

  const whatsappShare = () => {
    const url = shareUrl || window.location.origin;
    const text = `${shareText}\n${url}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
  };

  const dateLabel = earnedAt
    ? new Date(earnedAt).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    : new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });

  return (
    <div className="space-y-4" data-testid="badge-share-wrapper">
      {/* ---- VISUAL CARD (this is what gets converted to PNG) ---- */}
      <div
        ref={ref}
        data-testid="badge-share-visual"
        style={{ width: "100%", maxWidth: 520, margin: "0 auto" }}
        className="bg-navy text-cream rounded-[36px] p-8 relative overflow-hidden shadow-warm"
      >
        <div
          className="absolute -top-24 -right-24 w-80 h-80 rounded-full blur-3xl pointer-events-none"
          style={{ background: `${tier.bg}55` }}
        />
        {/* Header — brand */}
        <div className="flex items-center justify-between mb-8 relative">
          <div className="inline-flex items-center gap-2 bg-white/10 text-cream font-bold px-3 py-1.5 rounded-full text-xs uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5 text-mustard" /> GénéraQuiz · Exploit
          </div>
          <div className="text-xs text-cream/60">{dateLabel}</div>
        </div>

        {/* Big badge emoji */}
        <div className="flex flex-col items-center text-center relative">
          <div
            className="w-40 h-40 rounded-full flex items-center justify-center mb-6 shadow-warm"
            style={{
              background: tier.bg,
              boxShadow: `0 0 0 12px ${tier.ring}55, 0 20px 40px rgba(0,0,0,0.3)`,
            }}
          >
            <span style={{ fontSize: 84, lineHeight: 1 }}>{badge.emoji}</span>
          </div>

          <div
            className="inline-block text-xs font-extrabold uppercase tracking-widest px-3 py-1 rounded-full mb-3"
            style={{ background: tier.bg, color: "#1A2530" }}
          >
            Palier {badge.tier}
          </div>

          <h2 className="font-display font-extrabold leading-tight mb-2" style={{ fontSize: 44 }}>
            {badge.title}
          </h2>
          <p className="text-cream/80 text-lg mb-6">{badge.desc}</p>

          <div className="w-full bg-white/10 rounded-2xl p-4 mt-2">
            <div className="text-xs uppercase tracking-widest text-mustard font-bold mb-1">Débloqué par</div>
            <div className="font-display font-extrabold text-mustard" style={{ fontSize: 32 }}>
              {firstName}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-cream/60 text-xs mt-6 relative">
          generaquiz.fr · Le jeu qui rapproche les générations
        </div>
      </div>

      {/* ---- ACTIONS (excluded from PNG capture) ---- */}
      <div data-exclude className="grid grid-cols-3 gap-2 max-w-[520px] mx-auto">
        <button
          onClick={share}
          disabled={busy}
          data-testid="badge-share-btn"
          className="inline-flex items-center justify-center gap-2 bg-terracotta hover:bg-terracotta-dark text-white font-bold px-3 py-3 rounded-full shadow-warm min-h-[52px] disabled:opacity-60 transition"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
          Partager
        </button>
        <button
          onClick={whatsappShare}
          data-testid="badge-share-whatsapp"
          className="inline-flex items-center justify-center gap-2 bg-[#25D366] hover:bg-[#1EA34F] text-white font-bold px-3 py-3 rounded-full min-h-[52px] transition"
        >
          WhatsApp
        </button>
        <button
          onClick={download}
          disabled={busy}
          data-testid="badge-share-download"
          className="inline-flex items-center justify-center gap-2 bg-white border-2 border-navy hover:bg-cream text-navy font-bold px-3 py-3 rounded-full min-h-[52px] disabled:opacity-60 transition"
        >
          <Download className="w-4 h-4" />
          Télécharger
        </button>
      </div>
    </div>
  );
}
