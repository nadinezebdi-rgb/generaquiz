import { useSeniorMode } from "@/contexts/SeniorModeContext";
import { Type } from "lucide-react";

/**
 * SeniorModeToggle — accessible size/contrast switch visible in the Navbar
 * on every page. Keyboard focusable, aria-pressed, respects reduced motion.
 */
export default function SeniorModeToggle({ compact = false }) {
  const { enabled, toggle } = useSeniorMode();
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={enabled}
      data-testid="senior-mode-toggle"
      title={enabled ? "Désactiver le mode senior" : "Activer le mode senior (grands caractères, contraste renforcé)"}
      className={`inline-flex items-center gap-2 rounded-full border-2 transition font-bold ${
        compact ? "px-2.5 py-1.5 text-xs" : "px-3 py-2 text-sm"
      } ${
        enabled
          ? "bg-navy border-navy text-cream"
          : "bg-white border-cream-dark text-navy hover:border-terracotta"
      }`}
    >
      <Type className={compact ? "w-3.5 h-3.5" : "w-4 h-4"} />
      <span className="hidden sm:inline">
        {enabled ? "Confort +" : "Confort +"}
      </span>
    </button>
  );
}
