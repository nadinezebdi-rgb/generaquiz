import { MessageCircle } from "lucide-react";

export const whatsappHref = (tip) =>
  `https://wa.me/?text=${encodeURIComponent(
    `${tip.title} — le conseil du jour de Lucette 💚\n${tip.text}\n\nTestez-vous avec le quiz Bien vieillir : ${tip.share_url}`
  )}`;

export const ShareTipButton = ({ tip, testId = "share-tip-whatsapp" }) => {
  if (!tip?.share_url) return null;
  return (
    <a
      href={whatsappHref(tip)}
      target="_blank"
      rel="noopener noreferrer"
      data-testid={testId}
      className="inline-flex items-center gap-2 bg-[#25D366] text-white font-bold px-5 py-2.5 rounded-full hover:bg-[#1ebe5a] transition-colors shadow-soft"
    >
      <MessageCircle className="w-4 h-4" /> Partager sur WhatsApp
    </a>
  );
};
