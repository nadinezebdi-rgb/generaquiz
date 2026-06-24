// Requiert NEXT_PUBLIC_API_URL dans .env.local

import type { Metadata } from 'next';
import { QuizSession } from '../../components/QuizSession';

export const metadata: Metadata = {
  title: "Quiz d'Antan — Le quiz intergénérationnel",
  description: 'Jouez en famille ! Questions pour toutes les générations.',
};

const badges = ['8 ans et +', 'Nostalgie', 'Famille'] as const;

export default function QuizPage() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      {/* @section: hero-quiz */}
      <section className="mx-auto flex w-full max-w-5xl flex-col items-center px-4 pb-8 pt-10 text-center sm:px-6 sm:pb-10 sm:pt-14 lg:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.24em] text-slate-500">
          Quiz intergénérationnel
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
          Quiz d&apos;Antan
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
          Le quiz qui réunit toutes les générations
        </p>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {badges.map((badge) => (
            <span
              key={badge}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm sm:text-sm"
            >
              {badge}
            </span>
          ))}
        </div>
      </section>

      {/* @section: quiz-session */}
      <section className="mx-auto w-full max-w-5xl px-0 pb-8 sm:px-6 lg:px-8">
        <QuizSession />
      </section>

      {/* @section: footer-minimal */}
      <footer className="border-t border-slate-200 px-4 py-6 text-center text-sm text-slate-500 sm:px-6">
        Propulsé par Mistral AI · Questions générées à la volée
      </footer>
    </main>
  );
}
