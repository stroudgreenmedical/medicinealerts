import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { useState, useEffect } from 'react';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AlertsList from './pages/AlertsList';
import AlertDetail from './pages/AlertDetail';
import Analytics from './pages/Analytics';
import Layout from './components/Layout';

// NHS color theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#005EB8', // NHS Blue
      light: '#0072CE',
      dark: '#003D78',
    },
    secondary: {
      main: '#768692', // NHS Grey
    },
    error: {
      main: '#D5281B', // NHS Red
    },
    warning: {
      main: '#FA9200', // NHS Amber
    },
    success: {
      main: '#00703C', // NHS Green
    },
    background: {
      default: '#F0F4F5',
      paper: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: 'Arial, sans-serif',
    h1: {
      fontSize: '2rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    body1: {
      fontSize: '1rem',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 4,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        },
      },
    },
  },
});

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('token');
    setIsAuthenticated(!!token);
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route 
            path="/login" 
            element={
              isAuthenticated ? 
                <Navigate to="/dashboard" /> : 
                <Login onLogin={handleLogin} />
            } 
          />
          
          <Route
            path="/"
            element={
              isAuthenticated ? 
                <Layout onLogout={handleLogout} /> : 
                <Navigate to="/login" />
            }
          >
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="alerts" element={<AlertsList />} />
            <Route path="alerts/:id" element={<AlertDetail />} />
            <Route path="analytics" element={<Analytics />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App
