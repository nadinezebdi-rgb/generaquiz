import { Link } from "react-router-dom";

/**
 * Modern GénéraQuiz logo — two overlapping circles symbolizing
 * the two generations the app connects, with "GQ" monogram in the middle.
 */
export default function Logo({ size = "md", showTagline = true, asLink = true, dark = false }) {
  const sizes = {
    sm: { svg: "w-9 h-9", title: "text-lg", tag: "text-[10px]" },
    md: { svg: "w-11 h-11", title: "text-2xl", tag: "text-xs" },
    lg: { svg: "w-16 h-16", title: "text-4xl", tag: "text-sm" },
  };
  const s = sizes[size] || sizes.md;
  const titleColor = dark ? "text-cream" : "text-navy";
  const tagColor = dark ? "text-cream/70" : "text-navy/60";

  const content = (
    <div className="flex items-center gap-3 group">
      <svg className={`${s.svg} shrink-0 transition-transform group-hover:scale-105`} viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <linearGradient id="gq-grad-1" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#F2A78F" />
            <stop offset="100%" stopColor="#E07A5F" />
          </linearGradient>
          <linearGradient id="gq-grad-2" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#2D4D74" />
            <stop offset="100%" stopColor="#1E3A5F" />
          </linearGradient>
        </defs>
        <circle cx="22" cy="30" r="18" fill="url(#gq-grad-1)" />
        <circle cx="38" cy="30" r="18" fill="url(#gq-grad-2)" fillOpacity="0.94" />
        <text x="30" y="38.5" textAnchor="middle" fill="#F2CC8F" fontSize="20" fontWeight="800" fontFamily="'Playfair Display', Georgia, serif">GQ</text>
      </svg>
      <div className="leading-tight">
        <div className={`font-display ${s.title} font-extrabold ${titleColor} tracking-tight`}>
          Généra<span className="text-terracotta">Quiz</span>
        </div>
        {showTagline && (
          <div className={`${s.tag} ${tagColor} font-medium tracking-wide`}>
            Le jeu qui rapproche les générations
          </div>
        )}
      </div>
    </div>
  );

  if (!asLink) return content;
  return (
    <Link to="/" className="inline-flex items-center" data-testid="navbar-logo">
      {content}
    </Link>
  );
}
