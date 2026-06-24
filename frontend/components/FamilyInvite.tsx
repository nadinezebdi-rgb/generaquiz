'use client';

import { useEffect, useMemo, useState } from 'react';

export interface FamilyJoinResult {
  playerId: string;
  pseudo: string;
  familyId: string;
  familyName: string;
  inviteCode?: string;
}

interface FamilyInviteProps {
  mode: 'create' | 'join';
  onSuccess: (data: FamilyJoinResult) => void;
}

interface FamilyLookupResult {
  family_id: string;
  name: string;
  nb_players: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const AVATARS = ['👴', '👵', '👨', '👩', '🧒'];

function normalizeInviteCode(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6);
}

async function readApiError(response: Response): Promise<string> {
  try {
    const payload = await response.json();
    if (typeof payload.detail === 'string') {
      return payload.detail;
    }
  } catch {
    // Le corps n'est pas toujours du JSON : on garde alors un message générique.
  }

  return 'Une erreur est survenue. Réessayez dans un instant.';
}

export default function FamilyInvite({ mode, onSuccess }: FamilyInviteProps) {
  const [activeMode, setActiveMode] = useState<'create' | 'join'>(mode);
  const [familyName, setFamilyName] = useState('');
  const [pseudo, setPseudo] = useState('');
  const [avatar, setAvatar] = useState(AVATARS[0]);
  const [inviteCode, setInviteCode] = useState('');
  const [lookupFamily, setLookupFamily] = useState<FamilyLookupResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingCode, setCheckingCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<FamilyJoinResult | null>(null);
  const [copied, setCopied] = useState(false);

  const canSubmit = useMemo(() => {
    if (loading) {
      return false;
    }

    if (activeMode === 'create') {
      return familyName.trim().length >= 2 && pseudo.trim().length >= 2;
    }

    return inviteCode.length === 6 && pseudo.trim().length >= 2;
  }, [activeMode, familyName, inviteCode, loading, pseudo]);

  useEffect(() => {
    setActiveMode(mode);
  }, [mode]);

  useEffect(() => {
    if (activeMode !== 'join') {
      return;
    }

    setLookupFamily(null);
    setError(null);

    if (inviteCode.length !== 6) {
      return;
    }

    const controller = new AbortController();
    setCheckingCode(true);

    // Validation en temps réel dès que le code atteint 6 caractères.
    fetch(`${API_URL}/api/family/by-code/${inviteCode}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await readApiError(response));
        }
        return response.json() as Promise<FamilyLookupResult>;
      })
      .then((data) => setLookupFamily(data))
      .catch((nextError: Error) => {
        if (nextError.name !== 'AbortError') {
          setLookupFamily(null);
          setError(nextError.message || 'Code introuvable.');
        }
      })
      .finally(() => setCheckingCode(false));

    return () => controller.abort();
  }, [activeMode, inviteCode]);

  function switchMode(nextMode: 'create' | 'join') {
    setActiveMode(nextMode);
    setError(null);
    setSuccess(null);
    setCopied(false);
    setLookupFamily(null);
  }

  async function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(await readApiError(response));
    }

    return response.json() as Promise<T>;
  }

  async function handleCreate() {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const createdFamily = await postJson<{ family_id: string; name: string; invite_code: string }>(
        '/api/family/create',
        { name: familyName.trim() },
      );

      // Le créateur rejoint automatiquement sa famille avec le code fraîchement généré.
      const joined = await postJson<{ player_id: string; pseudo: string; family_id: string; family_name: string }>(
        '/api/family/join',
        { invite_code: createdFamily.invite_code, pseudo: pseudo.trim(), avatar },
      );

      const result: FamilyJoinResult = {
        playerId: joined.player_id,
        pseudo: joined.pseudo,
        familyId: joined.family_id,
        familyName: joined.family_name,
        inviteCode: createdFamily.invite_code,
      };

      setSuccess(result);
      onSuccess(result);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Création impossible pour le moment.');
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin() {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const joined = await postJson<{ player_id: string; pseudo: string; family_id: string; family_name: string }>(
        '/api/family/join',
        { invite_code: inviteCode, pseudo: pseudo.trim(), avatar },
      );

      const result: FamilyJoinResult = {
        playerId: joined.player_id,
        pseudo: joined.pseudo,
        familyId: joined.family_id,
        familyName: joined.family_name,
      };

      setSuccess(result);
      onSuccess(result);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Impossible de rejoindre cette famille.');
    } finally {
      setLoading(false);
    }
  }

  async function copyInviteCode() {
    if (!success?.inviteCode || typeof navigator === 'undefined') {
      return;
    }

    await navigator.clipboard.writeText(success.inviteCode);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <section className="mx-auto w-full max-w-xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      {/* @section: family-invite-toggle */}
      <div className="mb-6 grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1">
        <button
          type="button"
          onClick={() => switchMode('create')}
          className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
            activeMode === 'create' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Créer une famille
        </button>
        <button
          type="button"
          onClick={() => switchMode('join')}
          className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
            activeMode === 'join' ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          Rejoindre une famille
        </button>
      </div>

      {/* @section: family-invite-form */}
      <div className="space-y-5">
        {activeMode === 'create' ? (
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Nom de famille</span>
            <input
              value={familyName}
              onChange={(event) => setFamilyName(event.target.value)}
              maxLength={50}
              placeholder="Famille Martin"
              className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            />
          </label>
        ) : (
          <div>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Code d'invitation</span>
              <input
                value={inviteCode}
                onChange={(event) => setInviteCode(normalizeInviteCode(event.target.value))}
                maxLength={6}
                placeholder="ABC234"
                className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-center text-lg font-bold uppercase tracking-[0.35em] outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              />
            </label>
            {checkingCode ? (
              <p className="mt-2 text-sm text-slate-500">Vérification du code…</p>
            ) : lookupFamily ? (
              <p className="mt-2 rounded-2xl bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
                Famille trouvée : {lookupFamily.name} · {lookupFamily.nb_players} membre
                {lookupFamily.nb_players > 1 ? 's' : ''}
              </p>
            ) : null}
          </div>
        )}

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Pseudo</span>
          <input
            value={pseudo}
            onChange={(event) => setPseudo(event.target.value)}
            maxLength={40}
            placeholder="MamieQuiz, TontonRetro…"
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
          />
        </label>

        <fieldset>
          <legend className="text-sm font-medium text-slate-700">Avatar</legend>
          <div className="mt-2 grid grid-cols-5 gap-2">
            {AVATARS.map((item) => (
              <label key={item} className="cursor-pointer">
                <input
                  type="radio"
                  name="avatar"
                  value={item}
                  checked={avatar === item}
                  onChange={() => setAvatar(item)}
                  className="sr-only"
                />
                <span
                  className={`flex aspect-square items-center justify-center rounded-2xl border text-2xl transition ${
                    avatar === item
                      ? 'border-amber-400 bg-amber-50 ring-2 ring-amber-100'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  {item}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <button
          type="button"
          disabled={!canSubmit}
          onClick={activeMode === 'create' ? handleCreate : handleJoin}
          className="w-full rounded-2xl bg-slate-950 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {loading ? 'Patientez…' : activeMode === 'create' ? 'Créer' : 'Rejoindre'}
        </button>
      </div>

      {/* @section: family-invite-success */}
      {success ? (
        <div className="mt-6 rounded-3xl border border-emerald-200 bg-emerald-50 p-5 text-center">
          <p className="text-sm font-semibold text-emerald-700">
            Bienvenue dans {success.familyName}, {success.pseudo} !
          </p>
          {success.inviteCode ? (
            <div className="mt-4">
              <p className="text-xs uppercase tracking-wide text-emerald-700">Code à partager</p>
              <p className="mt-2 text-3xl font-black tracking-[0.25em] text-slate-950">{success.inviteCode}</p>
              <button
                type="button"
                onClick={copyInviteCode}
                className="mt-4 rounded-full bg-white px-4 py-2 text-sm font-semibold text-emerald-700 ring-1 ring-emerald-200 transition hover:bg-emerald-100"
              >
                {copied ? 'Copié !' : 'Copier'}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
