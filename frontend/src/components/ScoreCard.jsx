import { useRef, useState } from "react";
import * as htmlToImage from "html-to-image";
import { Download, Share2, Loader2, Flame, Trophy } from "lucide-react";
import { toast } from "sonner";
import { BACKEND_URL } from "@/lib/api";

/**
 * ScoreCard
 * --------
 * Self-contained visual card + actions (Download PNG / Share to socials).
 * Used at the end of QuizPlayer, ChallengePlay and DailyQuiz.
 *
 * Props:
 *  - title: string (e.g., "Cinéma", "Quiz du Jour", "Défi Famille")
 *  - score: number
 *  - total: number
 *  - playerName?: string
 *  - mascotImage?: string (relative or absolute URL)
 *  - mascotName?: string
 *  - streak?: number       — display flame badge if >= 1
 *  - subtitle?: string     — short tag line (e.g., date or "5 questions au choix")
 *  - shareText?: string    — text used by Web Share API
 *  - shareUrl?: string     — defaults to current origin
 */
export default function ScoreCard({
  title,
  score,
  total,
  playerName,
  mascotImage,
  mascotName,
  streak,
  subtitle,
  shareText,
  shareUrl,
}) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);

  const ratio = total > 0 ? score / total : 0;
  const verdict =
    ratio === 1 ? "Sans-faute !" : ratio >= 0.7 ? "Bravo !" : ratio >= 0.4 ? "Belle tentative" : "À reprendre";
  const emoji = ratio === 1 ? "🏆" : ratio >= 0.7 ? "⭐" : ratio >= 0.4 ? "💪" : "🎯";

  // Resolve mascot URL (handles both absolute and /api/... relative paths)
  const mascotSrc = mascotImage
    ? mascotImage.startsWith("http") ? mascotImage : `${BACKEND_URL}${mascotImage}`
    : null;

  const buildImageBlob = async () => {
    if (!ref.current) return null;
    // Use a robust PNG conversion. cacheBust avoids stale CORS-blocked mascot image.
    const dataUrl = await htmlToImage.toPng(ref.current, {
      cacheBust: true,
      pixelRatio: 2,
      backgroundColor: "#F4F1DE",
      filter: (node) => !node.dataset?.exclude,
    });
    const res = await fetch(dataUrl);
    return res.blob();
  };

  const download = async () => {
    setBusy(true);
    try {
      const blob = await buildImageBlob();
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `generaquiz-${title.toLowerCase().replace(/\s+/g, "-")}-${score}sur${total}.png`;
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
      const blob = await buildImageBlob();
      if (!blob) return;
      const file = new File([blob], "generaquiz-score.png", { type: "image/png" });
      const url = shareUrl || window.location.origin;
      const text = shareText || `J'ai fait ${score}/${total} sur GénéraQuiz — ${title} ! Saurez-vous battre mon score ?`;

      // Try native Web Share API with file (works on mobile)
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: "Mon score GénéraQuiz",
          text,
          url,
        });
        return;
      }
      // Fallback: copy to clipboard then download
      try {
        if (navigator.clipboard && window.ClipboardItem) {
          await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
          toast.success("Image copiée ! Collez-la dans WhatsApp ou Messenger.");
          return;
        }
      } catch { /* clipboard refused */ }

      // Last-resort fallback: download the image
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = dlUrl;
      a.download = `generaquiz-score.png`;
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
    const text = shareText || `🎯 J'ai fait ${score}/${total} sur *GénéraQuiz — ${title}* !\nVenez tester votre culture sur ${shareUrl || window.location.origin}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank");
  };

  return (
    <div className="space-y-4" data-testid="score-card-wrapper">
      {/* ============ VISUAL CARD (this is what gets converted to PNG) ============ */}
      <div
        ref={ref}
        data-testid="score-card-visual"
        style={{
          // Inline styles so html-to-image captures them reliably (CSS variables can fail).
          width: 540,
          maxWidth: "100%",
          margin: "0 auto",
          padding: 28,
          borderRadius: 28,
          background: "linear-gradient(135deg, #F4F1DE 0%, #FCE7B6 100%)",
          border: "4px solid #1E3A5F",
          boxShadow: "0 14px 40px -10px rgba(30,58,95,0.35)",
          color: "#1A2530",
          fontFamily: "'Fraunces', Georgia, serif",
        }}
      >
        {/* Brand header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 999,
              background: "#7A1F2B", color: "#FCE7B6",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 800, fontSize: 20, fontFamily: "'Fraunces', Georgia, serif",
            }}>GQ</div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 20, color: "#1A2530", letterSpacing: -0.5 }}>GénéraQuiz</div>
              <div style={{ fontSize: 12, color: "#1E3A5F", opacity: 0.7 }}>Le jeu qui rapproche les générations</div>
            </div>
          </div>
          {streak >= 2 && (
            <div data-exclude style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              background: "#E07A5F", color: "#FFF", padding: "6px 12px",
              borderRadius: 999, fontSize: 13, fontWeight: 800, fontFamily: "'Fraunces', Georgia, serif",
            }}>🔥 {streak} jours</div>
          )}
        </div>

        {/* Title */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#1E3A5F", opacity: 0.65, textTransform: "uppercase", letterSpacing: 1.2 }}>
            {subtitle || "Mon résultat"}
          </div>
          <div style={{ fontSize: 30, fontWeight: 800, color: "#1A2530", lineHeight: 1.1, marginTop: 4 }}>{title}</div>
        </div>

        {/* Score block + mascot */}
        <div style={{ display: "flex", alignItems: "center", gap: 20, padding: 20, background: "#FFF", borderRadius: 20, border: "2px solid #E8E2C9" }}>
          {mascotSrc && (
            <img
              src={mascotSrc}
              alt={mascotName || ""}
              crossOrigin="anonymous"
              style={{ width: 90, height: 90, borderRadius: 16, objectFit: "cover", border: "2px solid #E8E2C9", flexShrink: 0 }}
            />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, color: "#1E3A5F", opacity: 0.65, marginBottom: 4 }}>
              {playerName ? `Joueur : ${playerName}` : "Mon score"}
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontSize: 56, fontWeight: 900, color: "#7A1F2B", lineHeight: 1, fontFamily: "'Fraunces', Georgia, serif" }}>{score}</span>
              <span style={{ fontSize: 24, fontWeight: 700, color: "#1E3A5F", opacity: 0.5 }}>/ {total}</span>
              <span style={{ fontSize: 32, marginLeft: 8 }}>{emoji}</span>
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#1A2530", marginTop: 4 }}>{verdict}</div>
          </div>
        </div>

        {/* CTA strip */}
        <div style={{
          marginTop: 18, padding: "12px 18px", background: "#1E3A5F", color: "#F4F1DE",
          borderRadius: 14, fontSize: 13, fontWeight: 600,
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>👉 Jouez aussi sur</span>
          <span style={{ fontWeight: 800, color: "#FCE7B6" }}>generaquiz.fr</span>
        </div>
      </div>

      {/* ============ ACTION BUTTONS (excluded from image) ============ */}
      <div className="flex flex-wrap gap-3 justify-center" data-exclude>
        <button
          type="button"
          onClick={share}
          disabled={busy}
          data-testid="score-share-btn"
          className="inline-flex items-center gap-2 bg-terracotta hover:bg-terracotta-dark disabled:opacity-60 text-white font-bold px-6 py-3 rounded-full shadow-warm transition min-h-[52px]"
        >
          {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Share2 className="w-5 h-5" />}
          Partager mon score
        </button>
        <button
          type="button"
          onClick={whatsappShare}
          disabled={busy}
          data-testid="score-whatsapp-btn"
          className="inline-flex items-center gap-2 bg-[#25D366] hover:bg-[#1FB155] text-white font-bold px-6 py-3 rounded-full shadow-warm transition min-h-[52px]"
          aria-label="Partager sur WhatsApp"
        >
          <span aria-hidden="true" className="text-lg">💬</span>
          WhatsApp
        </button>
        <button
          type="button"
          onClick={download}
          disabled={busy}
          data-testid="score-download-btn"
          className="inline-flex items-center gap-2 bg-white border-2 border-navy text-navy hover:bg-navy hover:text-white font-bold px-6 py-3 rounded-full transition min-h-[52px]"
        >
          {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
          Télécharger l&apos;image
        </button>
      </div>
    </div>
  );
}

// Re-export icons so consumers can compose without importing lucide directly
ScoreCard.Flame = Flame;
ScoreCard.Trophy = Trophy;
