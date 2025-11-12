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
  Checkbox,
  Upload,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { databaseService } from '../services';
import { showError, showSuccess } from '../utils/notification';

const DatabaseConfigTab = () => {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDatabase, setEditingDatabase] = useState(null);
  const [testingId, setTestingId] = useState(null);
  const [form] = Form.useForm();
  const [useSchemaFile, setUseSchemaFile] = useState(false);
  const [schemaFileContent, setSchemaFileContent] = useState('');

  useEffect(() => {
    loadDatabases();
  }, []);

  const loadDatabases = async () => {
    try {
      setLoading(true);
      const response = await databaseService.getDatabases();
      setDatabases(response.data);
    } catch (error) {
      showError('加载数据库配置失败', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingDatabase(null);
    form.resetFields();
    setUseSchemaFile(false);
    setSchemaFileContent('');
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingDatabase(record);
    form.setFieldsValue({
      name: record.name,
      type: record.type,
      url: record.url,
      username: record.username,
      // Don't populate password for security
    });
    setUseSchemaFile(record.use_schema_file || false);
    setSchemaFileContent(record.schema_description || '');
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await databaseService.deleteDatabase(id);
      showSuccess('删除成功');
      loadDatabases();
    } catch (error) {
      showError('删除失败', error.message);
    }
  };

  const handleTestConnection = async (id) => {
    try {
      setTestingId(id);
      const response = await databaseService.testConnection(id);
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

  const handleFileUpload = (file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      setSchemaFileContent(content);
      showSuccess('文件读取成功');
    };
    reader.onerror = () => {
      showError('文件读取失败', '无法读取文件内容');
    };
    reader.readAsText(file);
    return false; // 阻止自动上传
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // 添加schema文件相关字段
      const submitData = {
        ...values,
        use_schema_file: useSchemaFile,
        schema_description: useSchemaFile ? schemaFileContent : null,
      };
      
      if (editingDatabase) {
        // Update existing database
        await databaseService.updateDatabase(editingDatabase.id, submitData);
        showSuccess('更新成功');
      } else {
        // Create new database
        await databaseService.createDatabase(submitData);
        showSuccess('创建成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      setUseSchemaFile(false);
      setSchemaFileContent('');
      loadDatabases();
    } catch (error) {
      if (error.errorFields) {
        // Form validation error
        return;
      }
      showError(
        editingDatabase ? '更新失败' : '创建失败',
        error.message
      );
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type) => {
        const colorMap = {
          sqlite: 'blue',
          mysql: 'green',
          postgresql: 'purple',
        };
        return <Tag color={colorMap[type] || 'default'}>{type.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'URL',
      dataIndex: 'url',
      key: 'url',
      width: 250,
      ellipsis: true,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      ellipsis: true,
    },
    {
      title: 'Schema',
      dataIndex: 'use_schema_file',
      key: 'use_schema_file',
      width: 120,
      render: (useSchemaFile) => (
        <Tag color={useSchemaFile ? 'green' : 'default'}>
          {useSchemaFile ? '自定义描述' : '自动提取'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right',
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
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个数据库配置吗？"
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
          添加数据库
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={databases}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 1200 }}
      />

      <Modal
        title={editingDatabase ? '编辑数据库配置' : '添加数据库配置'}
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
          initialValues={{ type: 'sqlite' }}
        >
          <Form.Item
            name="name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：生产数据库" />
          </Form.Item>

          <Form.Item
            name="type"
            label="数据库类型"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select>
              <Select.Option value="sqlite">SQLite</Select.Option>
              <Select.Option value="mysql">MySQL</Select.Option>
              <Select.Option value="postgresql">PostgreSQL</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="url"
            label="数据库URL"
            rules={[{ required: true, message: '请输入数据库URL' }]}
            extra="例如：sqlite:///data/test.db 或 mysql://localhost:3306/dbname"
          >
            <Input placeholder="数据库连接URL" />
          </Form.Item>

          <Form.Item
            name="username"
            label="用户名"
          >
            <Input placeholder="数据库用户名（SQLite可选）" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            extra={editingDatabase ? '留空表示不修改密码' : ''}
          >
            <Input.Password placeholder="数据库密码" />
          </Form.Item>

          <Form.Item label="Schema描述文件">
            <Checkbox
              checked={useSchemaFile}
              onChange={(e) => {
                setUseSchemaFile(e.target.checked);
                if (!e.target.checked) {
                  setSchemaFileContent('');
                }
              }}
            >
              使用自定义Schema描述文件
            </Checkbox>
            {useSchemaFile && (
              <div style={{ marginTop: 8 }}>
                <Upload
                  accept=".md,.txt"
                  beforeUpload={handleFileUpload}
                  maxCount={1}
                  showUploadList={false}
                >
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                </Upload>
                {schemaFileContent && (
                  <div style={{ marginTop: 8 }}>
                    <Input.TextArea
                      value={schemaFileContent}
                      onChange={(e) => setSchemaFileContent(e.target.value)}
                      rows={6}
                      placeholder="Schema描述内容"
                    />
                    <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                      已加载 {schemaFileContent.length} 个字符
                    </div>
                  </div>
                )}
              </div>
            )}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DatabaseConfigTab;
