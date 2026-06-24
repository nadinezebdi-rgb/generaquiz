'use client';

import { useEffect } from 'react';
import { QuizCard } from './QuizCard';
import { ThemeSelector } from './ThemeSelector';
import { useQuiz } from '../hooks/useQuiz';
import type { Theme } from '../types/quiz';

function getScoreMessage(score: number, total: number): string {
  if (total === 0) {
    return 'Prêt pour une nouvelle partie ?';
  }

  const ratio = score / total;

  if (ratio >= 0.8) {
    return 'Excellent ! La famille est fière de vous.';
  }

  if (ratio >= 0.5) {
    return 'Bravo ! Les générations ont bien travaillé ensemble.';
  }

  return 'Joli essai ! Le prochain quiz sera l’occasion de partager encore plus de souvenirs.';
}

export interface QuizSessionProps {
  nbQuestions?: number;
  enableTimer?: boolean;
}

export function QuizSession({ nbQuestions = 5, enableTimer = false }: QuizSessionProps) {
  const {
    questions,
    loading,
    error,
    currentIndex,
    score,
    sessionDone,
    selectedChoice,
    showResult,
    currentQuestion,
    startQuiz,
    startRandom,
    answerQuestion,
    nextQuestion,
    resetQuiz,
  } = useQuiz({ nbQuestions });

  useEffect(() => {
    if (showResult && !sessionDone) {
      const timeoutId = window.setTimeout(() => {
        nextQuestion();
      }, 1200);

      return () => window.clearTimeout(timeoutId);
    }

    return undefined;
  }, [nextQuestion, sessionDone, showResult]);

  async function handleThemeSelection(theme: Theme) {
    await startQuiz(theme.id);
  }

  const hasActiveQuiz = questions.length > 0 && currentQuestion && !sessionDone;
  const progressValue = questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0;

  if (!hasActiveQuiz && !sessionDone) {
    return (
      <main className="min-h-screen bg-stone-50">
        <ThemeSelector onSelectTheme={handleThemeSelection} onSelectRandom={startRandom} />

        {loading ? (
          <div className="mx-auto max-w-3xl px-4 pb-8">
            <div className="rounded-2xl border border-stone-200 bg-white p-5 text-center text-stone-600 shadow-sm">
              Préparation du quiz…
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="mx-auto max-w-3xl px-4 pb-8">
            <div className="rounded-2xl border border-rose-100 bg-rose-50 p-5 text-center text-rose-700 shadow-sm">
              {error}
            </div>
          </div>
        ) : null}
      </main>
    );
  }

  if (sessionDone) {
    const total = questions.length;

    return (
      <main className="flex min-h-screen items-center justify-center bg-stone-50 px-4 py-8">
        <section className="w-full max-w-xl rounded-3xl border border-stone-200 bg-white p-6 text-center shadow-sm sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-sky-700">
            Résultat final
          </p>
          <h1 className="mt-3 text-4xl font-bold text-stone-900">
            {score} / {total}
          </h1>
          <p className="mt-4 text-lg font-medium text-stone-800">
            {getScoreMessage(score, total)}
          </p>
          <p className="mt-3 text-sm leading-6 text-stone-600">
            Continuez à jouer ensemble : les meilleures réponses naissent souvent des
            discussions entre petits et grands.
          </p>
          <button
            type="button"
            onClick={resetQuiz}
            className="mt-8 rounded-full bg-sky-600 px-6 py-3 text-sm font-semibold text-white transition duration-200 hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-300"
          >
            Recommencer
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-stone-50 px-4 py-6 sm:px-6">
      <section className="mx-auto max-w-3xl">
        <div className="mb-5 rounded-3xl border border-stone-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between text-sm font-medium text-stone-600">
            <span>
              Question {currentIndex + 1} / {questions.length}
            </span>
            <span>Score : {score}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-sky-300 transition-all duration-300"
              style={{ width: `${progressValue}%` }}
            />
          </div>
        </div>

        {error ? (
          <div className="mb-5 rounded-2xl border border-rose-100 bg-rose-50 p-4 text-center text-rose-700">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="rounded-3xl border border-stone-200 bg-white p-6 text-center text-stone-600 shadow-sm">
            Chargement de la question…
          </div>
        ) : null}

        {currentQuestion ? (
          <QuizCard
            question={currentQuestion}
            onAnswer={answerQuestion}
            showResult={showResult}
            selectedChoice={selectedChoice}
            enableTimer={enableTimer}
            onTimeUp={() => answerQuestion('')}
          />
        ) : null}

        {showResult ? (
          <div className="mt-5 flex justify-center">
            <button
              type="button"
              onClick={nextQuestion}
              className="rounded-full border border-sky-200 bg-white px-5 py-2.5 text-sm font-semibold text-sky-700 transition duration-200 hover:bg-sky-50"
            >
              {currentIndex >= questions.length - 1 ? 'Voir le résultat' : 'Question suivante'}
            </button>
          </div>
        ) : null}
      </section>
    </main>
  );
}
