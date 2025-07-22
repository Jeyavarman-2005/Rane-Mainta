import React from 'react';
import { 
  FiSend, FiMessageSquare, FiUser, FiX, FiMenu 
} from 'react-icons/fi';
import { 
  BsLightningFill, BsRobot, BsCheckCircleFill 
} from 'react-icons/bs';
import { RiFileExcel2Line } from 'react-icons/ri';
import { 
  MdOutlineAttachFile, MdOutlineAnalytics
} from 'react-icons/md';
import { BiSolidUserCircle } from 'react-icons/bi';
import logo from '../rane-logo.png';
import botAvatar from '../bot-avatar.png';
import './Chatbot.css';

const Chatbot = ({
  messages,
  loading,
  input,
  setInput,
  handleSubmit,
  inputRef,
  exampleQuestions,
  suggestQuestion,
  formatText,
  renderSources,
  messagesEndRef
}) => {
  const FormattedText = ({ text }) => {
    const formatted = formatText(text);
    return <div dangerouslySetInnerHTML={{ __html: formatted }} />;
  };

  return (
    <>
      {/* Chat Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <div className="welcome-content">
              <img src={botAvatar} alt="Rane Mainta" className="welcome-avatar" />
              <h3>Hi, I'm Rane Mainta</h3>
              <p>How can I help you today? I can assist with machine maintenance data, breakdown analysis, and provide insights from your industrial equipment records.</p>
              
              <div className="quick-questions">
                <h4>Try asking me something like:</h4>
                {exampleQuestions.map((q, i) => (
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
                  <BiSolidUserCircle className="sender-icon" />
                ) : message.sender === 'error' ? (
                  <span className="error-icon">⚠️</span>
                ) : message.avatar ? (
                  <img src={message.avatar} alt="Bot Avatar" />
                ) : (
                  <BsRobot className="sender-icon" />
                )}
              </div>
              <div className="message-content">
                <div className="message-text">
                  <FormattedText text={message.text} />
                </div>
                {message.sender === 'bot' && message.processingTime && (
                  <div className="processing-time">
                    Generated in {message.processingTime}
                    {message.breakdownType && (
                      <span className="breakdown-hint">
                        (Mainly {message.breakdownType} issues)
                      </span>
                    )}
                  </div>
                )}
                {message.sender === 'bot' && renderSources(message.sources)}
                <div className="message-time">
                  {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message bot">
            <div className="message-sender">
              <img src={logo} alt="Bot Loading" />
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
      
      {/* Chat Input */}
      <form onSubmit={handleSubmit} className="chat-input-area">
        <div className="chat-input-wrapper">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Rane Mainta about machine data..."
            disabled={loading}
            className="chat-input"
          />
        </div>
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
    </>
  );
};

export default Chatbot;