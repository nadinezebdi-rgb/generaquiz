import { MessageCircle, Facebook } from "lucide-react";

export const whatsappHref = (tip) =>
  `https://wa.me/?text=${encodeURIComponent(
    `${tip.title} — le conseil du jour de Lucette 💚\n${tip.text}\n\nTestez-vous avec le quiz Bien vieillir : ${tip.share_url}`
  )}`;

export const facebookHref = (url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;

const BTN = "inline-flex items-center gap-2 text-white font-bold px-5 py-2.5 rounded-full transition-colors shadow-soft";

export const ShareTipButton = ({ tip, testId = "share-tip-whatsapp" }) => {
  if (!tip?.share_url) return null;
  return (
    <>
      <a href={whatsappHref(tip)} target="_blank" rel="noopener noreferrer" data-testid={testId} className={`${BTN} bg-[#25D366] hover:bg-[#1ebe5a]`}>
        <MessageCircle className="w-4 h-4" /> Partager sur WhatsApp
      </a>
      <a
        href={facebookHref(tip.share_url)}
        target="_blank"
        rel="noopener noreferrer"
        data-testid={testId.replace("whatsapp", "facebook").replace(/^tip-share-/, "tip-share-facebook-")}
        className={`${BTN} bg-[#1877F2] hover:bg-[#0f63d1]`}
      >
        <Facebook className="w-4 h-4" /> Partager sur Facebook
      </a>
    </>
  );
};
