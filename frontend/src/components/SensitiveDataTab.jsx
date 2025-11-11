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
  Card,
  Typography,
  Spin,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { sensitiveRuleService, databaseService } from '../services';
import { showError, showSuccess } from '../utils/notification';

const { TextArea } = Input;
const { Text } = Typography;

const SensitiveDataTab = () => {
  const [rules, setRules] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [parsedRule, setParsedRule] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRules();
    loadDatabases();
  }, []);

  const loadRules = async () => {
    try {
      setLoading(true);
      const response = await sensitiveRuleService.getRules();
      setRules(response.data);
    } catch (error) {
      showError('加载敏感信息规则失败', error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDatabases = async () => {
    try {
      const response = await databaseService.getDatabases();
      setDatabases(response.data);
    } catch (error) {
      console.error('加载数据库列表失败', error);
    }
  };

  const handleCreate = () => {
    setEditingRule(null);
    setParsedRule(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingRule(record);
    setParsedRule(null);
    form.setFieldsValue({
      name: record.name,
      description: record.description,
      db_config_id: record.db_config_id,
      mode: record.mode,
      columns: record.columns.join(', '),
      pattern: record.pattern,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await sensitiveRuleService.deleteRule(id);
      showSuccess('删除成功');
      loadRules();
    } catch (error) {
      showError('删除失败', error.message);
    }
  };

  const handleParseNaturalLanguage = async () => {
    try {
      const description = form.getFieldValue('description');
      if (!description) {
        showError('解析失败', '请先输入规则描述');
        return;
      }

      setParsing(true);
      const response = await sensitiveRuleService.parseRule(description);
      const parsed = response.data;
      
      setParsedRule(parsed);
      
      // Auto-fill form with parsed values
      const columnsValue = Array.isArray(parsed.columns) 
        ? parsed.columns.join(', ') 
        : parsed.columns;
      
      form.setFieldsValue({
        name: parsed.name || form.getFieldValue('name'),
        mode: parsed.mode,
        columns: columnsValue,
        pattern: parsed.pattern,
      });
      
      // Show different message based on whether columns were detected
      if (!columnsValue || columnsValue.trim() === '') {
        showSuccess('规则解析成功，请手动选择应用列');
      } else {
        showSuccess('规则解析成功');
      }
    } catch (error) {
      showError('解析失败', error.message);
    } finally {
      setParsing(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // Convert columns string to array
      const columnsArray = values.columns
        .split(',')
        .map(col => col.trim())
        .filter(col => col.length > 0);
      
      const ruleData = {
        ...values,
        columns: columnsArray,
      };
      
      if (editingRule) {
        // Update existing rule
        await sensitiveRuleService.updateRule(editingRule.id, ruleData);
        showSuccess('更新成功');
      } else {
        // Create new rule
        await sensitiveRuleService.createRule(ruleData);
        showSuccess('创建成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      setParsedRule(null);
      loadRules();
    } catch (error) {
      if (error.errorFields) {
        // Form validation error
        return;
      }
      showError(
        editingRule ? '更新失败' : '创建失败',
        error.message
      );
    }
  };

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '处理模式',
      dataIndex: 'mode',
      key: 'mode',
      render: (mode) => {
        const config = {
          filter: { color: 'red', text: '完全过滤' },
          mask: { color: 'orange', text: '脱敏处理' },
        };
        const { color, text } = config[mode] || { color: 'default', text: mode };
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '应用列',
      dataIndex: 'columns',
      key: 'columns',
      render: (columns) => (
        <Space wrap>
          {columns.map((col, idx) => (
            <Tag key={idx}>{col}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个规则吗？"
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
          添加敏感信息规则
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={rules}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editingRule ? '编辑敏感信息规则' : '添加敏感信息规则'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setParsedRule(null);
        }}
        okText="保存"
        cancelText="取消"
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ mode: 'mask' }}
        >
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: '请输入规则名称' }]}
          >
            <Input placeholder="例如：过滤身份证号" />
          </Form.Item>

          <Form.Item
            name="description"
            label="规则描述（自然语言）"
            extra="使用自然语言描述规则，然后点击下方按钮自动解析"
          >
            <TextArea
              rows={3}
              placeholder="例如：对所有包含身份证号和手机号的列进行脱敏处理"
            />
          </Form.Item>

          <Form.Item>
            <Button
              icon={<ThunderboltOutlined />}
              onClick={handleParseNaturalLanguage}
              loading={parsing}
              block
            >
              智能解析规则
            </Button>
          </Form.Item>

          {parsedRule && (
            <Alert
              message="解析成功"
              description={
                !parsedRule.columns || parsedRule.columns.length === 0
                  ? "已自动填充部分字段。由于描述较为通用，无法自动推断列名，请手动输入需要应用的列名。"
                  : "已自动填充下方字段，请检查并确认"
              }
              type={
                !parsedRule.columns || parsedRule.columns.length === 0
                  ? "warning"
                  : "success"
              }
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Form.Item
            name="db_config_id"
            label="应用到数据库"
            extra="选择此规则应用的数据库配置（可选）"
          >
            <Select
              placeholder="选择数据库配置"
              allowClear
            >
              {databases.map(db => (
                <Select.Option key={db.id} value={db.id}>
                  {db.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="mode"
            label="处理模式"
            rules={[{ required: true, message: '请选择处理模式' }]}
          >
            <Select>
              <Select.Option value="filter">
                完全过滤（移除列）
              </Select.Option>
              <Select.Option value="mask">
                脱敏处理（使用***替换）
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="columns"
            label="应用列"
            rules={[{ required: true, message: '请输入列名' }]}
            extra="多个列名用逗号分隔，例如：id_card, phone, email"
          >
            <Input placeholder="id_card, phone" />
          </Form.Item>

          <Form.Item
            name="pattern"
            label="匹配模式（可选）"
            extra="正则表达式，用于匹配特定格式的数据"
          >
            <Input placeholder="例如：^\d{18}$ 匹配18位数字" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SensitiveDataTab;
