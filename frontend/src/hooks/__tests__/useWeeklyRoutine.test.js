/**
 * Tests des fonctions pures de la routine hebdomadaire.
 *
 * Le calcul de semaine ISO 8601 est la partie la plus fragile du module
 * (bascules d'année, semaine 53, dimanche/lundi). Ces repères sont vérifiables
 * à la main sur un calendrier.
 */
import { isoWeekKey, weekKeyBefore, computeStreak } from "@/hooks/useWeeklyRoutine";

const FULL = { marche: true, equilibre: true, memoire: true, lien: true };
const NOW = new Date(2026, 8, 9); // mercredi 9 septembre 2026

describe("isoWeekKey", () => {
  it("numérote la semaine courante", () => {
    expect(isoWeekKey(NOW)).toBe("2026-W37");
  });

  it("gère le dimanche comme dernier jour de la semaine ISO", () => {
    expect(isoWeekKey(new Date(2026, 8, 13))).toBe("2026-W37");
    expect(isoWeekKey(new Date(2026, 8, 14))).toBe("2026-W38");
  });

  it("gère les bascules d'année", () => {
    expect(isoWeekKey(new Date(2026, 0, 1))).toBe("2026-W01");
    expect(isoWeekKey(new Date(2021, 0, 1))).toBe("2020-W53");
    expect(isoWeekKey(new Date(2019, 11, 30))).toBe("2020-W01");
  });
});

describe("weekKeyBefore", () => {
  it("recule d'une semaine", () => {
    expect(weekKeyBefore(1, NOW)).toBe("2026-W36");
  });

  it("traverse l'année", () => {
    expect(weekKeyBefore(37, NOW)).toBe("2025-W52");
  });
});

describe("computeStreak", () => {
  it("vaut 0 sans donnée", () => {
    expect(computeStreak({}, NOW)).toBe(0);
  });

  it("compte les semaines consécutives validées", () => {
    expect(computeStreak({ "2026-W37": FULL, "2026-W36": FULL }, NOW)).toBe(2);
  });

  it("ne casse pas la série tant que la semaine en cours n'est pas finie", () => {
    expect(computeStreak({ "2026-W36": FULL, "2026-W35": FULL }, NOW)).toBe(2);
  });

  it("ignore une semaine sous le seuil", () => {
    expect(computeStreak({ "2026-W37": { marche: true } }, NOW)).toBe(0);
  });

  it("s'arrête au premier trou", () => {
    expect(computeStreak({ "2026-W37": FULL, "2026-W35": FULL }, NOW)).toBe(1);
  });
});
