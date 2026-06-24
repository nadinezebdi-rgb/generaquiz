'use client';

import { useEffect, useMemo } from 'react';
import type { Category, Theme } from '../types/quiz';
import { useQuiz } from '../hooks/useQuiz';

const categoryIcons: Record<Category, string> = {
  nostalgie: '📻',
  moderne: '📱',
  intemporel: '🤝',
  culture: '🎭',
};

const categoryTitles: Record<Category, string> = {
  nostalgie: 'Nostalgie',
  moderne: 'Moderne',
  intemporel: 'Intemporel',
  culture: 'Culture générale',
};

const categoryOrder: Category[] = ['nostalgie', 'moderne', 'intemporel', 'culture'];

export interface ThemeSelectorProps {
  onSelectTheme: (theme: Theme) => void;
  onSelectRandom: () => void;
}

export function ThemeSelector({ onSelectTheme, onSelectRandom }: ThemeSelectorProps) {
  const { themes, loading, error, fetchThemes } = useQuiz();

  useEffect(() => {
    void fetchThemes();
  }, [fetchThemes]);

  const groupedThemes = useMemo(() => {
    return themes.reduce<Record<Category, Theme[]>>(
      (groups, theme) => {
        groups[theme.category].push(theme);
        return groups;
      },
      {
        nostalgie: [],
        moderne: [],
        intemporel: [],
        culture: [],
      },
    );
  }, [themes]);

  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      <div className="mb-8 text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-sky-700">
          Quiz d’Antan
        </p>
        <h1 className="mt-2 text-3xl font-bold text-stone-900 sm:text-4xl">
          Choisissez un thème à partager en famille
        </h1>
        <p className="mt-3 text-stone-600">
          Des questions variées pour faire dialoguer souvenirs, culture et actualité.
        </p>
      </div>

      <button
        type="button"
        onClick={onSelectRandom}
        className="mb-8 w-full rounded-3xl border border-sky-100 bg-gradient-to-br from-sky-50 to-amber-50 p-5 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md sm:p-6"
      >
        <span className="text-3xl" aria-hidden="true">
          ✨
        </span>
        <div className="mt-3">
          <h2 className="text-xl font-bold text-stone-900">Surprise intergénérationnelle</h2>
          <p className="mt-2 text-sm leading-6 text-stone-600">
            Un mélange de nostalgie, de modernité, de culture et de questions intemporelles
            pour que chaque génération ait son moment.
          </p>
        </div>
      </button>

      {loading ? (
        <div className="rounded-2xl border border-stone-200 bg-white p-5 text-center text-stone-600">
          Chargement des thèmes…
        </div>
      ) : null}

      {error ? (
        <div className="rounded-2xl border border-rose-100 bg-rose-50 p-5 text-center text-rose-700">
          {error}
        </div>
      ) : null}

      {!loading && !error ? (
        <div className="space-y-8">
          {categoryOrder.map((category) => {
            const categoryThemes = groupedThemes[category];

            if (!categoryThemes.length) {
              return null;
            }

            return (
              <div key={category}>
                <h2 className="mb-3 flex items-center gap-2 text-lg font-bold text-stone-900">
                  <span aria-hidden="true">{categoryIcons[category]}</span>
                  {categoryTitles[category]}
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryThemes.map((theme) => (
                    <button
                      key={theme.id}
                      type="button"
                      onClick={() => onSelectTheme(theme)}
                      className="rounded-2xl border border-stone-200 bg-white p-4 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-sky-200 hover:bg-sky-50 hover:shadow-md"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-semibold text-stone-900">{theme.name}</h3>
                        <span className="text-xl" aria-hidden="true">
                          {categoryIcons[theme.category]}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                        <span className="rounded-full bg-stone-100 px-2.5 py-1 text-stone-700">
                          {categoryTitles[theme.category]}
                        </span>
                        <span className="rounded-full bg-violet-50 px-2.5 py-1 text-violet-700">
                          {theme.era}
                        </span>
                      </div>
                      {theme.description ? (
                        <p className="mt-3 text-sm leading-6 text-stone-600">{theme.description}</p>
                      ) : null}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
