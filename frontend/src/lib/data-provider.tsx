import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { Match } from '../types';
import { checkHealth, getAllMatches, getTeams } from '../api/matches';
import { DataContext } from './data-context';
import type { DataState } from './data-context';
import { seasonFromMatches } from './data-utils';

type FetchResult =
  | { status: 'offline' }
  | { status: 'online'; matches: Match[]; gameweeks: number[]; teams: DataState['teams'] };

async function fetchAll(): Promise<FetchResult> {
  const isOnline = await checkHealth();
  if (!isOnline) return { status: 'offline' };
  const [all, teamData] = await Promise.allSettled([getAllMatches(), getTeams()]);
  return {
    status: 'online',
    matches: all.status === 'fulfilled' ? all.value.matches : [],
    gameweeks: all.status === 'fulfilled' ? all.value.gameweeks : [],
    teams:
      teamData.status === 'fulfilled'
        ? teamData.value.map((t) => ({ name: t.name, short_name: '', badge_url: t.badge_url ?? null }))
        : [],
  };
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
      const res = await fetchAll();
      if (res.status === 'offline') {
        setStatus('offline');
        return;
      }
      setMatches(res.matches);
      setGameweeks(res.gameweeks);
      setTeams(res.teams);
      setStatus('online');
    })();
  }, []);

  const season = useMemo(() => seasonFromMatches(matches), [matches]);

  const value = useMemo(
    () => ({ status, matches, gameweeks, teams, season, reload }),
    [status, matches, gameweeks, teams, season, reload]
  );

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}
