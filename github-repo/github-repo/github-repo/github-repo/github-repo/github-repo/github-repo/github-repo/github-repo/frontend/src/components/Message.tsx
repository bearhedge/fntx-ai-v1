
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Bot, User } from 'lucide-react';

interface MessageProps {
  message: {
    id: string;
    content: string | string[];
    table?: string; // allow HTML table from backend
    sender: 'user' | 'ai';
    timestamp: Date | string;
  };
}

const Message = ({ message }: MessageProps) => {
  const isUser = message.sender === 'user';

  // Debug log for development
  console.log('Message content:', message.content, typeof message.content, Array.isArray(message.content));

  // Format the timestamp
  const formatTime = (date: Date) => {
    // If date is a string, convert to Date object
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Always prefer message.table if available, fallback to content
  let content = message.table || message.content;
  if (Array.isArray(content) && typeof content[0] === 'string') {
    content = content[0];
  }

  // Render content appropriately based on type
  let renderedContent;
  if (typeof content === 'string' && content.trim().startsWith('<table')) {
    // If content starts with <table, it's an HTML table, so we use dangerouslySetInnerHTML to render it
    renderedContent = <div dangerouslySetInnerHTML={{ __html: content }} />;
  } else if (!isUser) {
    // AI messages: render as Markdown with styling
    renderedContent = (
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  } else {
    // User messages: render as plain text
    renderedContent = <div>{content}</div>;
  }

  return (
    <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
        isUser ? 'bg-gray-600' : 'bg-gray-300'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-gray-600" />
        )}
      </div>

      {/* Message Bubble */}
      <div className={`max-w-xs lg:max-w-md xl:max-w-lg ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-lg px-4 py-3 shadow-sm border transition-all duration-200 hover:shadow-md ${
          isUser 
            ? 'bg-gray-600 text-white border-gray-600' 
            : 'bg-white text-gray-800 border-gray-200'
        }`}>
          {renderedContent}
        </div>
        {/* Timestamp */}
        <p className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  );
};

export default Message;
