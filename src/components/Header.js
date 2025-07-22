import React, { useEffect, useRef } from 'react';
import { FiMenu } from 'react-icons/fi';
import { RiRobot2Line } from 'react-icons/ri';
import { 
  MdOutlineDashboard, MdOutlineAnalytics,
  MdOutlineHistory 
} from 'react-icons/md';
import logo from '../rane-logo.png';
import './Header.css';

const Header = ({ 
  showMenuDropdown, 
  setShowMenuDropdown,
  activeTab,
  setActiveTab,
  plant,
  onLogout
}) => {
  const dropdownRef = useRef(null);
  const menuButtonRef = useRef(null);

  useEffect(() => {
  const handleClickOutside = (event) => {
    if (
      showMenuDropdown && 
      dropdownRef.current && 
      !dropdownRef.current.contains(event.target)
    ) {
      if (menuButtonRef.current && !menuButtonRef.current.contains(event.target)) {
        setShowMenuDropdown(false);
      }
    }
  };

  document.addEventListener('mousedown', handleClickOutside);
  return () => {
    document.removeEventListener('mousedown', handleClickOutside);
  };
}, [showMenuDropdown, setShowMenuDropdown]);


  return (
    <div className="chat-header">
      <div className="header-left">
        <button 
          ref={menuButtonRef}
          onClick={() => setShowMenuDropdown(!showMenuDropdown)} 
          className="menu-button"
        >
          <FiMenu className="menu-icon" />
        </button>
        {showMenuDropdown && (
          <div className="menu-dropdown" ref={dropdownRef}>
            <div 
              className={`menu-item ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('chat');
                setShowMenuDropdown(false);
              }}
            >
              <RiRobot2Line className="menu-icon" /> 
              <span className="menu-text">Chat</span>
            </div>
            <div 
              className={`menu-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('dashboard');
                setShowMenuDropdown(false);
              }}
            >
              <MdOutlineDashboard className="menu-icon" /> 
              <span className="menu-text">Dashboard</span>
            </div>
            <div 
              className={`menu-item ${activeTab === 'breakdown-data' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('breakdown-data');
                setShowMenuDropdown(false);
              }}
            >
              <MdOutlineAnalytics className="menu-icon" /> 
              <span className="menu-text">Breakdown Data</span>
            </div>
            <div 
              className={`menu-item ${activeTab === 'history' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('history');
                setShowMenuDropdown(false);
              }}
            >
              <MdOutlineHistory className="menu-icon" /> 
              <span className="menu-text">History</span>
            </div>
          </div>
        )}
      </div>

      <div className="header-center">
        <div className="header-logo">
          <img src={logo} alt="Rane Mainta" className="bot-avatar" />
          <div className="header-title">
            <h2>Rane Mainta - {plant}</h2>
            <p>Industrial Maintenance Assistant</p>
          </div>
        </div>
      </div>
      
      <div className="header-right">
        <button 
          onClick={onLogout}
          className="logout-button"
        >
          <span className="logout-text">Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Header;