import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  FiSend, FiSettings, FiSave, FiDownload, FiUpload, 
  FiMessageSquare, FiUser, FiCpu, FiX, FiMenu 
} from 'react-icons/fi';
import { 
  BsLightningFill, BsDatabase, BsRobot, BsCheckCircleFill 
} from 'react-icons/bs';
import { RiRobot2Line, RiFileExcel2Line } from 'react-icons/ri';
import { 
  MdOutlineAttachFile, MdOutlineDashboard, MdOutlineAnalytics,
  MdOutlineSupport, MdOutlineHistory, MdOutlineFeedback 
} from 'react-icons/md';
import { IoMdNotificationsOutline } from 'react-icons/io';
import { BiSolidUserCircle } from 'react-icons/bi';
import { TbChartArcs } from 'react-icons/tb';
import logo from './rane-logo.png';
import './MachineChatbot.css';

// Import components
import Header from './components/Header';
import Footer from './components/Footer';
import Chatbot from './components/Chatbot';
import Dashboard from './components/Dashboard/Dashboard';
import BreakdownData from './components/BreakdownData/BreakdownData';
import ChatHistory from './components/ChatHistory';

const MachineChatbot = ({ plant, onLogout }) => {
   const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [apiEndpoint, setApiEndpoint] = useState('http://localhost:8000/api/chat');
  const [selectedFile, setSelectedFile] = useState(null);
  const [exampleQuestions, setExampleQuestions] = useState([]);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('chat');
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [typingIndicator, setTypingIndicator] = useState(false);
  const [showMenuDropdown, setShowMenuDropdown] = useState(false);
  const [isBotResponding, setIsBotResponding] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const loadConversation = (conversationId) => {
    const conversation = conversations.find(c => c.id === conversationId);
    if (conversation) {
      setMessages(conversation.messages);
      setActiveConversation(conversationId);
    }
  };
  
  // Format text with markdown-like syntax
  const formatText = (text) => {
    if (!text) return text;
    
    // Replace **text** with bold
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Replace ### text with heading
    formattedText = formattedText.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    
    // Replace lists
    formattedText = formattedText.replace(/^\s*-\s(.*$)/gm, '<li>$1</li>');
    
    return formattedText;
  };

  useEffect(() => {
    const savedConversations = localStorage.getItem('rane-mainta-conversations');
    if (savedConversations) {
      setConversations(JSON.parse(savedConversations));
    }
    
    fetchExampleQuestions();
    
    // Focus input on load
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, typingIndicator]);

  const fetchExampleQuestions = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/examples');
      setExampleQuestions(response.data.examples);
    } catch (err) {
      console.error("Couldn't fetch example questions:", err);
      setExampleQuestions([
        "Show me recent breakdowns of IBJ Assy - 02",
        "What is the MTBF for machine 10009627?",
        "List electrical issues from last week",
        "Compare downtime between Plant 1150 and 1151"
      ]);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const simulateTyping = async () => {
    setTypingIndicator(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    setTypingIndicator(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = {
      id: Date.now(),
      text: input,
      sender: 'user',
      timestamp: new Date().toISOString(),
      avatar: null
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError(null);
    
    // Show typing indicator
    await simulateTyping();

    try {
      const authAxios = createAuthAxios();
      const response = await authAxios.post('/api/chat', {
        question: input
      });

      const botMessage = {
        id: Date.now() + 1,
        text: response.data.answer || response.data.response,
        sender: 'bot',
        timestamp: new Date().toISOString(),
        sources: response.data.sources || [],
        processingTime: response.data.processing_time,
        breakdownType: response.data.breakdown_type,
        avatar: logo
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error("API Error:", err);
      setError(err.response?.data?.detail || err.message);
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Error: ' + (err.response?.data?.detail || err.message || 'Failed to get response'),
        sender: 'error',
        timestamp: new Date().toISOString(),
        avatar: null
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setActiveConversation(null);
  };

  const suggestQuestion = (question) => {
    setInput(question);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const markNotificationAsRead = (id) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? {...n, read: true} : n)
    );
  };

  const createAuthAxios = () => {
    const authToken = sessionStorage.getItem('authToken');
    return axios.create({
      baseURL: 'http://localhost:8000',
      headers: {
        'Authorization': `Basic ${authToken}`,
        'Content-Type': 'application/json'
      }
    });
  };

  const renderSources = (sources) => {
    if (!sources || sources.length === 0) return null;

    const filteredSources = sourceFilter === 'all' 
      ? sources 
      : sources.filter(source => source.breakdown_type?.toLowerCase() === sourceFilter.toLowerCase());

    if (filteredSources.length === 0) {
      return <div className="no-sources">No {sourceFilter} sources found</div>;
    }

    return (
      <div className="sources-container">
        <div className="sources-header">
          <h4>Reference Data</h4>
          <select 
            value={sourceFilter} 
            onChange={(e) => setSourceFilter(e.target.value)}
            className="source-filter"
          >
            <option value="all">All Types</option>
            <option value="mechanical">Mechanical</option>
            <option value="electrical">Electrical</option>
            <option value="hydraulic">Hydraulic</option>
            <option value="pneumatic">Pneumatic</option>
          </select>
        </div>
        
        <div className="sources-grid">
          {filteredSources.map((source, index) => (
            <div key={index} className="source-card">
              <div className="source-card-header">
                <h5>{source.machine || 'Unknown Machine'}</h5>
                <span className={`breakdown-tag ${source.breakdown_type?.toLowerCase() || 'other'}`}>
                  {source.breakdown_type || 'Unknown Type'}
                </span>
              </div>
              <div className="source-card-body">
                <p><strong>SAP Code:</strong> {source.sap_code || 'N/A'}</p>
                <p><strong>Location:</strong> {source.plant} / {source.shop}</p>
                <p><strong>Time:</strong> {source.start_time || 'N/A'} ({source.duration || 'N/A'})</p>
                <p><strong>Problem:</strong> {source.problem_type || 'N/A'}</p>
                <p><strong>Root Cause:</strong> {source.actual_reason || 'N/A'}</p>
                <p><strong>Resolution:</strong> {source.closure_reason || 'N/A'}</p>
              </div>
              <div className="source-card-footer">
                <button className="source-action-btn">
                  <RiFileExcel2Line /> Export
                </button>
                <button className="source-action-btn">
                  <MdOutlineAnalytics /> Analyze
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
     <div className="chatbot-container">
    {/* Chat History Sidebar */}
    {activeTab === 'chat' && (
      <ChatHistory 
        messages={messages}
        conversations={conversations}
        activeConversation={activeConversation}
        setMessages={setMessages}
        setConversations={setConversations}
        setActiveConversation={setActiveConversation}
        setNotifications={setNotifications}
        setError={setError}
        setSelectedFile={setSelectedFile}
        selectedFile={selectedFile}
        setShowSidebar={setShowSidebar}
        clearConversation={clearConversation}
        showSidebar={showSidebar}
        logo={logo}
        activeTab={activeTab}
      />
    )}
    
    {/* Main Chat Area */}
    <div className={`chat-main ${activeTab !== 'chat' ? 'full-width' : ''}`}>
      {/* Header */}
        <Header 
          showMenuDropdown={showMenuDropdown}
          setShowMenuDropdown={setShowMenuDropdown}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          setShowNotifications={setShowNotifications}
          showNotifications={showNotifications}
          notifications={notifications}
          markNotificationAsRead={markNotificationAsRead}
          settingsOpen={settingsOpen}
          setSettingsOpen={setSettingsOpen}
          apiEndpoint={apiEndpoint}
          setApiEndpoint={setApiEndpoint}
          plant={plant}
          onLogout={onLogout}
          setShowSidebar={setShowSidebar}
        />
        
        {/* Tab Content */}
        {activeTab === 'chat' && (
          <Chatbot 
            messages={messages}
            loading={loading}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            inputRef={inputRef}
            exampleQuestions={exampleQuestions}
            suggestQuestion={suggestQuestion}
            formatText={formatText}
            renderSources={renderSources}
            messagesEndRef={messagesEndRef}
            typingIndicator={typingIndicator}
          />
        )}
        
        {activeTab === 'dashboard' && <Dashboard />}
        
        {activeTab === 'breakdown-data' && <BreakdownData plant={plant} />}
        
        {activeTab === 'history' && (
          <div className="dashboard-tab">
            <h3>Conversation History</h3>
            {conversations.length > 0 ? (
              <div className="conversation-list">
                {conversations.map(conv => (
                  <div 
                    key={conv.id} 
                    className={`conversation-item ${activeConversation === conv.id ? 'active' : ''}`}
                    onClick={() => loadConversation(conv.id)}
                  >
                    <FiMessageSquare className="conversation-icon" />
                    <div className="conversation-info">
                      <span className="conversation-title">{conv.title}</span>
                      <span className="conversation-date">
                        {new Date(conv.createdAt).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No conversation history yet. Start chatting to save conversations.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default MachineChatbot;