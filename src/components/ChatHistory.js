import React from 'react';
import { FiSave, FiDownload, FiUpload, FiMessageSquare, FiX } from 'react-icons/fi';
import './ChatHistory.css';
import logo from '.././rane-logo.png';

const ChatHistory = ({
  messages,
  conversations,
  activeConversation,
  setMessages,
  setConversations,
  setActiveConversation,
  setNotifications,
  setShowSidebar,
  clearConversation,
  setError,
  setSelectedFile,
  selectedFile,
  activeTab,
  showSidebar
}) => {
  const saveConversation = () => {
    if (messages.length === 0) return;

    const firstUserMessage = messages.find(m => m.sender === 'user');
    const title = firstUserMessage 
      ? firstUserMessage.text.slice(0, 30) + (firstUserMessage.text.length > 30 ? '...' : '')
      : `Conversation ${conversations.length + 1}`;

    const newConversation = {
      id: Date.now(),
      title: title,
      messages: [...messages],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    const updatedConversations = [...conversations, newConversation];
    setConversations(updatedConversations);
    localStorage.setItem('rane-mainta-conversations', JSON.stringify(updatedConversations));
    
    // Show success notification
    const notification = {
      id: Date.now(),
      title: "Conversation saved",
      message: `"${title}" has been saved to your history`,
      timestamp: new Date().toISOString(),
      read: false,
      type: "success"
    };
    setNotifications(prev => [notification, ...prev]);
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
    
    const exportFileDefaultName = `rane-mainta-conversations-${new Date().toISOString()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    // Show success notification
    const notification = {
      id: Date.now(),
      title: "Export successful",
      message: "Your conversations have been exported",
      timestamp: new Date().toISOString(),
      read: false,
      type: "success"
    };
    setNotifications(prev => [notification, ...prev]);
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
          localStorage.setItem('rane-mainta-conversations', JSON.stringify(data));
          
          // Show success notification
          const notification = {
            id: Date.now(),
            title: "Import successful",
            message: `${data.length} conversations imported`,
            timestamp: new Date().toISOString(),
            read: false,
            type: "success"
          };
          setNotifications(prev => [notification, ...prev]);
        }
      } catch (err) {
        setError('Invalid file format');
        // Show error notification
        const notification = {
          id: Date.now(),
          title: "Import failed",
          message: "The file format is invalid",
          timestamp: new Date().toISOString(),
          read: false,
          type: "error"
        };
        setNotifications(prev => [notification, ...prev]);
      }
    };
    reader.readAsText(file);
    setSelectedFile(file.name);
  };

   if (activeTab !== 'chat' || !showSidebar) return null;   

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <img src={logo} alt="Rane Logo" className="sidebar-logo" />
        <h3>Chat History</h3>
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
        <button 
          onClick={saveConversation} 
          className="action-button"
          disabled={messages.length === 0}
        >
          <FiSave /> Save
        </button>
        <button onClick={clearConversation} className="action-button">
          <FiMessageSquare /> New
        </button>
      </div>
    </div>
  );
};

export default ChatHistory;