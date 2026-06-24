/**
 * Types partagés pour le module Quiz d'Antan.
 * Ces types sont alignés sur le format JSON renvoyé par le backend.
 */

export type Difficulty = 'facile' | 'moyen' | 'difficile';

export type Category = 'nostalgie' | 'moderne' | 'intemporel' | 'culture';

export type Era = '1950-1980' | '1980-2000' | '2000-2020' | 'intemporel';

export interface Question {
  question: string;
  choices: [string, string, string, string] | string[];
  answer: string;
  difficulty: Difficulty;
  category: Category;
  era: Era;
}

export interface Theme {
  id: string;
  name: string;
  category: Category;
  era: Era;
  description?: string;
}

export interface QuizAnswer {
  questionIndex: number;
  choice: string;
  correctAnswer: string;
  isCorrect: boolean;
}

export interface QuizSession {
  questions: Question[];
  currentIndex: number;
  score: number;
  answers: QuizAnswer[];
  sessionDone: boolean;
  theme?: Theme | string;
  startedAt?: string;
  completedAt?: string;
}

export interface QuizGenerateResponse {
  questions: Question[];
}

export type QuizRandomResponse = Question[] | QuizGenerateResponse;

export type ThemesResponse = Theme[] | { themes: Theme[] };
