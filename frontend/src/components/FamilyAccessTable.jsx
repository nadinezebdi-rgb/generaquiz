import { Check, Lock } from "lucide-react";
import { FAMILY_ACCESS } from "@/config/pricing";

const Cell = ({ value }) => {
  const included = value.startsWith("Inclus");
  return (
    <td className="px-3 py-3 align-top">
      <span className={`inline-flex items-start gap-1.5 text-sm ${included ? "text-navy font-semibold" : "text-navy/60"}`}>
        {included ? <Check className="w-4 h-4 text-[#3D9970] shrink-0 mt-0.5" /> : <Lock className="w-4 h-4 shrink-0 mt-0.5" />}
        {value}
      </span>
    </td>
  );
};

export const FamilyAccessTable = ({ dark = false }) => (
  <div className={`rounded-2xl overflow-x-auto border-2 ${dark ? "border-mustard/40 bg-white" : "border-cream-dark bg-white"}`} data-testid="family-access-table">
    <table className="w-full text-left">
      <thead className="bg-cream">
        <tr className="text-xs uppercase tracking-wider text-navy/70">
          <th className="px-3 py-3 font-bold">Accès</th>
          <th className="px-3 py-3 font-bold">Bénéficiaire</th>
          <th className="px-3 py-3 font-bold">Les 4 proches</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-cream-dark">
        {FAMILY_ACCESS.map((row) => (
          <tr key={row.label}>
            <td className="px-2 sm:px-3 py-3 text-sm text-navy align-top">{row.label}</td>
            <Cell value={row.owner} />
            <Cell value={row.proches} />
          </tr>
        ))}
      </tbody>
    </table>
    <p className="px-3 py-3 text-xs text-navy/70 bg-cream/50">
      Les quatre proches jouent gratuitement avec le bénéficiaire dans l&apos;espace familial. Ils paient uniquement s&apos;ils souhaitent leur propre accès complet à GénéraQuiz.
    </p>
  </div>
);
