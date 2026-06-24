'use client';

import { useCallback, useMemo, useState } from 'react';
import type {
  Question,
  QuizGenerateResponse,
  QuizRandomResponse,
  Theme,
  ThemesResponse,
} from '../types/quiz';

const DEFAULT_QUESTION_COUNT = 5;
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

function buildApiUrl(path: string): string {
  const normalizedBase = API_URL.replace(/\/$/, '');
  return `${normalizedBase}${path}`;
}

function extractQuestions(payload: QuizRandomResponse): Question[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  return payload.questions;
}

function extractThemes(payload: ThemesResponse): Theme[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  return payload.themes;
}

function normalizeAnswer(value: string): string {
  return value.trim().toLocaleLowerCase('fr-FR');
}

function isCorrectChoice(choice: string, question: Question): boolean {
  const normalizedChoice = normalizeAnswer(choice);
  const normalizedAnswer = normalizeAnswer(question.answer);
  const answerIndex = question.choices.findIndex(
    (availableChoice) => normalizeAnswer(availableChoice) === normalizedChoice,
  );
  const answerLetter = answerIndex >= 0 ? normalizeAnswer(String.fromCharCode(65 + answerIndex)) : '';

  return normalizedChoice === normalizedAnswer || answerLetter === normalizedAnswer;
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Erreur API (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export interface UseQuizOptions {
  nbQuestions?: number;
}

export interface UseQuizReturn {
  questions: Question[];
  themes: Theme[];
  loading: boolean;
  error: string | null;
  currentIndex: number;
  score: number;
  sessionDone: boolean;
  selectedChoice?: string;
  showResult: boolean;
  currentQuestion?: Question;
  fetchThemes: () => Promise<Theme[]>;
  startQuiz: (theme?: string) => Promise<void>;
  startRandom: () => Promise<void>;
  answerQuestion: (choice: string) => void;
  nextQuestion: () => void;
  resetQuiz: () => void;
}

export function useQuiz(options: UseQuizOptions = {}): UseQuizReturn {
  const nbQuestions = options.nbQuestions ?? DEFAULT_QUESTION_COUNT;

  const [questions, setQuestions] = useState<Question[]>([]);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [sessionDone, setSessionDone] = useState(false);
  const [selectedChoice, setSelectedChoice] = useState<string | undefined>();
  const [showResult, setShowResult] = useState(false);

  const currentQuestion = useMemo(
    () => questions[currentIndex],
    [questions, currentIndex],
  );

  const resetProgress = useCallback(() => {
    setCurrentIndex(0);
    setScore(0);
    setSessionDone(false);
    setSelectedChoice(undefined);
    setShowResult(false);
  }, []);

  const loadQuestions = useCallback(async (url: string) => {
    setLoading(true);
    setError(null);
    resetProgress();

    try {
      const payload = await fetchJson<QuizRandomResponse>(url);
      const nextQuestions = extractQuestions(payload);

      if (!nextQuestions.length) {
        throw new Error('Aucune question reçue depuis le serveur.');
      }

      setQuestions(nextQuestions);
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : 'Impossible de charger le quiz pour le moment.';
      setQuestions([]);
      setError(`Le quiz n’a pas pu être chargé. ${message}`);
    } finally {
      setLoading(false);
    }
  }, [resetProgress]);

  const fetchThemes = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const payload = await fetchJson<ThemesResponse>(buildApiUrl('/api/quiz/themes'));
      const nextThemes = extractThemes(payload);
      setThemes(nextThemes);
      return nextThemes;
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : 'Impossible de récupérer les thèmes.';
      setError(`Les thèmes ne sont pas disponibles. ${message}`);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const startQuiz = useCallback(
    async (theme?: string) => {
      const params = new URLSearchParams({ nb: String(nbQuestions) });

      if (theme) {
        params.set('theme', theme);
      }

      await loadQuestions(buildApiUrl(`/api/quiz/generate?${params.toString()}`));
    },
    [loadQuestions, nbQuestions],
  );

  const startRandom = useCallback(async () => {
    await loadQuestions(buildApiUrl('/api/quiz/random'));
  }, [loadQuestions]);

  const answerQuestion = useCallback(
    (choice: string) => {
      if (!currentQuestion || showResult || sessionDone) {
        return;
      }

      setSelectedChoice(choice);
      setShowResult(true);

      if (isCorrectChoice(choice, currentQuestion)) {
        setScore((previousScore) => previousScore + 1);
      }
    },
    [currentQuestion, sessionDone, showResult],
  );

  const nextQuestion = useCallback(() => {
    if (!questions.length) {
      return;
    }

    const isLastQuestion = currentIndex >= questions.length - 1;

    if (isLastQuestion) {
      setSessionDone(true);
      return;
    }

    setCurrentIndex((previousIndex) => previousIndex + 1);
    setSelectedChoice(undefined);
    setShowResult(false);
  }, [currentIndex, questions.length]);

  const resetQuiz = useCallback(() => {
    setQuestions([]);
    setError(null);
    resetProgress();
  }, [resetProgress]);

  return {
    questions,
    themes,
    loading,
    error,
    currentIndex,
    score,
    sessionDone,
    selectedChoice,
    showResult,
    currentQuestion,
    fetchThemes,
    startQuiz,
    startRandom,
    answerQuestion,
    nextQuestion,
    resetQuiz,
  };
}
