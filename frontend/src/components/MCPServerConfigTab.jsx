import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Popconfirm,
  Tag,
  Collapse,
  Typography,
  Spin,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { mcpService } from '../services';
import { showError, showSuccess } from '../utils/notification';

const { Panel } = Collapse;
const { Text, Paragraph } = Typography;

const MCPServerConfigTab = () => {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [toolsModalVisible, setToolsModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [selectedServerTools, setSelectedServerTools] = useState([]);
  const [loadingTools, setLoadingTools] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const response = await mcpService.getMCPServers();
      setServers(response.data);
    } catch (error) {
      showError('加载MCP Server配置失败', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingServer(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingServer(record);
    form.setFieldsValue({
      name: record.name,
      url: record.url,
      auth_type: record.auth_type || 'none',
      // Don't populate auth_token for security
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await mcpService.deleteMCPServer(id);
      showSuccess('删除成功');
      loadServers();
    } catch (error) {
      showError('删除失败', error.message);
    }
  };

  const handleTestConnection = async (id) => {
    try {
      setTestingId(id);
      const response = await mcpService.testConnection(id);
      if (response.data.success) {
        showSuccess('连接测试成功');
      } else {
        showError('连接测试失败', response.data.message || '未知错误');
      }
    } catch (error) {
      showError('连接测试失败', error.message);
    } finally {
      setTestingId(null);
    }
  };

  const handleViewTools = async (record) => {
    try {
      setLoadingTools(true);
      setToolsModalVisible(true);
      const response = await mcpService.getTools(record.id);
      setSelectedServerTools(response.data.tools || []);
    } catch (error) {
      showError('获取工具列表失败', error.message);
      setToolsModalVisible(false);
    } finally {
      setLoadingTools(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingServer) {
        // Update existing server
        await mcpService.updateMCPServer(editingServer.id, values);
        showSuccess('更新成功');
      } else {
        // Create new server
        await mcpService.createMCPServer(values);
        showSuccess('创建成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      loadServers();
    } catch (error) {
      if (error.errorFields) {
        // Form validation error
        return;
      }
      showError(
        editingServer ? '更新失败' : '创建失败',
        error.message
      );
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      ellipsis: true,
    },
    {
      title: '认证类型',
      dataIndex: 'auth_type',
      key: 'auth_type',
      render: (authType) => {
        const colorMap = {
          none: 'default',
          bearer: 'blue',
          api_key: 'green',
        };
        const labelMap = {
          none: '无',
          bearer: 'Bearer Token',
          api_key: 'API Key',
        };
        return (
          <Tag color={colorMap[authType] || 'default'}>
            {labelMap[authType] || authType}
          </Tag>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<CheckCircleOutlined />}
            loading={testingId === record.id}
            onClick={() => handleTestConnection(record.id)}
          >
            测试连接
          </Button>
          <Button
            type="link"
            icon={<ApiOutlined />}
            onClick={() => handleViewTools(record)}
          >
            查看工具
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个MCP Server配置吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          添加MCP Server
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={servers}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editingServer ? '编辑MCP Server配置' : '添加MCP Server配置'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ auth_type: 'none' }}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：外部API服务" />
          </Form.Item>

          <Form.Item
            name="url"
            label="Server URL"
            rules={[{ required: true, message: '请输入Server URL' }]}
            extra="MCP Server的连接地址"
          >
            <Input placeholder="http://localhost:8080" />
          </Form.Item>

          <Form.Item
            name="auth_type"
            label="认证类型"
            rules={[{ required: true, message: '请选择认证类型' }]}
          >
            <Select>
              <Select.Option value="none">无认证</Select.Option>
              <Select.Option value="bearer">Bearer Token</Select.Option>
              <Select.Option value="api_key">API Key</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.auth_type !== currentValues.auth_type
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('auth_type') !== 'none' ? (
                <Form.Item
                  name="auth_token"
                  label="认证令牌"
                  extra={editingServer ? '留空表示不修改令牌' : ''}
                >
                  <Input.Password placeholder="输入认证令牌" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="可用工具列表"
        open={toolsModalVisible}
        onCancel={() => setToolsModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setToolsModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={700}
      >
        {loadingTools ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
          </div>
        ) : selectedServerTools.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text type="secondary">暂无可用工具</Text>
          </div>
        ) : (
          <Collapse accordion>
            {selectedServerTools.map((tool, index) => (
              <Panel
                header={
                  <Space>
                    <ApiOutlined />
                    <Text strong>{tool.name}</Text>
                  </Space>
                }
                key={index}
              >
                <Paragraph>
                  <Text strong>描述：</Text>
                  <br />
                  {tool.description || '无描述'}
                </Paragraph>
                {tool.parameters && Object.keys(tool.parameters).length > 0 && (
                  <Paragraph>
                    <Text strong>参数：</Text>
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: '8px',
                        borderRadius: '4px',
                        marginTop: '8px',
                      }}
                    >
                      {JSON.stringify(tool.parameters, null, 2)}
                    </pre>
                  </Paragraph>
                )}
              </Panel>
            ))}
          </Collapse>
        )}
      </Modal>
    </div>
  );
};

export default MCPServerConfigTab;
