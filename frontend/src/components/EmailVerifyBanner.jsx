import { useState } from "react";
import { MailCheck } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";

export function EmailVerifyBanner({ user }) {
  const [busy, setBusy] = useState(false);
  if (!user || user.email_verified || /@(google|apple)\.local$/.test(user.email || "")) return null;
  const resend = async () => {
    setBusy(true);
    try { await api.post("/auth/resend-verification"); toast.success(`Lien envoyé à ${user.email}`); }
    catch (e) { toast.error(formatError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <div className="bg-mustard/25 border-2 border-mustard rounded-2xl p-4 mb-6 flex flex-wrap items-center gap-3" data-testid="email-verify-banner">
      <MailCheck className="w-6 h-6 text-navy shrink-0" aria-hidden="true" />
      <p className="flex-1 min-w-[220px] text-navy">
        Confirmez votre adresse <strong>{user.email}</strong> en cliquant sur le lien reçu par e-mail : cela protège votre compte.
      </p>
      <button type="button" onClick={resend} disabled={busy} data-testid="email-verify-resend"
        className="bg-navy text-cream font-bold px-5 py-2.5 rounded-full hover:bg-navy-dark transition-colors disabled:opacity-60">
        {busy ? "Envoi…" : "Renvoyer le lien"}
      </button>
    </div>
  );
}
