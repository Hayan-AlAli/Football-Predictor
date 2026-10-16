import { useCallback, useEffect, useState, type DependencyList } from 'react';

export type LoadState<T> =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: T };

/**
 * Load data when the component mounts and whenever `deps` change; `reload`
 * shows the loading state and tries again. An answer that arrives after a
 * newer load has started (or after unmount) is dropped.
 */
export function useLoad<T>(load: () => Promise<T>, deps: DependencyList): [LoadState<T>, () => void] {
  const [state, setState] = useState<LoadState<T>>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
    // `load` is a fresh closure every render; `deps` says when it really changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const reload = useCallback(() => {
    setState({ status: 'loading' });
    setAttempt((n) => n + 1);
  }, []);

  return [state, reload];
}
