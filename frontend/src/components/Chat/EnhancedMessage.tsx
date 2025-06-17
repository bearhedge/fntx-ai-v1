import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '../../types/trading';
import { WaitingPeriodTimer } from '../Trading/WaitingPeriodTimer';

// Custom pandas-like table style as a string to inject with HTML tables
const tableStyle = `
  <style>
    .pandas-table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
      background: #fff;
    }
    .pandas-table th, .pandas-table td {
      border: 1px solid #d3d3d3;
      padding: 6px 12px;
      text-align: center;
    }
    .pandas-table th {
      background: #f6f6f6;
      font-weight: bold;
    }
    .pandas-table tr:nth-child(even) {
      background: #f9f9f9;
    }
    .pandas-table tr:hover {
      background: #e6f2ff;
    }
  </style>
`;

interface EnhancedMessageProps {
  message: Message;
}

export const EnhancedMessage = ({ message }: EnhancedMessageProps) => {
  const isAI = message.sender === 'ai';
  const isSystem = message.sender === 'system';

  // Always prefer message.table if available, fallback to content
  // This ensures backend HTML tables are rendered even if they're not in content
  let content = message.table || message.content;
  if (Array.isArray(content) && typeof content[0] === 'string') {
    content = content[0];
  }

  // Render HTML table with style if present, else render as Markdown for AI or plain text for user
  const renderContent = () => {
    if (typeof content === 'string' && content.trim().startsWith('<table')) {
      let styledTable = content;
      if (!content.includes('pandas-table')) {
        styledTable = content.replace('<table', '<table class="pandas-table"');
        styledTable = tableStyle + styledTable;
      }
      return (
        <div
          className="text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: styledTable }}
        />
      );
    }
    
    // Render AI messages as Markdown, user messages as plain text
    if (isAI || isSystem) {
      return (
        <div className="text-sm leading-relaxed prose prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      );
    }
    
    return <div className="text-sm whitespace-pre-line">{content}</div>;
  };

  const renderTimestamp = () => {
    if (typeof message.timestamp === 'string') {
      return new Date(message.timestamp).toLocaleTimeString();
    }
    return message.timestamp.toLocaleTimeString();
  };

  return (
    <div className={`flex ${isAI || isSystem ? 'justify-start' : 'justify-end'}`}>
      <div
        className={`max-w-[80%] rounded-lg p-4 ${
          isSystem
            ? 'bg-gray-50 text-gray-600 w-full text-sm'
            : isAI
            ? 'bg-gray-50 text-gray-800'
            : 'bg-gray-800 text-white'
        }`}
      >
        {renderContent()}

        {message.type === 'waiting-period' && message.waitingPeriod && (
          <div className="mt-3">
            <WaitingPeriodTimer
              totalMinutes={message.waitingPeriod.totalMinutes}
              remainingMinutes={message.waitingPeriod.remainingMinutes}
              reason={message.waitingPeriod.reason}
            />
          </div>
        )}

        <div className="text-xs text-gray-400 mt-2">
          {renderTimestamp()}
        </div>
      </div>
    </div>
  );
};