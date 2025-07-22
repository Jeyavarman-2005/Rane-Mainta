import React, { useState, useEffect } from 'react';
import MachineChatbot from './MachineChatbot';
import Login from './Login';
import './App.css';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [currentPlant, setCurrentPlant] = useState('master');
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    // Check for existing auth on initial load
    const authToken = sessionStorage.getItem('authToken');
    if (authToken) {
      // Extract plant from the token (username is the plant in your system)
      try {
        const decoded = atob(authToken);
        const username = decoded.split(':')[0];
        const plant = USER_DATABASE[username]?.plant || 'master';
        
        setCurrentPlant(plant);
        setLoggedIn(true);
      } catch (e) {
        console.error("Error decoding token:", e);
        sessionStorage.removeItem('authToken');
      }
    }
    setIsCheckingAuth(false);
  }, []);

  const handleLogin = (plant) => {
    setCurrentPlant(plant);
    setLoggedIn(true);
  };

  const handleLogout = () => {
    setLoggedIn(false);
    setCurrentPlant('master');
    sessionStorage.removeItem('authToken');
  };

  if (isCheckingAuth) {
    return <div className="App">Loading...</div>; // Or a loading spinner
  }

  return (
    <div className="App">
      {!loggedIn ? (
        <Login onLogin={handleLogin} />
      ) : (
        <MachineChatbot 
          plant={currentPlant} 
          onLogout={handleLogout} 
        />
      )}
    </div>
  );
}

// This should match your Login.js user database
const USER_DATABASE = {
  "master": {"password": "masterpass", "plant": "Master"},
  "plant1150": {"password": "plant1150pass", "plant": "1150"},
  "plant1200": {"password": "plant1200pass", "plant": "1200"},
  "plant1250": {"password": "plant1250pass", "plant": "1250"},
  "plant1300": {"password": "plant1300pass", "plant": "1300"}
};

export default App;