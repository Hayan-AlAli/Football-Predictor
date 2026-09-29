import { useEffect, useState } from 'react';
import { getCalibration } from '../api/matches';
import type { CalibrationData } from '../types';

export type CalibrationState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; data: CalibrationData };

// One request per page load: the stats strip and the record panel share it.
let pending: Promise<CalibrationData> | null = null;

function loadCalibration(force = false): Promise<CalibrationData> {
  if (!pending || force) {
    pending = getCalibration().catch((err) => {
      pending = null;
      throw err;
    });
  }
  return pending;
}

/** The model's season record (accuracy, Brier, per-matchweek hits), fetched once and shared. */
export function useCalibration(): CalibrationState {
  const [state, setState] = useState<CalibrationState>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    loadCalibration()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'error' }); });
    return () => { cancelled = true; };
  }, []);

  return state;
}

/** The most recent block of decided calls (the backend groups calls in tens). */
export function lastDecidedWeek(data: CalibrationData) {
  const decided = data.rolling.filter((r) => r.decided > 0);
  return decided.length > 0 ? decided[decided.length - 1] : null;
}

/** The calibration bin nearest a 60% call, for the one-line honesty check. */
export function headlineBin(data: CalibrationData) {
  const bins = data.bins.filter((b) => b.count > 0);
  if (bins.length === 0) return null;
  return bins.reduce((best, b) => (Math.abs(b.predicted - 0.6) < Math.abs(best.predicted - 0.6) ? b : best));
}
