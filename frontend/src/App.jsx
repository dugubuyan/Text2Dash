import { useState } from 'react';
import MainLayout from './layouts/MainLayout';
import HomePage from './pages/HomePage';
import SettingsPage from './pages/SettingsPage';
import SavedReportsPage from './pages/SavedReportsPage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('home');

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
