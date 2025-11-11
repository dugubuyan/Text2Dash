import { useState, useEffect } from 'react';
import { Card, List, Typography, Empty, Spin, Tag, Button } from 'antd';
import { ClockCircleOutlined, FileTextOutlined, PlusOutlined } from '@ant-design/icons';
import { sessionService } from '../services';
import { showError } from '../utils/notification';
import { formatRelativeTime } from '../utils/dateFormatter';

const { Text, Paragraph } = Typography;

const SessionHistory = ({ sessionId, onSelectHistory, onNewChat }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    if (sessionId) {
      loadHistory();
    }
  }, [sessionId]);

  // 暴露刷新方法给父组件
  useEffect(() => {
    window.refreshSessionHistory = loadHistory;
    return () => {
      window.refreshSessionHistory = null;
    };
  }, [sessionId]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const response = await sessionService.getSessionHistory(sessionId);
      setHistory(response.data?.interactions || []);
    } catch (error) {
      showError('加载历史记录失败', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = (item) => {
    setSelectedId(item.id);
    if (onSelectHistory) {
      onSelectHistory(item);
    }
  };



  if (!sessionId) {
    return (
      <Card title="会话历史">
        <Empty description="请先创建会话" />
      </Card>
    );
  }

  return (
    <div style={{ minHeight: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: 16,
        padding: '0 4px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Text strong style={{ fontSize: 16 }}>历史记录</Text>
          <Tag color="blue" style={{ margin: 0 }}>
            {history.length}
          </Tag>
        </div>
        {onNewChat && (
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={onNewChat}
            style={{
              borderRadius: 6,
              fontSize: 12,
              height: 28,
              padding: '0 12px'
            }}
          >
            新对话
          </Button>
        )}
      </div>
      
      <div style={{ flex: 1, minHeight: 0 }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin />
          </div>
        ) : history.length === 0 ? (
          <div style={{
            backgroundColor: '#fff',
            borderRadius: 8,
            padding: '60px 20px',
            border: '1px solid #e8e8e8',
            minHeight: '200px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Empty 
              description="暂无历史记录" 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          </div>
        ) : (
          <List
            dataSource={history}
            split={false}
            renderItem={(item) => (
              <List.Item
                key={item.id}
                onClick={() => handleSelectHistory(item)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: selectedId === item.id ? '#e6f7ff' : '#fff',
                  padding: '12px 16px',
                  margin: '0 0 8px 0',
                  borderRadius: 8,
                  transition: 'all 0.2s',
                  border: selectedId === item.id ? '1px solid #91d5ff' : '1px solid #e8e8e8',
                  boxShadow: selectedId === item.id ? '0 2px 8px rgba(24, 144, 255, 0.15)' : 'none'
                }}
                onMouseEnter={(e) => {
                  if (selectedId !== item.id) {
                    e.currentTarget.style.backgroundColor = '#fff';
                    e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.08)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (selectedId !== item.id) {
                    e.currentTarget.style.backgroundColor = '#fff';
                    e.currentTarget.style.boxShadow = 'none';
                  }
                }}
              >
                <div style={{ width: '100%' }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    marginBottom: 4
                  }}>
                    <Text 
                      strong 
                      ellipsis 
                      style={{ 
                        flex: 1,
                        fontSize: 14,
                        marginRight: 8
                      }}
                    >
                      {item.user_query}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
                      {formatRelativeTime(item.created_at)}
                    </Text>
                  </div>
                  {item.summary && (
                    <Paragraph
                      ellipsis={{ rows: 2 }}
                      type="secondary"
                      style={{ 
                        marginBottom: 0,
                        fontSize: 12,
                        lineHeight: 1.4
                      }}
                    >
                      {item.summary}
                    </Paragraph>
                  )}
                </div>
              </List.Item>
            )}
          />
        )}
      </div>
    </div>
  );
};

export default SessionHistory;
