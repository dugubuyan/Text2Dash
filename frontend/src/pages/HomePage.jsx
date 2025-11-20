import { useState, useEffect } from 'react';
import { Row, Col, Typography, Button } from 'antd';

import { QueryInput, ReportDisplay, ChatMessages } from '../components';
import { reportService, sessionService } from '../services';
import { showError, showSuccess } from '../utils/notification';

const HomePage = () => {
  const [sessionId, setSessionId] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);

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
    // 添加用户消息到对话
    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: queryData.query,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      setLoading(true);
      
      console.log('发送报表生成请求:', queryData);
      const response = await reportService.generateReport(queryData);
      console.log('收到报表响应:', response);
      console.log('响应数据详情:', {
        hasData: !!response.data,
        dataKeys: response.data ? Object.keys(response.data) : [],
        dataArray: response.data?.data,
        dataLength: response.data?.data?.length,
        chartConfig: response.data?.chart_config,
        summary: response.data?.summary
      });
      
      if (response.data) {
        // 修复：检查是否有数据或图表配置
        const hasData = response.data.data && response.data.data.length > 0;
        const hasChartConfig = response.data.chart_config !== null && response.data.chart_config !== undefined;
        
        // 检查是否是纯文本类型（clarify_and_guide 或 direct_conversation）
        const isTextOnly = response.data.chart_config?.type === 'text';
        
        // 只有当有数据或有非文本类型的图表配置时，才认为有报表
        const hasReport = (hasData || hasChartConfig) && !isTextOnly;
        
        console.log('报表检查结果:', { hasData, hasChartConfig, isTextOnly, hasReport });
        
        // 添加AI回复到对话
        const assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          summary: response.data.summary || '已完成分析',
          has_report: hasReport,
          created_at: new Date().toISOString(),
          reportData: hasReport ? response.data : null
        };
        setMessages(prev => [...prev, assistantMessage]);
        
        // 如果有报表数据，设置当前报表
        if (hasReport) {
          console.log('设置报表数据:', response.data);
          setReportData(response.data);
          showSuccess('报表生成成功');
        } else {
          console.log('没有报表数据，仅显示文本回复');
          // 如果之前有报表，清除它
          setReportData(null);
          showSuccess('查询完成');
        }
      } else {
        console.error('响应中没有数据');
        showError('报表生成失败：响应数据为空');
      }
    } catch (error) {
      console.error('报表生成错误:', error);
      const errorMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        summary: '抱歉，处理您的请求时出现了错误：' + (error.response?.data?.detail || error.message),
        has_report: false,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      showError('生成报表失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = (message) => {
    if (message.reportData) {
      setReportData(message.reportData);
      showSuccess('已加载报表');
    }
  };

  const handleNewChat = async () => {
    try {
      // 创建新会话
      const response = await sessionService.createSession('default_user');
      setSessionId(response.data.id);
      
      // 清空所有状态
      setReportData(null);
      setMessages([]);
      
      showSuccess('已开启新对话');
    } catch (error) {
      showError('创建新对话失败', error.message);
    }
  };



  // 准备对话消息（添加查看报表的回调）
  const chatMessages = messages.map(msg => ({
    ...msg,
    onViewReport: msg.has_report ? () => handleViewReport(msg) : null
  }));

  // 布局：未开始会话时显示欢迎词和输入框
  if (messages.length === 0) {
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

  // 布局：有报表时显示左右分栏，无报表时全屏显示对话
  return (
    <Row gutter={[0, 0]} style={{ height: 'calc(100vh - 64px)' }}>
      {/* 左侧：报表显示区域（仅在有报表时显示） */}
      {reportData && (
        <Col xs={24} lg={14} style={{ 
          height: '100%', 
          overflowY: 'auto',
          padding: '24px',
          backgroundColor: '#fff',
          position: 'relative'
        }}>
          <ReportDisplay reportData={reportData} />
        </Col>
      )}

      {/* 右侧：对话区域 + 输入框 */}
      <Col xs={24} lg={reportData ? 10 : 24} className="no-print" style={{ 
        height: '100%',
        borderLeft: reportData ? '1px solid #f0f0f0' : 'none',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#fff'
      }}>
        {/* 顶部工具栏 */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#fafafa'
        }}>
          <Typography.Text strong style={{ fontSize: 16 }}>
            对话
          </Typography.Text>
          <Button
            type="primary"
            size="small"
            onClick={handleNewChat}
          >
            新对话
          </Button>
        </div>

        {/* 对话消息区域 */}
        <div style={{ 
          flex: 1, 
          overflowY: 'auto',
          backgroundColor: '#fff'
        }}>
          <ChatMessages messages={chatMessages} />
        </div>

        {/* 输入框区域 */}
        <div style={{ 
          borderTop: '1px solid #e8e8e8',
          padding: '20px',
          backgroundColor: '#fafafa'
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
