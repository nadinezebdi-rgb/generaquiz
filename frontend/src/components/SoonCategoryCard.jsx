import { Clock } from "lucide-react";

/** Carte non cliquable « Bientôt » (badge au style « En dev. » de l'accueil). */
export const SoonCategoryCard = ({ item, testidPrefix }) => (
  <div
    aria-disabled="true"
    data-testid={`${testidPrefix}-${item.id}`}
    className="relative bg-cream/50 border-2 border-dashed border-cream-dark rounded-[28px] p-6 flex flex-col justify-center min-h-[180px] select-none"
  >
    <span className="absolute top-3 right-3 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-navy/40" data-testid={`${testidPrefix}-badge-${item.id}`}>
      <Clock className="w-3 h-3" /> Bientôt
    </span>
    <h3 className="font-display text-xl sm:text-2xl font-bold text-navy/50 mb-2">{item.title}</h3>
    <p className="text-navy/50 text-base">{item.description}</p>
  </div>
);
