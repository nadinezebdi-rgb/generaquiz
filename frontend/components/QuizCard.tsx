'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Category, Difficulty, Era, Question } from '../types/quiz';

const difficultyStyles: Record<Difficulty, string> = {
  facile: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  moyen: 'bg-orange-50 text-orange-700 ring-orange-100',
  difficile: 'bg-rose-50 text-rose-700 ring-rose-100',
};

const categoryLabels: Record<Category, string> = {
  nostalgie: 'Nostalgie',
  moderne: 'Moderne',
  intemporel: 'Intemporel',
  culture: 'Culture',
};

const eraLabels: Record<Era, string> = {
  '1950-1980': '1950-1980',
  '1980-2000': '1980-2000',
  '2000-2020': '2000-2020',
  intemporel: 'Intemporel',
};

function normalizeAnswer(value: string): string {
  return value.trim().toLocaleLowerCase('fr-FR');
}

function getAnswerChoice(question: Question): string {
  const normalizedAnswer = normalizeAnswer(question.answer);
  const letterIndex = normalizedAnswer.length === 1
    ? normalizedAnswer.charCodeAt(0) - 'a'.charCodeAt(0)
    : -1;

  if (letterIndex >= 0 && letterIndex < question.choices.length) {
    return question.choices[letterIndex];
  }

  return question.answer;
}

export interface QuizCardProps {
  question: Question;
  onAnswer: (choice: string) => void;
  showResult: boolean;
  selectedChoice?: string;
  enableTimer?: boolean;
  timerSeconds?: number;
  onTimeUp?: () => void;
}

export function QuizCard({
  question,
  onAnswer,
  showResult,
  selectedChoice,
  enableTimer = false,
  timerSeconds = 30,
  onTimeUp,
}: QuizCardProps) {
  const [remainingTime, setRemainingTime] = useState(timerSeconds);
  const answerChoice = getAnswerChoice(question);

  useEffect(() => {
    setRemainingTime(timerSeconds);
  }, [question.question, timerSeconds]);

  useEffect(() => {
    if (!enableTimer || showResult) {
      return undefined;
    }

    if (remainingTime <= 0) {
      onTimeUp?.();
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setRemainingTime((previousTime) => previousTime - 1);
    }, 1000);

    return () => window.clearTimeout(timeoutId);
  }, [enableTimer, onTimeUp, remainingTime, showResult]);

  const timerProgress = useMemo(() => {
    if (!enableTimer) {
      return 100;
    }

    return Math.max(0, (remainingTime / timerSeconds) * 100);
  }, [enableTimer, remainingTime, timerSeconds]);

  function getChoiceStyle(choice: string): string {
    const baseStyle =
      'w-full rounded-2xl border px-4 py-3 text-left text-sm font-medium transition duration-200 sm:text-base';

    if (!showResult) {
      return selectedChoice === choice
        ? `${baseStyle} border-sky-200 bg-sky-50 text-sky-900 shadow-sm`
        : `${baseStyle} border-stone-200 bg-white text-stone-800 hover:border-sky-200 hover:bg-sky-50`;
    }

    if (choice === answerChoice) {
      return `${baseStyle} border-emerald-200 bg-emerald-50 text-emerald-800`;
    }

    if (choice === selectedChoice && choice !== answerChoice) {
      return `${baseStyle} border-rose-200 bg-rose-50 text-rose-800`;
    }

    return `${baseStyle} border-stone-200 bg-stone-50 text-stone-500`;
  }

  return (
    <article className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
      <div className="mb-5 flex flex-wrap gap-2">
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${difficultyStyles[question.difficulty]}`}
        >
          {question.difficulty}
        </span>
        <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 ring-1 ring-sky-100">
          {categoryLabels[question.category]}
        </span>
        <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700 ring-1 ring-violet-100">
          {eraLabels[question.era]}
        </span>
      </div>

      {enableTimer ? (
        <div className="mb-5" aria-label={`Temps restant : ${remainingTime} secondes`}>
          <div className="mb-2 flex items-center justify-between text-xs text-stone-500">
            <span>Temps restant</span>
            <span>{remainingTime}s</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-sky-200 transition-all duration-500"
              style={{ width: `${timerProgress}%` }}
            />
          </div>
        </div>
      ) : null}

      <h2 className="mb-6 text-xl font-semibold leading-relaxed text-stone-900 sm:text-2xl">
        {question.question}
      </h2>

      <div className="grid gap-3">
        {question.choices.map((choice, index) => {
          const letter = String.fromCharCode(65 + index);

          return (
            <button
              key={`${choice}-${index}`}
              type="button"
              className={getChoiceStyle(choice)}
              onClick={() => onAnswer(choice)}
              disabled={showResult}
              aria-pressed={selectedChoice === choice}
            >
              <span className="mr-3 inline-flex h-7 w-7 items-center justify-center rounded-full bg-stone-100 text-xs font-bold text-stone-600">
                {letter}
              </span>
              {choice}
            </button>
          );
        })}
      </div>

      {showResult ? (
        <p className="mt-5 rounded-2xl bg-stone-50 px-4 py-3 text-sm text-stone-700">
          {selectedChoice === answerChoice
            ? 'Bonne réponse ! Voilà un joli pont entre les générations.'
            : `Presque ! La bonne réponse était : ${answerChoice}`}
        </p>
      ) : null}
    </article>
  );
}
