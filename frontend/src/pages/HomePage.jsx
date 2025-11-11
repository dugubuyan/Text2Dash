import { useState, useEffect } from 'react';
import { Row, Col, Typography, Space } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import { QueryInput, ReportDisplay, SessionHistory } from '../components';
import { reportService, sessionService } from '../services';
import { showError, showSuccess } from '../utils/notification';

const { Title } = Typography;

const HomePage = () => {
  const [sessionId, setSessionId] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  useEffect(() => {
    initializeSession();
  }, []);

  const initializeSession = async () => {
    try {
      const response = await sessionService.createSession('default_user');
      setSessionId(response.data.id);
    } catch (error) {
      showError('创建会话失败', error.message);
    }
  };

  const handleQuerySubmit = async (queryData) => {
    try {
      setLoading(true);
      setHasStarted(true); // 标记会话已开始
      
      console.log('发送报表生成请求:', queryData);
      const response = await reportService.generateReport(queryData);
      console.log('收到报表响应:', response);
      console.log('报表数据:', response.data);
      console.log('报表数据 JSON:', JSON.stringify(response.data, null, 2));
      
      if (response.data) {
        setReportData(response.data);
        console.log('已设置 reportData 状态');
        showSuccess('报表生成成功');
        
        // 延迟刷新历史记录，等待后端异步保存完成
        setTimeout(() => {
          if (window.refreshSessionHistory) {
            window.refreshSessionHistory();
          }
        }, 1000);
      } else {
        console.error('响应中没有数据');
        showError('报表生成失败：响应数据为空');
      }
    } catch (error) {
      console.error('报表生成错误:', error);
      showError('生成报表失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = async (historyItem) => {
    try {
      setHasStarted(true);
      
      // 检查是否有数据快照
      const hasData = historyItem.data_snapshot && historyItem.data_snapshot.length > 0;
      
      // Reconstruct report data from history item
      setReportData({
        query_plan: historyItem.query_plan || {},
        chart_config: historyItem.chart_config,
        summary: historyItem.summary,
        original_query: historyItem.user_query,
        data_source_ids: historyItem.data_source_ids || [],
        data: hasData ? historyItem.data_snapshot : [],
        metadata: hasData ? {
          columns: Object.keys(historyItem.data_snapshot[0] || {}),
          row_count: historyItem.data_snapshot.length
        } : { columns: [], row_count: 0 },
      });
      
      if (hasData) {
        showSuccess('已加载历史报表');
      } else {
        showSuccess('已加载历史摘要（无完整数据）');
      }
    } catch (error) {
      showError('加载历史报表失败', error.message);
    }
  };

  const handleNewChat = async () => {
    try {
      // 创建新会话
      const response = await sessionService.createSession('default_user');
      setSessionId(response.data.id);
      
      // 清空当前报表数据
      setReportData(null);
      
      // 重置为欢迎页状态
      setHasStarted(false);
      
      showSuccess('已开启新对话');
    } catch (error) {
      showError('创建新对话失败', error.message);
    }
  };

  // 布局：未开始会话时显示欢迎词和输入框
  if (!hasStarted) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'flex-start',
        minHeight: 'calc(100vh - 64px)',
        padding: '0 20px 120px',
        backgroundColor: '#fafafa'
      }}>
        <div style={{ 
          textAlign: 'center', 
          marginTop: '15vh',
          marginBottom: 32,
          maxWidth: 700
        }}>
          <Typography.Paragraph 
            style={{ 
              fontSize: 18, 
              color: '#8c8c8c',
              marginBottom: 0,
              lineHeight: 1.6
            }}
          >
            用自然语言提问，AI 为您提供数据智能分析与可视化洞察
          </Typography.Paragraph>
        </div>
        
        <div style={{ 
          width: '100%', 
          maxWidth: 800,
          transform: 'translateX(-20px)'
        }}>
          <QueryInput
            onSubmit={handleQuerySubmit}
            loading={loading}
            sessionId={sessionId}
          />
        </div>
      </div>
    );
  }

  // 布局：会话开始后，中间显示结果，右侧显示历史和输入框
  return (
    <Row gutter={[0, 0]} style={{ height: 'calc(100vh - 64px)' }}>
      {/* 左侧：报表显示区域 */}
      <Col xs={24} lg={16} style={{ 
        height: '100%', 
        overflowY: 'auto',
        padding: '24px',
        backgroundColor: '#fff'
      }}>
        {reportData ? (
          <ReportDisplay reportData={reportData} />
        ) : (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            height: '100%',
            color: '#999'
          }}>
            <Space direction="vertical" align="center" size="large">
              <BarChartOutlined style={{ fontSize: 64 }} />
              <Title level={4} type="secondary">等待生成报表...</Title>
            </Space>
          </div>
        )}
      </Col>

      {/* 右侧：历史记录 + 输入框 */}
      <Col xs={24} lg={8} style={{ 
        height: '100%',
        borderLeft: '1px solid #f0f0f0',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#f5f5f5'
      }}>
        {/* 历史记录区域 */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto',
          padding: '24px',
          backgroundColor: '#f5f5f5'
        }}>
          <SessionHistory
            sessionId={sessionId}
            onSelectHistory={handleSelectHistory}
            onNewChat={handleNewChat}
          />
        </div>

        {/* 输入框区域 */}
        <div style={{ 
          borderTop: '1px solid #e8e8e8',
          padding: '20px',
          backgroundColor: '#f5f5f5'
        }}>
          <QueryInput
            onSubmit={handleQuerySubmit}
            loading={loading}
            sessionId={sessionId}
            compact={true}
          />
        </div>
      </Col>
    </Row>
  );
};

export default HomePage;
