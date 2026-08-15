import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Match } from '../types';
import { checkHealth, getAllMatches, getTeams } from '../api/matches';
import { DataContext } from './data-context';
import type { DataState } from './data-context';
import { seasonFromMatches } from './data-utils';

const CACHE_KEY = 'fp-data-cache';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface CacheEntry {
  timestamp: number;
  data: { matches: Match[]; gameweeks: number[]; teams: DataState['teams'] };
}

function getCachedData(): CacheEntry | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const entry: CacheEntry = JSON.parse(raw);
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      sessionStorage.removeItem(CACHE_KEY);
      return null;
    }
    return entry;
  } catch {
    return null;
  }
}

function setCachedData(data: CacheEntry['data']): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ timestamp: Date.now(), data }));
  } catch {
    // sessionStorage may be full or disabled — ignore silently
  }
}

type FetchResult =
  | { status: 'offline' }
  | { status: 'online'; matches: Match[]; gameweeks: number[]; teams: DataState['teams'] };

async function fetchAll(useCache = true): Promise<FetchResult> {
  if (useCache) {
    const cached = getCachedData();
    if (cached) return { status: 'online', ...cached.data };
  }

  const isOnline = await checkHealth();
  if (!isOnline) return { status: 'offline' };
  const [all, teamData] = await Promise.allSettled([getAllMatches(), getTeams()]);
  const data = {
    matches: all.status === 'fulfilled' ? all.value.matches : [],
    gameweeks: all.status === 'fulfilled' ? all.value.gameweeks : [],
    teams:
      teamData.status === 'fulfilled'
        ? teamData.value.map((t) => ({ name: t.name, short_name: '', badge_url: t.badge_url ?? null }))
        : [],
  };
  setCachedData(data);
  return { status: 'online', ...data };
}

/** Loads the ledger once for the whole book; reload() re-presses it. */
export default function DataProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DataState['status']>('loading');
  const [matches, setMatches] = useState<Match[]>([]);
  const [gameweeks, setGameweeks] = useState<number[]>([]);
  const [teams, setTeams] = useState<DataState['teams']>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const res = await fetchAll();
      if (cancelled) return;
      if (res.status === 'offline') {
        setStatus('offline');
        return;
      }
      setMatches(res.matches);
      setGameweeks(res.gameweeks);
      setTeams(res.teams);
      setStatus('online');
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const reload = useCallback(() => {
    setStatus('loading');
    (async () => {
      try {
        const res = await fetchAll(false);
        if (res.status === 'offline') {
          setStatus('offline');
          return;
        }
        setMatches(res.matches);
        setGameweeks(res.gameweeks);
        setTeams(res.teams);
        setStatus('online');
      } catch {
        setStatus('offline');
      }
    })();
  }, []);

  const season = useMemo(() => seasonFromMatches(matches), [matches]);

  const value = useMemo(
    () => ({ status, matches, gameweeks, teams, season, reload }),
    [status, matches, gameweeks, teams, season, reload]
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}
