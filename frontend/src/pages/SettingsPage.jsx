import { Tabs } from 'antd';
import {
  DatabaseOutlined,
  ApiOutlined,
  SafetyOutlined,
} from '@ant-design/icons';
import DatabaseConfigTab from '../components/DatabaseConfigTab';
import MCPServerConfigTab from '../components/MCPServerConfigTab';
import SensitiveDataTab from '../components/SensitiveDataTab';

const SettingsPage = () => {
  const items = [
    {
      key: 'database',
      label: (
        <span>
          <DatabaseOutlined />
          数据库配置
        </span>
      ),
      children: <DatabaseConfigTab />,
    },
    {
      key: 'mcp',
      label: (
        <span>
          <ApiOutlined />
          MCP Server配置
        </span>
      ),
      children: <MCPServerConfigTab />,
    },
    {
      key: 'sensitive',
      label: (
        <span>
          <SafetyOutlined />
          敏感信息规则
        </span>
      ),
      children: <SensitiveDataTab />,
    },
  ];

  return (
    <div style={{ padding: '0 24px' }}>
      <h1 style={{ marginBottom: 24 }}>系统设置</h1>
      <Tabs
        defaultActiveKey="database"
        items={items}
        size="large"
      />
    </div>
  );
};

export default SettingsPage;
