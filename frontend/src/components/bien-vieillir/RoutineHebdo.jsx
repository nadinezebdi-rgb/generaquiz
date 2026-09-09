/**
 * RoutineHebdo — la routine hebdomadaire à cocher de la rubrique Bien vieillir.
 *
 * Publique et sans compte : l'état vit en localStorage (voir useWeeklyRoutine).
 * Accessibilité : chaque habitude est une vraie case à cocher, atteignable au
 * clavier, avec une cible tactile large — la page s'adresse d'abord à des
 * personnes âgées et le mode « Confort + » agrandit encore l'ensemble.
 */
import { Check, Flame, RotateCcw, Info } from "lucide-react";
import { HABITS, WEEK_VALID_THRESHOLD } from "@/content/routineHebdo";
import useWeeklyRoutine from "@/hooks/useWeeklyRoutine";

function StreakBadge({ streak }) {
  if (streak < 1) return null;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full bg-terracotta/10 px-3 py-1 text-sm font-bold text-terracotta"
      data-testid="routine-streak"
    >
      <Flame className="h-4 w-4" aria-hidden="true" />
      {streak} semaine{streak > 1 ? "s" : ""} d&apos;affilée
    </span>
  );
}

function HistoryStrip({ history }) {
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-navy/70">Vos 8 dernières semaines</p>
      <ul className="flex flex-wrap gap-1.5" data-testid="routine-history">
        {history.map((w) => {
          const state = w.valid ? "validée" : w.count > 0 ? "partielle" : "sans activité";
          return (
            <li
              key={w.week}
              title={`${w.week} — ${w.count}/${HABITS.length} · ${state}`}
              aria-label={`Semaine ${w.week} : ${w.count} sur ${HABITS.length}, ${state}`}
              className={[
                "flex h-9 w-9 items-center justify-center rounded-lg text-xs font-bold",
                w.valid
                  ? "bg-terracotta text-white"
                  : w.count > 0
                    ? "bg-mustard text-navy"
                    : "bg-cream-dark/60 text-navy/40",
                w.isCurrent ? "ring-2 ring-navy ring-offset-1" : "",
              ].join(" ")}
            >
              {w.count || "·"}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function RoutineHebdo() {
  const {
    currentWeekLabel,
    checkedCount,
    isChecked,
    toggleHabit,
    resetWeek,
    history,
    streak,
    weekValidated,
    persistError,
  } = useWeeklyRoutine();

  const total = HABITS.length;
  const progressPct = Math.round((checkedCount / total) * 100);

  return (
    <section
      className="rounded-3xl border-2 border-cream-dark bg-white p-6 shadow-warm sm:p-8"
      aria-labelledby="routine-title"
      data-testid="routine-hebdo"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="routine-title" className="font-display text-2xl font-extrabold text-navy sm:text-3xl">
            Ma routine de la semaine
          </h2>
          <p className="mt-1 text-navy/70">
            {currentWeekLabel} · {checkedCount} sur {total}
          </p>
        </div>
        <StreakBadge streak={streak} />
      </div>

      {/* Barre de progression — décorative, l'information chiffrée est au-dessus */}
      <div className="mt-5 h-3 w-full overflow-hidden rounded-full bg-cream-dark" aria-hidden="true">
        <div
          className={`h-full rounded-full transition-all duration-500 ${weekValidated ? "bg-terracotta" : "bg-mustard"}`}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <ul className="mt-6 space-y-3">
        {HABITS.map((habit) => {
          const done = isChecked(habit.id);
          return (
            <li key={habit.id}>
              <label
                className={[
                  "flex cursor-pointer items-start gap-4 rounded-2xl border-2 p-4 transition",
                  done
                    ? "border-terracotta bg-terracotta/5"
                    : "border-cream-dark bg-bgmain hover:border-mustard",
                ].join(" ")}
              >
                <input
                  type="checkbox"
                  checked={done}
                  onChange={() => toggleHabit(habit.id)}
                  className="sr-only"
                  data-testid={`routine-habit-${habit.id}`}
                />
                <span
                  aria-hidden="true"
                  className={[
                    "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2 transition",
                    done ? "border-terracotta bg-terracotta text-white" : "border-navy/30 bg-white",
                  ].join(" ")}
                >
                  {done && <Check className="h-5 w-5" strokeWidth={3} />}
                </span>
                <span className="min-w-0">
                  <span className="block text-lg font-bold text-navy">
                    <span aria-hidden="true">{habit.emoji}</span> {habit.label}
                  </span>
                  <span className="mt-0.5 block text-sm leading-relaxed text-navy/60">{habit.help}</span>
                </span>
              </label>
            </li>
          );
        })}
      </ul>

      <p
        className="mt-5 rounded-2xl bg-cream px-4 py-3 text-sm text-navy/75"
        role="status"
        data-testid="routine-status"
      >
        {weekValidated ? (
          <>
            <strong className="text-terracotta">Semaine validée.</strong> Elle compte dans votre série
            de régularité. Tout ce que vous cochez en plus est du bonus.
          </>
        ) : (
          <>
            Cochez au moins <strong>{WEEK_VALID_THRESHOLD} habitudes sur {total}</strong> pour valider
            la semaine. Il vous en reste {WEEK_VALID_THRESHOLD - checkedCount}.
          </>
        )}
      </p>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-cream-dark pt-6">
        <HistoryStrip history={history} />
        <button
          type="button"
          onClick={resetWeek}
          disabled={checkedCount === 0}
          data-testid="routine-reset"
          className="inline-flex items-center gap-2 rounded-full border-2 border-navy/20 px-4 py-2 text-sm font-bold text-navy/70 transition hover:border-navy hover:text-navy disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Réinitialiser la semaine
        </button>
      </div>

      <p className="mt-5 flex items-start gap-2 text-xs leading-relaxed text-navy/50">
        <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        {persistError ? (
          <span data-testid="routine-persist-error">
            Votre navigateur bloque l&apos;enregistrement local : vos coches ne seront pas conservées
            après la fermeture de l&apos;onglet. Vérifiez vos paramètres de cookies et de données de site.
          </span>
        ) : (
          <span>
            Vos coches restent sur cet appareil, dans votre navigateur. Rien n&apos;est envoyé à
            GénéraQuiz et aucun compte n&apos;est nécessaire.
          </span>
        )}
      </p>
    </section>
  );
}
