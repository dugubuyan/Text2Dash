import { useEffect, useRef } from 'react';
import { Typography } from 'antd';
import { formatRelativeTime } from '../utils/dateFormatter';

const { Text } = Typography;

const ChatMessages = ({ messages = [] }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: '#bfbfbf',
        fontSize: 14,
        padding: '0 40px',
        textAlign: 'center'
      }}>
        开始对话，提出你的数据分析需求
      </div>
    );
  }

  return (
    <div style={{ 
      height: '100%',
      overflowY: 'auto',
      padding: '24px 0'
    }}>
      {messages.map((message) => (
        <div
          key={message.id}
          style={{
            marginBottom: 32,
            padding: '0 24px'
          }}
        >
          {/* 用户消息 */}
          {message.role === 'user' && (
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {formatRelativeTime(message.created_at)}
                </Text>
              </div>
              <div style={{
                fontSize: 15,
                lineHeight: 1.7,
                color: '#262626',
                wordBreak: 'break-word'
              }}>
                {message.content}
              </div>
            </div>
          )}

          {/* AI 回复 */}
          {message.role === 'assistant' && (
            <div>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center',
                gap: 8,
                marginBottom: 8
              }}>
                <div style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: '#52c41a'
                }} />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {formatRelativeTime(message.created_at)}
                </Text>
              </div>
              
              <div style={{
                fontSize: 15,
                lineHeight: 1.7,
                color: '#595959',
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap'
              }}>
                {message.summary}
              </div>
              
              {message.has_report && (
                <div
                  onClick={() => message.onViewReport && message.onViewReport()}
                  style={{
                    marginTop: 12,
                    padding: '10px 14px',
                    backgroundColor: '#f0f9ff',
                    border: '1px solid #bae7ff',
                    borderRadius: 6,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#e6f7ff';
                    e.currentTarget.style.borderColor = '#91d5ff';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#f0f9ff';
                    e.currentTarget.style.borderColor = '#bae7ff';
                  }}
                >
                  <span style={{ fontSize: 16 }}>📊</span>
                  <Text style={{ fontSize: 13, color: '#1890ff' }}>
                    查看报表
                  </Text>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;
