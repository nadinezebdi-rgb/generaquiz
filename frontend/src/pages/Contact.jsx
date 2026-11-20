import { useState } from "react";
import { toast } from "sonner";
import { Send, CheckCircle2 } from "lucide-react";
import LegalLayout from "@/components/LegalLayout";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, formatError } from "@/lib/api";

const SUBJECTS = [
  ["question", "Une question"], ["abonnement", "Mon abonnement"], ["cadeau", "Un cadeau"],
  ["ehpad", "Établissement / EHPAD"], ["idee", "Une idée ou un souci"], ["autre", "Autre"],
];
const EMPTY = { name: "", email: "", subject: "question", message: "", website: "" };

function Sent({ onAgain }) {
  return (
    <div className="bg-white rounded-3xl border-2 border-cream-dark p-8 text-center" data-testid="contact-success">
      <CheckCircle2 className="w-12 h-12 text-terracotta mx-auto mb-3" />
      <p className="font-display text-2xl font-bold text-navy mb-2">Merci, votre message est parti !</p>
      <p className="text-navy/70">Un e-mail de confirmation vient de vous être envoyé. Nous vous répondons très vite.</p>
      <button onClick={onAgain} className="mt-6 text-terracotta font-bold underline" data-testid="contact-again-btn">Écrire un autre message</button>
    </div>
  );
}

export default function Contact() {
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { await api.post("/contact", f); setSent(true); setF(EMPTY); window.scrollTo({ top: 0, behavior: "smooth" }); }
    catch (err) { toast.error(formatError(err.response?.data?.detail) || "Envoi impossible"); }
    finally { setBusy(false); }
  };

  return (
    <LegalLayout title="Nous écrire" testId="contact-page">
      <p className="text-navy/70 mt-2">Une question, une idée, un souci ? Écrivez-nous, une vraie personne vous répond.</p>
      {sent ? <Sent onAgain={() => setSent(false)} /> : (
        <form onSubmit={submit} className="bg-white rounded-3xl border-2 border-cream-dark p-6 sm:p-8 space-y-5" data-testid="contact-form">
          <div className="grid sm:grid-cols-2 gap-4">
            <label className="block font-semibold">Votre nom
              <Input required minLength={2} value={f.name} onChange={set("name")} className="mt-1 h-12 text-lg" data-testid="contact-name-input" />
            </label>
            <label className="block font-semibold">Votre e-mail
              <Input required type="email" value={f.email} onChange={set("email")} className="mt-1 h-12 text-lg" data-testid="contact-email-input" />
            </label>
          </div>
          <label className="block font-semibold">Sujet
            <select value={f.subject} onChange={set("subject")} className="mt-1 w-full h-12 rounded-md border border-input bg-white px-3 text-lg" data-testid="contact-subject-select">
              {SUBJECTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="block font-semibold">Votre message
            <Textarea required minLength={10} rows={6} value={f.message} onChange={set("message")} className="mt-1 text-lg" data-testid="contact-message-input" />
          </label>
          <input type="text" tabIndex={-1} autoComplete="off" value={f.website} onChange={set("website")} className="hidden" aria-hidden="true" />
          <button disabled={busy} className="inline-flex items-center gap-2 bg-terracotta text-white font-bold text-lg px-7 py-3 rounded-full hover:bg-terracotta/90 transition-colors disabled:opacity-60" data-testid="contact-submit-btn">
            <Send className="w-5 h-5" /> {busy ? "Envoi…" : "Envoyer mon message"}
          </button>
        </form>
      )}
    </LegalLayout>
  );
}
