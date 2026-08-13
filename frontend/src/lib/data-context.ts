import { createContext, useContext } from 'react';
import type { Match } from '../types';
import type { TeamMeta } from './data-utils';

export interface DataState {
  status: 'loading' | 'online' | 'offline';
  matches: Match[];
  gameweeks: number[];
  teams: TeamMeta[];
  season: string;
  reload: () => void;
}

export const DataContext = createContext<DataState>({
  status: 'loading',
  matches: [],
  gameweeks: [],
  teams: [],
  season: '',
  reload: () => {},
});

export function useData(): DataState {
  return useContext(DataContext);
}
