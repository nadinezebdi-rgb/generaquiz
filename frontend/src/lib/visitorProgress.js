// Série « question de Lucette » sur l'appareil + mini-quiz en attente de compte.
const STREAK_KEY = "gq_tip_streak";
const PENDING_MINI_KEY = "gq_pending_mini";
const MINI_TTL_MS = 8 * 24 * 3600 * 1000;

export const parisToday = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Paris" }).format(new Date());

const yesterdayOf = (key) => {
  const d = new Date(`${key}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
};

const read = (k) => {
  try { return JSON.parse(localStorage.getItem(k) || "null"); } catch { return null; }
};

export function loadStreak() {
  const st = read(STREAK_KEY) || { count: 0, best: 0, last_date: null, last_result: null, answers: {} };
  const today = parisToday();
  const alive = st.last_date === today || st.last_date === yesterdayOf(today);
  return { ...st, answers: st.answers || {}, count: alive ? st.count : 0, answered_today: st.last_date === today };
}

export function saveStreak(st) {
  const answers = Object.fromEntries(Object.entries(st.answers || {}).sort().slice(-14));
  localStorage.setItem(STREAK_KEY, JSON.stringify({ ...st, answers }));
}

// Applique la réponse du jour (jamais deux fois le même jour).
export function applyTodayAnswer(correct, result, choice) {
  const st = loadStreak();
  const today = parisToday();
  const answers = { ...st.answers, [today]: { ...result, picked: choice } };
  if (st.last_date === today) return { ...st, answers };
  const prev = st.last_date === yesterdayOf(today) && st.last_result ? st.count : 0;
  const count = correct ? prev + 1 : 0;
  const next = { count, best: Math.max(st.best || 0, count), last_date: today, last_result: correct, answers, answered_today: true };
  saveStreak(next);
  return next;
}

export function adoptAccountStreak(server) {
  const st = loadStreak();
  const next = { ...st, count: server.count, best: server.best, last_date: server.last_date, last_result: server.last_result };
  saveStreak(next);
  return loadStreak();
}

export function savePendingMini(categoryId, answers) {
  localStorage.setItem(PENDING_MINI_KEY, JSON.stringify({ category_id: categoryId, answers, at: Date.now() }));
}

export function takePendingMini() {
  const p = read(PENDING_MINI_KEY);
  localStorage.removeItem(PENDING_MINI_KEY);
  return p && Date.now() - p.at < MINI_TTL_MS ? p : null;
}
