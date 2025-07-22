import React, { useState } from 'react';
import axios from 'axios';
import './Login.css';
import { FaEye, FaEyeSlash } from 'react-icons/fa'; // Import eye icons

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false); // State for password visibility
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
    const handleSubmit = async (e) => {
      e.preventDefault();
      setIsLoading(true);
      setError('');
      
      try {
        const auth = btoa(`${username}:${password}`);
        sessionStorage.setItem('authToken', auth);
        
        const response = await axios.post('http://localhost:8000/api/login', {}, {
          headers: { 'Authorization': `Basic ${auth}` }
        });
        
        onLogin(response.data.plant);
      } catch (err) {
        sessionStorage.removeItem('authToken');
        setError('Invalid username or password');
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <div className="login-container">
        <div className="login-glass-card">
          <div className="login-branding">
            <img src="/rane-mainta-logo.png" alt="Rane-Mainta Logo" className="login-logo" />
            <h1 className="login-title">Rane-Mainta</h1>
            <p className="login-subtitle">Machine Breakdown Analysis System</p>
          </div>
          
          <form className="login-form" onSubmit={handleSubmit}>
        {error && <div className="login-error-message">{error}</div>}
        
        <div className="login-input-group">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder=" "
            required
            className="login-input"
          />
          <label className={`login-input-label ${username ? 'login-input-label-hidden' : ''}`}>
            Username
          </label>
          <span className="login-input-highlight"></span>
        </div>
        
        <div className="login-input-group">
        <input
          type={showPassword ? "text" : "password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onFocus={() => setIsPasswordFocused(true)}
          onBlur={() => setIsPasswordFocused(false)}
          placeholder=" "
          required
          className="login-input"
        />
        <label className={`login-input-label ${password ? 'login-input-label-hidden' : ''}`}>
          Password
        </label>
        <span className="login-input-highlight"></span>
        {(isPasswordFocused || password) && (
          <button 
            type="button" 
            className="login-password-toggle"
            onClick={() => setShowPassword(!showPassword)}
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <FaEyeSlash /> : <FaEye />}
          </button>
        )}
      </div>
            
            <button 
              type="submit" 
              className="login-submit-button"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="login-spinner"></span>
                  Authenticating...
                </>
              ) : (
                'Login to Dashboard'
              )}
            </button>
          </form>
          
          
        </div>
        
        <div className="login-background">
          <div className="login-bg-circle-1"></div>
          <div className="login-bg-circle-2"></div>
          <div className="login-bg-circle-3"></div>
        </div>
      </div>
    );
  };

  export default Login;