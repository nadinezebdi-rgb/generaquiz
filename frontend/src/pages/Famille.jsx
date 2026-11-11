import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Users, UserPlus, Trash2, Trophy, Swords, Copy, LogOut, Gift } from "lucide-react";
import Navbar from "@/components/Navbar";
import { FamilyAccessTable } from "@/components/FamilyAccessTable";
import { api, formatError } from "@/lib/api";

const err = (e) => toast.error(formatError(e.response?.data?.detail));
const input = "w-full rounded-xl border-2 border-cream-dark bg-white px-4 py-3 text-navy focus:border-navy outline-none";

function InviteForm({ onDone }) {
  const [f, setF] = useState({ name: "", email: "" });
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/famille/proches", f); toast.success(`Invitation envoyée à ${f.name}`); setF({ name: "", email: "" }); onDone(); }
    catch (e2) { err(e2); }
  };
  return (
    <form onSubmit={submit} className="grid sm:grid-cols-[1fr_1.4fr_auto] gap-3" data-testid="famille-invite-form">
      <input required maxLength={40} placeholder="Prénom" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={input} data-testid="famille-invite-name" />
      <input required type="email" placeholder="E-mail du proche" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={input} data-testid="famille-invite-email" />
      <button type="submit" data-testid="famille-invite-submit" className="inline-flex items-center justify-center gap-2 bg-terracotta text-white font-bold px-5 py-3 rounded-full hover:bg-terracotta-dark transition-colors"><UserPlus className="w-4 h-4" /> Inviter</button>
    </form>
  );
}

function ProchesList({ space, reload }) {
  const owner = space.role === "owner";
  const remove = async (p) => {
    if (!window.confirm(`Retirer ${p.name} de l'espace famille ?`)) return;
    try { await api.delete(`/famille/proches/${p.id}`); reload(); } catch (e) { err(e); }
  };
  const copy = (link) => navigator.clipboard?.writeText(link).then(() => toast.success("Lien copié — envoyez-le par SMS ou WhatsApp"));
  return (
    <section className="bg-white rounded-3xl border-2 border-cream-dark p-6" data-testid="famille-proches">
      <h2 className="font-display text-2xl font-extrabold text-navy mb-1 flex items-center gap-2"><Users className="w-6 h-6 text-terracotta" /> Les proches ({space.proches.length}/{space.max_proches})</h2>
      <p className="text-navy/70 mb-4 text-sm">Ils jouent gratuitement aux quiz et défis du groupe familial.</p>
      <ul className="divide-y divide-cream-dark mb-5">
        {space.proches.length === 0 && <li className="py-3 text-navy/60" data-testid="famille-proches-empty">Aucun proche pour le moment.</li>}
        {space.proches.map((p, i) => (
          <li key={p.id || i} className="py-3 flex flex-wrap items-center gap-3" data-testid={`famille-proche-${i}`}>
            <span className="font-semibold text-navy flex-1 min-w-[120px]">{p.name}</span>
            <span className={`text-xs font-bold px-3 py-1 rounded-full ${p.status === "accepted" ? "bg-[#3D9970]/15 text-[#2E7A57]" : "bg-mustard/40 text-navy"}`}>{p.status === "accepted" ? "A rejoint" : "Invité"}</span>
            {owner && p.status === "invited" && <button type="button" onClick={() => copy(p.link)} data-testid={`famille-proche-copy-${i}`} className="text-sm font-semibold text-navy inline-flex items-center gap-1 hover:text-terracotta"><Copy className="w-4 h-4" /> Lien</button>}
            {owner && <button type="button" onClick={() => remove(p)} aria-label={`Retirer ${p.name}`} data-testid={`famille-proche-remove-${i}`} className="p-2 text-bordeaux hover:bg-bordeaux/10 rounded-full"><Trash2 className="w-4 h-4" /></button>}
          </li>
        ))}
      </ul>
      {owner && space.proches.length < space.max_proches && <InviteForm onDone={reload} />}
    </section>
  );
}

function Leaderboard({ rows, me }) {
  return (
    <section className="bg-white rounded-3xl border-2 border-cream-dark p-6" data-testid="famille-leaderboard">
      <h2 className="font-display text-2xl font-extrabold text-navy mb-4 flex items-center gap-2"><Trophy className="w-6 h-6 text-mustard-dark" /> Classement familial <span className="text-sm font-sans font-normal text-navy/60">(30 derniers jours)</span></h2>
      <ol className="grid gap-2">
        {rows.map((r, i) => (
          <li key={r.user_id} className={`flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl px-4 py-3 ${r.user_id === me ? "bg-mustard/30" : "bg-cream/60"}`} data-testid={`famille-rank-${i}`}>
            <span className="font-display text-2xl font-extrabold text-navy w-8">{i + 1}</span>
            <span className="font-semibold text-navy flex-1 min-w-0 truncate">{r.name}</span>
            <span className="font-bold text-bordeaux sm:order-last">{r.score} pts</span>
            <span className="text-sm text-navy/70 w-full sm:w-auto pl-11 sm:pl-0">{r.games} parties · {r.accuracy} %</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Challenges({ items }) {
  return (
    <section className="bg-white rounded-3xl border-2 border-cream-dark p-6" data-testid="famille-challenges">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="font-display text-2xl font-extrabold text-navy flex items-center gap-2"><Swords className="w-6 h-6 text-terracotta" /> Défis de la famille</h2>
        <Link to="/app/challenges/new" data-testid="famille-new-challenge" className="bg-navy text-cream font-bold px-5 py-2.5 rounded-full hover:bg-terracotta transition-colors">Lancer un défi</Link>
      </div>
      {items.length === 0 ? <p className="text-navy/60">Aucun défi encore. Lancez le premier !</p> : (
        <ul className="grid gap-2">
          {items.map((c) => (
            <li key={c.token}><Link to={`/defi/${c.token}`} className="flex items-center justify-between gap-3 rounded-2xl bg-cream/60 px-4 py-3 hover:bg-cream transition-colors" data-testid={`famille-challenge-${c.token}`}>
              <span className="text-navy"><strong>{c.category_title}</strong> · par {c.creator_name}</span>
              <span className="text-sm text-navy/70">{c.participants} joueur{c.participants > 1 ? "s" : ""}</span>
            </Link></li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NoFamily() {
  return (
    <div className="grid gap-6" data-testid="famille-none">
      <div className="bg-white rounded-3xl border-2 border-cream-dark p-8">
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-navy mb-3">L&apos;espace famille</h1>
        <p className="text-navy/75 mb-6">Avec l&apos;offre Famille, le bénéficiaire invite 4 proches pour jouer ensemble toute l&apos;année.</p>
        <div className="flex flex-wrap gap-3">
          <Link to="/app/pricing" data-testid="famille-none-pricing" className="bg-terracotta text-white font-bold px-6 py-3 rounded-full hover:bg-terracotta-dark transition-colors">Voir l&apos;offre Famille</Link>
          <Link to="/activer" data-testid="famille-none-activate" className="bg-white border-2 border-navy text-navy font-bold px-6 py-3 rounded-full inline-flex items-center gap-2 hover:bg-navy hover:text-cream transition-colors"><Gift className="w-4 h-4" /> J&apos;ai un code cadeau</Link>
        </div>
      </div>
      <FamilyAccessTable />
    </div>
  );
}

export default function Famille() {
  const [space, setSpace] = useState(null);
  const load = useCallback(() => api.get("/famille").then((r) => setSpace(r.data)).catch(err), []);
  useEffect(() => { load(); }, [load]);
  const leave = async () => {
    if (!window.confirm("Quitter cet espace famille ?")) return;
    try { await api.post("/famille/quitter"); load(); } catch (e) { err(e); }
  };
  return (
    <div className="min-h-screen paper-bg">
      <Navbar variant="app" />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10 grid gap-6 [&>*]:min-w-0" data-testid="famille-page">
        {!space ? <p className="text-navy">Chargement…</p> : space.role === "none" ? <NoFamily /> : (
          <>
            <header>
              <p className="text-terracotta font-bold uppercase tracking-[0.2em] text-xs mb-2">Espace famille</p>
              <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-navy" data-testid="famille-title">
                {space.role === "owner" ? "Votre famille GénéraQuiz" : `La famille de ${space.owner_name}`}
              </h1>
            </header>
            <Leaderboard rows={space.leaderboard} me={space.me} />
            <Challenges items={space.challenges} />
            <ProchesList space={space} reload={load} />
            {space.role === "proche" && (
              <button type="button" onClick={leave} data-testid="famille-leave" className="justify-self-start text-sm text-navy/60 inline-flex items-center gap-1 hover:text-bordeaux"><LogOut className="w-4 h-4" /> Quitter cet espace famille</button>
            )}
          </>
        )}
      </main>
    </div>
  );
}
