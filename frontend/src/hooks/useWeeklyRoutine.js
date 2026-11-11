/**
 * useWeeklyRoutine — état de la routine hebdomadaire « Bien vieillir ».
 *
 * Persistance : localStorage d'abord (clé `gq_bien_vieillir_routine`), comme
 * SeniorModeContext. Aucun compte n'est requis pour utiliser la routine — c'est
 * délibéré : la rubrique est publique et doit rester utilisable sans inscription.
 *
 * Le format est versionné et volontairement plat pour être poussé tel quel vers
 * `PUT /api/bien-vieillir/routine` le jour où la synchronisation multi-appareils
 * sera activée (l'endpoint existe déjà côté backend et accepte cette forme).
 *
 *   {
 *     version: 1,
 *     weeks: { "2026-W37": { marche: true, memoire: true } },
 *     updatedAt: "2026-09-09T10:00:00.000Z"
 *   }
 *
 * Les semaines sans aucune coche ne sont pas stockées.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { HABIT_IDS, ROUTINE_VERSION, WEEK_VALID_THRESHOLD } from "@/content/routineHebdo";

const STORAGE_KEY = "gq_bien_vieillir_routine";

/* -------------------------------------------------------------------------- */
/* Clés de semaine ISO 8601 (la semaine commence le lundi)                     */
/* -------------------------------------------------------------------------- */

/** Renvoie la clé ISO "YYYY-Www" d'une date. */
export function isoWeekKey(date = new Date()) {
  // Copie en UTC pour éviter les décalages de fuseau autour de minuit.
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  // Jeudi de la semaine courante : détermine l'année ISO.
  const dayNum = d.getUTCDay() || 7; // dimanche = 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const isoYear = d.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const weekNo = Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  return `${isoYear}-W${String(weekNo).padStart(2, "0")}`;
}

/** Clé de la semaine située `offset` semaines avant `from` (offset ≥ 0). */
export function weekKeyBefore(offset, from = new Date()) {
  const d = new Date(from);
  d.setDate(d.getDate() - 7 * offset);
  return isoWeekKey(d);
}

/** Libellé lisible : "semaine du 7 au 13 septembre". */
export function weekLabel(date = new Date()) {
  const d = new Date(date);
  const dayNum = d.getDay() || 7;
  const monday = new Date(d);
  monday.setDate(d.getDate() - dayNum + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmtDay = new Intl.DateTimeFormat("fr-FR", { day: "numeric" });
  const fmtFull = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long" });
  const sameMonth = monday.getMonth() === sunday.getMonth();
  return sameMonth
    ? `semaine du ${fmtDay.format(monday)} au ${fmtFull.format(sunday)}`
    : `semaine du ${fmtFull.format(monday)} au ${fmtFull.format(sunday)}`;
}

/* -------------------------------------------------------------------------- */
/* Lecture / écriture localStorage — tolérantes aux données corrompues          */
/* -------------------------------------------------------------------------- */

const emptyState = () => ({ version: ROUTINE_VERSION, weeks: {}, updatedAt: null });

function sanitise(raw) {
  if (!raw || typeof raw !== "object" || typeof raw.weeks !== "object" || raw.weeks === null) {
    return emptyState();
  }
  const weeks = {};
  for (const [week, checks] of Object.entries(raw.weeks)) {
    if (!/^\d{4}-W\d{2}$/.test(week) || !checks || typeof checks !== "object") continue;
    const kept = {};
    for (const id of HABIT_IDS) if (checks[id] === true) kept[id] = true;
    if (Object.keys(kept).length) weeks[week] = kept;
  }
  return { version: ROUTINE_VERSION, weeks, updatedAt: raw.updatedAt ?? null };
}

function readState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? sanitise(JSON.parse(raw)) : emptyState();
  } catch {
    // localStorage désactivé (navigation privée, cookies bloqués) ou JSON invalide.
    return emptyState();
  }
}

/* -------------------------------------------------------------------------- */
/* Série de régularité                                                         */
/* -------------------------------------------------------------------------- */

/**
 * Nombre de semaines validées consécutives.
 *
 * La semaine en cours n'interrompt pas la série tant qu'elle n'est pas finie :
 * si elle n'est pas encore validée, on démarre le comptage à la semaine
 * précédente. Sinon un lundi matin remettrait tout le monde à zéro.
 */
export function computeStreak(weeks, now = new Date()) {
  const isValid = (key) => Object.keys(weeks[key] || {}).length >= WEEK_VALID_THRESHOLD;
  let offset = isValid(isoWeekKey(now)) ? 0 : 1;
  let streak = 0;
  // Garde-fou : 520 semaines = 10 ans, largement au-delà de tout usage réel.
  while (offset < 520 && isValid(weekKeyBefore(offset, now))) {
    streak += 1;
    offset += 1;
  }
  return streak;
}

/* -------------------------------------------------------------------------- */
/* Hook                                                                        */
/* -------------------------------------------------------------------------- */

export default function useWeeklyRoutine() {
  const [state, setState] = useState(readState);
  const [persistError, setPersistError] = useState(false);

  const currentWeek = isoWeekKey();

  useEffect(() => {
    if (!state.updatedAt) return; // rien à écrire tant que l'utilisateur n'a rien coché
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      setPersistError(false);
    } catch {
      setPersistError(true);
    }
  }, [state]);

  const toggleHabit = useCallback((habitId) => {
    if (!HABIT_IDS.includes(habitId)) return;
    const week = isoWeekKey();
    setState((prev) => {
      const checks = { ...(prev.weeks[week] || {}) };
      if (checks[habitId]) delete checks[habitId];
      else checks[habitId] = true;
      const weeks = { ...prev.weeks };
      if (Object.keys(checks).length) weeks[week] = checks;
      else delete weeks[week];
      return { version: ROUTINE_VERSION, weeks, updatedAt: new Date().toISOString() };
    });
  }, []);

  const resetWeek = useCallback(() => {
    const week = isoWeekKey();
    setState((prev) => {
      const weeks = { ...prev.weeks };
      delete weeks[week];
      return { version: ROUTINE_VERSION, weeks, updatedAt: new Date().toISOString() };
    });
  }, []);

  const checked = state.weeks[currentWeek] || {};
  const checkedCount = Object.keys(checked).length;

  const history = useMemo(() => {
    // Les 8 dernières semaines, de la plus ancienne à la semaine en cours.
    const out = [];
    for (let i = 7; i >= 0; i -= 1) {
      const key = weekKeyBefore(i);
      const count = Object.keys(state.weeks[key] || {}).length;
      out.push({ week: key, count, valid: count >= WEEK_VALID_THRESHOLD, isCurrent: i === 0 });
    }
    return out;
  }, [state.weeks]);

  const streak = useMemo(() => computeStreak(state.weeks), [state.weeks]);

  return {
    currentWeek,
    currentWeekLabel: weekLabel(),
    checked,
    checkedCount,
    isChecked: (id) => Boolean(checked[id]),
    toggleHabit,
    resetWeek,
    history,
    streak,
    weekValidated: checkedCount >= WEEK_VALID_THRESHOLD,
    /** true si l'écriture localStorage a échoué (navigation privée, quota). */
    persistError,
    /** Charge utile prête pour `PUT /api/bien-vieillir/routine`. */
    exportPayload: () => ({ ...state }),
  };
}
