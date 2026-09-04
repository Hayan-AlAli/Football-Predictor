import { lazy, Suspense, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import DataProvider from './lib/data-provider';
import { BookContext } from './lib/book';
import RunningHead from './components/RunningHead';
import { useThisWeek } from './lib/gameweek';
import SectionFooter from './components/SectionFooter';
import Press from './components/Press';

const MatchdayPage = lazy(() => import('./pages/MatchdayPage'));
const MethodPage = lazy(() => import('./pages/MethodPage'));
const RecordsPage = lazy(() => import('./pages/RecordsPage'));
const TeamsPage = lazy(() => import('./pages/TeamsPage'));
const ForecastPage = lazy(() => import('./pages/ForecastPage'));
const CalibrationPage = lazy(() => import('./pages/CalibrationPage'));
const TeamDetailPage = lazy(() => import('./pages/TeamDetailPage'));

function Shell() {
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null);
  const location = useLocation();
  const thisWeek = useThisWeek();

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <BookContext.Provider value={{ selectedGameweek, setSelectedGameweek }}>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-rubric focus:text-paper focus:px-4 focus:py-2 focus:font-mono focus:text-sm focus:uppercase focus:tracking-wider-caps focus:no-underline"
      >
        Skip to content
      </a>
      <RunningHead gameweek={selectedGameweek ?? thisWeek ?? undefined} />
      <main id="main-content" className="flex-1">
        <Suspense fallback={<Press />}>
          <Routes>
            <Route path="/" element={<MatchdayPage />} />
            <Route path="/method" element={<MethodPage />} />
            <Route path="/records" element={<RecordsPage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/calibration" element={<CalibrationPage />} />
            <Route path="/teams/:teamName" element={<TeamDetailPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      <SectionFooter />
    </BookContext.Provider>
  );
}

function App() {
  return (
    <DataProvider>
      <BrowserRouter>
        <div className="flex min-h-screen flex-col">
          <Shell />
        </div>
      </BrowserRouter>
    </DataProvider>
  );
}

export default App;
