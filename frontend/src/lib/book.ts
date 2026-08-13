import { createContext, useContext } from 'react';

export interface BookContextValue {
  selectedGameweek: number | null;
  setSelectedGameweek: (gw: number) => void;
}

export const BookContext = createContext<BookContextValue>({
  selectedGameweek: null,
  setSelectedGameweek: () => {},
});

export function useBook(): BookContextValue {
  return useContext(BookContext);
}
