import type { Metadata } from 'next';
import Link from 'next/link';
import LeaderboardPanel from '../../components/LeaderboardPanel';

export const metadata: Metadata = {
  title: "Classement — Quiz d'Antan",
  description: "Le classement en direct des familles sur Quiz d'Antan.",
};

export default function LeaderboardPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      {/* @section: leaderboard-hero */}
      {/* Hero sobre pour introduire le classement public global. */}
      <section className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8 lg:p-10">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl lg:text-5xl">
                  Classement des familles
                </h1>
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" aria-hidden="true" />
                  En direct
                </span>
              </div>
              <p className="mt-4 text-base leading-7 text-slate-600 sm:text-lg">
                Qui règne sur le quiz intergénérationnel ?
              </p>
            </div>
          </div>
        </div>

        {/* @section: global-leaderboard */}
        {/* Vue publique : aucun identifiant famille ou joueur n'est nécessaire. */}
        <LeaderboardPanel showGlobal={true} />

        {/* @section: leaderboard-navigation */}
        <div className="flex flex-col items-center justify-between gap-4 rounded-3xl border border-slate-200 bg-white px-5 py-4 text-center shadow-sm sm:flex-row sm:text-left">
          <p className="text-sm text-slate-500">Prêt à défier une autre génération ?</p>
          <Link
            href="/quiz"
            className="inline-flex items-center justify-center rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2"
          >
            Retour au quiz
          </Link>
        </div>
      </section>

      {/* @section: realtime-footer */}
      <footer className="border-t border-slate-200 bg-white px-4 py-5 text-center text-sm text-slate-500">
        Mis à jour en temps réel via Supabase Realtime
      </footer>
    </main>
  );
}
