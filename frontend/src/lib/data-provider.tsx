import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Match } from '../types';
import { getMatches, getTeams } from '../api/matches';
import { DataContext } from './data-context';
import type { DataState, TeamMeta } from './data-context';
import { seasonFromMatches } from './data-utils';
import { registerTeams } from './teams';

const CACHE_KEY = 'fp-data-cache-v2';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface Snapshot {
  matches: Match[];
  gameweeks: number[];
  teams: TeamMeta[];
}

function readCache(): Snapshot | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const entry = JSON.parse(raw) as { timestamp: number; data: Snapshot };
    if (Date.now() - entry.timestamp > CACHE_TTL) return null;
    return entry.data;
  } catch {
    return null;
  }
}

function writeCache(data: Snapshot): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ timestamp: Date.now(), data }));
  } catch {
    // sessionStorage may be full or disabled - the page works without it
  }
}

/** Matches are the ledger: if they cannot be fetched, the press is offline. */
async function fetchAll(useCache: boolean): Promise<Snapshot | null> {
  if (useCache) {
    const cached = readCache();
    if (cached) return cached;
  }
  const [season, teams] = await Promise.allSettled([getMatches(), getTeams()]);
  if (season.status === 'rejected') return null;
  const data: Snapshot = {
    matches: season.value.matches,
    gameweeks: season.value.gameweeks,
    teams: teams.status === 'fulfilled'
      ? teams.value.map((t) => ({ ...t, short_name: t.short_name ?? '', badge_url: t.badge_url ?? null }))
      : [],
  };
  writeCache(data);
  return data;
}

/** Loads the ledger once for the whole book; reload() re-presses it. */
export default function DataProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DataState['status']>('loading');
  const [snapshot, setSnapshot] = useState<Snapshot>({ matches: [], gameweeks: [], teams: [] });

  const load = useCallback((useCache: boolean, isCancelled: () => boolean = () => false) => {
    fetchAll(useCache)
      .catch(() => null)
      .then((data) => {
        if (isCancelled()) return;
        if (!data) {
          setStatus('offline');
          return;
        }
        registerTeams(data.teams);
        setSnapshot(data);
        setStatus('online');
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    load(true, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [load]);

  const reload = useCallback(() => {
    setStatus('loading');
    load(false);
  }, [load]);

  const season = useMemo(() => seasonFromMatches(snapshot.matches), [snapshot.matches]);

  const value = useMemo(
    () => ({ status, ...snapshot, season, reload }),
    [status, snapshot, season, reload]
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}
