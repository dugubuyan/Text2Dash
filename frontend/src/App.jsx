import { useState, useEffect } from 'react';
import MainLayout from './layouts/MainLayout';
import HomePage from './pages/HomePage';
import SettingsPage from './pages/SettingsPage';
import SavedReportsPage from './pages/SavedReportsPage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

  useEffect(() => {
    // Check for token in URL (passed from landing page)
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const username = params.get('username');

    if (token) {
      localStorage.setItem('token', token);
      if (username) localStorage.setItem('username', username);

      // Clean URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'home':
        return <HomePage />;
      case 'saved-reports':
        return <SavedReportsPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <MainLayout onMenuChange={setCurrentPage}>
      {renderPage()}
    </MainLayout>
  );
}

export default App;
