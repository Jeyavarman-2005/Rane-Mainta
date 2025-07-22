import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { FiSend, FiSettings, FiSave, FiDownload, FiUpload, FiMessageSquare, FiUser, FiCpu } from 'react-icons/fi';
import { BsLightningFill, BsDatabase } from 'react-icons/bs';
import { RiRobot2Line } from 'react-icons/ri';
import { MdOutlineAttachFile } from 'react-icons/md';
import './MachineChatbot.css'; // We'll define the CSS later

const MachineChatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8000/query');
  const [darkMode, setDarkMode] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  
  const messagesEndRef = useRef(null);

  // Load saved conversations from localStorage
  useEffect(() => {
    const savedConversations = localStorage.getItem('machine-chat-conversations');
    if (savedConversations) {
      setConversations(JSON.parse(savedConversations));
    }
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      text: input,
      sender: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const result = await axios.post(apiEndpoint, {
        question: input
      });

      // Add bot response to chat
      const botMessage = {
        id: Date.now() + 1,
        text: result.data.answer,
        sender: 'bot',
        data: result.data.data,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Error: ' + (err.response?.data?.detail || err.message),
        sender: 'error',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const saveConversation = () => {
    if (messages.length === 0) return;

    const newConversation = {
      id: Date.now(),
      title: `Conversation ${conversations.length + 1}`,
      messages: [...messages],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    const updatedConversations = [...conversations, newConversation];
    setConversations(updatedConversations);
    localStorage.setItem('machine-chat-conversations', JSON.stringify(updatedConversations));
  };

  const loadConversation = (conversationId) => {
    const conversation = conversations.find(c => c.id === conversationId);
    if (conversation) {
      setMessages(conversation.messages);
      setActiveConversation(conversationId);
    }
  };

  const exportConversations = () => {
    const dataStr = JSON.stringify(conversations, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `machine-chat-conversations-${new Date().toISOString()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target.result);
        if (Array.isArray(data)) {
          setConversations(data);
          localStorage.setItem('machine-chat-conversations', JSON.stringify(data));
        }
      } catch (err) {
        setError('Invalid file format');
      }
    };
    reader.readAsText(file);
    setSelectedFile(file.name);
  };

  const clearConversation = () => {
    setMessages([]);
    setActiveConversation(null);
  };

  const suggestQuestion = (question) => {
    setInput(question);
  };

  const suggestedQuestions = [
    "What's the current status of machine X?",
    "Show me maintenance history for the last month",
    "Which machines need servicing soon?",
    "Display production metrics for today"
  ];

  return (
    <div className={`chatbot-container ${darkMode ? 'dark-mode' : ''}`}>
      <div className={`sidebar ${showSidebar ? 'open' : ''}`}>
        <div className="sidebar-header">
          <RiRobot2Line className="sidebar-icon" />
          <h3>Machine Chat</h3>
          <button onClick={() => setShowSidebar(false)} className="close-sidebar">
            &times;
          </button>
        </div>
        
        <div className="conversation-list">
          {conversations.length > 0 ? (
            conversations.map(conv => (
              <div 
                key={conv.id} 
                className={`conversation-item ${activeConversation === conv.id ? 'active' : ''}`}
                onClick={() => loadConversation(conv.id)}
              >
                <FiMessageSquare className="conversation-icon" />
                <div className="conversation-info">
                  <span className="conversation-title">{conv.title}</span>
                  <span className="conversation-date">
                    {new Date(conv.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-conversations">
              <p>No saved conversations</p>
            </div>
          )}
        </div>
        
        <div className="sidebar-actions">
          <button onClick={saveConversation} className="action-button">
            <FiSave /> Save
          </button>
          <button onClick={clearConversation} className="action-button">
            <FiMessageSquare /> New
          </button>
          <div className="file-upload-wrapper">
            <label htmlFor="file-upload" className="action-button">
              <FiUpload /> Import
            </label>
            <input 
              id="file-upload" 
              type="file" 
              accept=".json" 
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            {selectedFile && <span className="file-name">{selectedFile}</span>}
          </div>
          <button onClick={exportConversations} className="action-button">
            <FiDownload /> Export
          </button>
        </div>
      </div>
      
      <div className="chat-main">
        <div className="chat-header">
          <button 
            onClick={() => setShowSidebar(!showSidebar)} 
            className="menu-button"
          >
            ☰
          </button>
          <h2>
            <BsDatabase className="header-icon" /> Machine Data Assistant
          </h2>
          <div className="header-actions">
            <button 
              onClick={() => setSettingsOpen(!settingsOpen)}
              className={`settings-button ${settingsOpen ? 'active' : ''}`}
            >
              <FiSettings />
            </button>
            <button 
              onClick={() => setDarkMode(!darkMode)}
              className="theme-toggle"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
        
        {settingsOpen && (
          <div className="settings-panel">
            <h4>API Settings</h4>
            <div className="setting-item">
              <label>Endpoint URL:</label>
              <input 
                type="text" 
                value={apiEndpoint}
                onChange={(e) => setApiEndpoint(e.target.value)}
                placeholder="Enter API endpoint"
              />
            </div>
            <div className="setting-item">
              <label>Dark Mode:</label>
              <input 
                type="checkbox" 
                checked={darkMode}
                onChange={() => setDarkMode(!darkMode)}
              />
            </div>
          </div>
        )}
        
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-content">
                <RiRobot2Line className="welcome-icon" />
                <h3>Machine Data Assistant</h3>
                <p>Ask questions about your industrial machines, maintenance records, production data, and more.</p>
                
                <div className="quick-questions">
                  <h4>Try asking:</h4>
                  {suggestedQuestions.map((q, i) => (
                    <div 
                      key={i} 
                      className="suggested-question"
                      onClick={() => suggestQuestion(q)}
                    >
                      <BsLightningFill className="lightning-icon" />
                      {q}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div 
                key={message.id} 
                className={`message ${message.sender}`}
              >
                <div className="message-sender">
                  {message.sender === 'user' ? (
                    <FiUser className="sender-icon" />
                  ) : message.sender === 'error' ? (
                    <span className="error-icon">⚠️</span>
                  ) : (
                    <FiCpu className="sender-icon" />
                  )}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.text}</div>
                  {message.data && message.data.length > 0 && (
                    <div className="message-data">
                      <details>
                        <summary>View {message.data.length} data records</summary>
                        <pre>{JSON.stringify(message.data, null, 2)}</pre>
                      </details>
                    </div>
                  )}
                  <div className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message bot">
              <div className="message-sender">
                <FiCpu className="sender-icon" />
              </div>
              <div className="message-content">
                <div className="loading-dots">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <form onSubmit={handleSubmit} className="chat-input-area">
          <div className="file-attach">
            <label htmlFor="file-attach-input">
              <MdOutlineAttachFile className="attach-icon" />
            </label>
            <input 
              id="file-attach-input" 
              type="file" 
              style={{ display: 'none' }}
            />
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about machine data..."
            disabled={loading}
            className="chat-input"
          />
          <button 
            type="submit" 
            disabled={loading || !input.trim()}
            className="send-button"
          >
            {loading ? (
              <div className="spinner"></div>
            ) : (
              <FiSend className="send-icon" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default MachineChatbot;