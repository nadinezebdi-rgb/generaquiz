import { Check, Lock } from "lucide-react";
import { FAMILY_ACCESS } from "@/config/pricing";

const Value = ({ value, who }) => {
  const included = value.startsWith("Inclus");
  return (
    <span className={`inline-flex items-start gap-1.5 text-sm ${included ? "text-navy font-semibold" : "text-navy/60"}`}>
      {included ? <Check className="w-4 h-4 text-[#3D9970] shrink-0 mt-0.5" /> : <Lock className="w-4 h-4 shrink-0 mt-0.5" />}
      {who && <span className="font-normal text-navy/60">{who} :</span>} {value}
    </span>
  );
};

const NOTE = "Les quatre proches jouent gratuitement avec le bénéficiaire dans l'espace familial. Ils paient uniquement s'ils souhaitent leur propre accès complet à GénéraQuiz.";

export const FamilyAccessTable = () => (
  <div className="rounded-2xl border-2 border-cream-dark bg-white overflow-hidden" data-testid="family-access-table">
    <table className="w-full text-left hidden sm:table">
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
            <td className="px-3 py-3 text-sm text-navy align-top">{row.label}</td>
            <td className="px-3 py-3 align-top"><Value value={row.owner} /></td>
            <td className="px-3 py-3 align-top"><Value value={row.proches} /></td>
          </tr>
        ))}
      </tbody>
    </table>
    <ul className="sm:hidden divide-y divide-cream-dark">
      {FAMILY_ACCESS.map((row) => (
        <li key={row.label} className="p-4 grid gap-1.5">
          <span className="font-semibold text-navy">{row.label}</span>
          <Value value={row.owner} who="Bénéficiaire" />
          <Value value={row.proches} who="Les 4 proches" />
        </li>
      ))}
    </ul>
    <p className="px-3 py-3 text-xs text-navy/70 bg-cream/50">{NOTE}</p>
  </div>
);
