import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import DataProvider from './lib/data-provider';
import { BookContext } from './lib/book';
import RunningHead from './components/RunningHead';
import SectionFooter from './components/SectionFooter';
import MatchdayPage from './pages/MatchdayPage';
import MethodPage from './pages/MethodPage';
import RecordsPage from './pages/RecordsPage';
import TeamsPage from './pages/TeamsPage';

function Shell() {
  const [selectedGameweek, setSelectedGameweek] = useState<number | null>(null);
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  return (
    <BookContext.Provider value={{ selectedGameweek, setSelectedGameweek }}>
      <RunningHead gameweek={selectedGameweek ?? undefined} />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<MatchdayPage />} />
          <Route path="/method" element={<MethodPage />} />
          <Route path="/records" element={<RecordsPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
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
