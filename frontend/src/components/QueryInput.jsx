import { useState, useEffect } from 'react';
import { Input, Button, Select, Space, Card, Spin, Dropdown, Badge } from 'antd';
import { SendOutlined, DatabaseOutlined } from '@ant-design/icons';
import { modelService, databaseService, mcpService } from '../services';
import { showError } from '../utils/notification';

const { TextArea } = Input;

const QueryInput = ({ onSubmit, loading = false, sessionId, compact = false }) => {
  const [query, setQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini/gemini-2.0-flash');
  const [selectedDataSources, setSelectedDataSources] = useState([]);
  const [models, setModels] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [mcpServers, setMcpServers] = useState([]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoadingData(true);
      const [modelsRes, databasesRes, mcpServersRes] = await Promise.all([
        modelService.getModels(),
        databaseService.getDatabases(),
        mcpService.getMCPServers(),
      ]);

      const loadedDatabases = databasesRes.data || [];
      const loadedMcpServers = mcpServersRes.data || [];
      
      setModels(modelsRes.data || []);
      setDatabases(loadedDatabases);
      setMcpServers(loadedMcpServers);
      
      // 如果只有一个数据源，自动选中它
      const allDataSources = [...loadedDatabases, ...loadedMcpServers];
      if (allDataSources.length === 1) {
        setSelectedDataSources([allDataSources[0].id]);
      }
    } catch (error) {
      showError('加载配置失败', error.message);
    } finally {
      setLoadingData(false);
    }
  };

  const handleSubmit = () => {
    if (!query.trim()) {
      showError('请输入查询内容');
      return;
    }

    if (selectedDataSources.length === 0) {
      showError('请至少选择一个数据源');
      return;
    }

    onSubmit({
      query: query.trim(),
      model: selectedModel,
      data_source_ids: selectedDataSources,
      session_id: sessionId,
    });
    
    // 发送成功后清空输入框
    setQuery('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  // Combine databases and MCP servers into data source options
  const dataSourceOptions = [
    {
      label: '数据库',
      options: databases.map((db) => ({
        label: db.name,
        value: db.id,
      })),
    },
    {
      label: 'MCP Server',
      options: mcpServers.map((mcp) => ({
        label: mcp.name,
        value: mcp.id,
      })),
    },
  ];

  if (loadingData) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>加载配置中...</p>
        </div>
      </Card>
    );
  }

  // 紧凑模式（用于右侧边栏）
  if (compact) {
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <TextArea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入查询内容..."
          rows={3}
          disabled={loading}
          style={{ resize: 'none' }}
        />
        
        <Space style={{ width: '100%' }} size="small">
          <Select
            value={selectedModel}
            onChange={setSelectedModel}
            style={{ flex: 1, minWidth: 120 }}
            disabled={loading}
            size="small"
            options={models.map((model) => ({
              label: model.name,
              value: model.id,
            }))}
          />
          <Select
            mode="multiple"
            value={selectedDataSources}
            onChange={setSelectedDataSources}
            style={{ flex: 2, minWidth: 150 }}
            placeholder="数据源"
            disabled={loading}
            size="small"
            maxTagCount={1}
            options={dataSourceOptions}
          />
        </Space>

        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSubmit}
          loading={loading}
          block
        >
          {loading ? '生成中...' : '发送'}
        </Button>
      </Space>
    );
  }

  // 构建数据源下拉菜单项
  const dataSourceMenuItems = [
    {
      key: 'databases',
      type: 'group',
      label: '数据库',
      children: databases.map((db) => ({
        key: db.id,
        label: (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>{db.name}</span>
            {selectedDataSources.includes(db.id) && (
              <span style={{ color: '#1890ff', marginLeft: 8 }}>✓</span>
            )}
          </div>
        ),
      })),
    },
    {
      key: 'mcp',
      type: 'group',
      label: 'MCP Server',
      children: mcpServers.map((mcp) => ({
        key: mcp.id,
        label: (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>{mcp.name}</span>
            {selectedDataSources.includes(mcp.id) && (
              <span style={{ color: '#1890ff', marginLeft: 8 }}>✓</span>
            )}
          </div>
        ),
      })),
    },
  ];

  // 处理数据源选择
  const handleDataSourceClick = ({ key }) => {
    if (selectedDataSources.includes(key)) {
      // 取消选择
      setSelectedDataSources(selectedDataSources.filter(id => id !== key));
    } else {
      // 添加选择
      setSelectedDataSources([...selectedDataSources, key]);
    }
  };

  // 获取已选择数据源的名称
  const getSelectedDataSourceNames = () => {
    const allSources = [...databases, ...mcpServers];
    return selectedDataSources
      .map(id => {
        const source = allSources.find(s => s.id === id);
        return source ? source.name : null;
      })
      .filter(Boolean);
  };

  // 完整模式（用于欢迎页中央）
  return (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: 16,
      boxShadow: '0 2px 16px rgba(0, 0, 0, 0.06)',
      padding: '20px 24px',
      border: '1px solid #e8e8e8',
      transition: 'all 0.3s ease'
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.boxShadow = '0 4px 24px rgba(0, 0, 0, 0.1)';
      e.currentTarget.style.borderColor = '#d9d9d9';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.boxShadow = '0 2px 16px rgba(0, 0, 0, 0.06)';
      e.currentTarget.style.borderColor = '#e8e8e8';
    }}
    >
      <TextArea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="请用自然语言描述您的数据需求，例如：显示2023年所有学生的平均成绩"
        rows={4}
        disabled={loading}
        autoSize={{ minRows: 4, maxRows: 8 }}
        style={{ 
          fontSize: 15,
          border: 'none',
          boxShadow: 'none',
          resize: 'none',
          padding: 0,
          outline: 'none'
        }}
        className="custom-textarea"
      />

      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid #f0f0f0'
      }}>
        <Space size="middle">
          <Select
            value={selectedModel}
            onChange={setSelectedModel}
            style={{ minWidth: 180 }}
            disabled={loading}
            bordered={false}
            suffixIcon={<span style={{ color: '#8c8c8c', fontSize: 12 }}>▼</span>}
            options={models.map((model) => ({
              label: model.name,
              value: model.id,
            }))}
          />
          
          <Dropdown
            menu={{
              items: dataSourceMenuItems,
              onClick: handleDataSourceClick,
            }}
            trigger={['click']}
            disabled={loading}
          >
            <Button
              style={{
                border: 'none',
                boxShadow: 'none',
                padding: '4px 12px',
                height: 'auto',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                color: selectedDataSources.length > 0 ? '#262626' : '#8c8c8c',
                fontWeight: selectedDataSources.length > 0 ? 500 : 400
              }}
            >
              <DatabaseOutlined />
              <span>
                {selectedDataSources.length > 0 
                  ? `数据源 (${selectedDataSources.length})`
                  : '选择数据源'
                }
              </span>
              <span style={{ color: '#8c8c8c', fontSize: 12 }}>▼</span>
            </Button>
          </Dropdown>
        </Space>

        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSubmit}
          loading={loading}
          size="large"
          style={{
            borderRadius: 8,
            height: 40,
            paddingLeft: 24,
            paddingRight: 24,
            fontWeight: 500
          }}
        >
          {loading ? '生成中...' : '发送'}
        </Button>
      </div>
    </div>
  );
};

export default QueryInput;
