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
  const [parsedRules, setParsedRules] = useState([]);
  const [selectedParsedRule, setSelectedParsedRule] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRules();
    loadDatabases();
  }, []);

  useEffect(() => {
    // Auto-select database if only one exists
    if (databases.length === 1 && !form.getFieldValue('db_config_id')) {
      form.setFieldsValue({ db_config_id: databases[0].id });
    }
  }, [databases, form]);

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
    setParsedRules([]);
    setSelectedParsedRule(null);
    form.resetFields();
    
    // Auto-select database if only one exists
    if (databases.length === 1) {
      form.setFieldsValue({ db_config_id: databases[0].id });
    }
    
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingRule(record);
    setParsedRules([]);
    setSelectedParsedRule(null);
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

      // 获取选中的数据库ID
      const dbConfigId = form.getFieldValue('db_config_id');

      setParsing(true);
      const response = await sensitiveRuleService.parseRule(description, dbConfigId);
      const parsedArray = response.data;
      
      setParsedRules(parsedArray);
      
      // If only one rule, auto-select it
      if (parsedArray.length === 1) {
        handleSelectParsedRule(parsedArray[0]);
        showSuccess('规则解析成功');
      } else if (parsedArray.length > 1) {
        showSuccess(`解析成功，识别到 ${parsedArray.length} 条规则`);
      }
    } catch (error) {
      showError('解析失败', error.message);
    } finally {
      setParsing(false);
    }
  };

  const handleSelectParsedRule = (parsed) => {
    setSelectedParsedRule(parsed);
    
    // Auto-fill form with parsed values
    const columnsValue = Array.isArray(parsed.columns) 
      ? parsed.columns.join(', ') 
      : parsed.columns;
    
    // Preserve db_config_id when filling form
    const currentDbConfigId = form.getFieldValue('db_config_id');
    
    form.setFieldsValue({
      name: parsed.name || form.getFieldValue('name'),
      mode: parsed.mode,
      columns: columnsValue,
      pattern: parsed.pattern,
      db_config_id: currentDbConfigId, // Keep the selected database
    });
  };

  const handleBatchCreateParsedRules = async () => {
    try {
      const dbConfigId = form.getFieldValue('db_config_id');
      
      // Create all parsed rules
      for (const rule of parsedRules) {
        const ruleData = {
          db_config_id: dbConfigId,
          name: rule.name,
          mode: rule.mode,
          table_name: rule.table_name,
          columns: rule.columns,
          pattern: rule.pattern,
        };
        await sensitiveRuleService.createRule(ruleData);
      }
      
      showSuccess(`成功创建 ${parsedRules.length} 条规则`);
      setModalVisible(false);
      form.resetFields();
      setParsedRules([]);
      setSelectedParsedRule(null);
      loadRules();
    } catch (error) {
      showError('批量创建失败', error.message);
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
      setParsedRules([]);
      setSelectedParsedRule(null);
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
      title: '表名',
      dataIndex: 'table_name',
      key: 'table_name',
      render: (tableName) => tableName || '-',
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
        title={
          editingRule 
            ? '编辑敏感信息规则' 
            : parsedRules.length > 0 
              ? '确认敏感信息规则' 
              : '添加敏感信息规则'
        }
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setParsedRules([]);
          setSelectedParsedRule(null);
        }}
        okText={selectedParsedRule && !editingRule ? "确认创建" : "保存"}
        cancelText="取消"
        width={700}
        okButtonProps={{
          disabled: !editingRule && parsedRules.length === 0 && !selectedParsedRule
        }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ mode: 'mask' }}
        >
          {!editingRule && parsedRules.length === 0 && (
            <>
              <Form.Item
                name="description"
                label="规则描述（自然语言）"
                extra="描述需要脱敏的数据类型，系统会自动识别相关字段并生成规则。支持一次识别多种类型。"
              >
                <TextArea
                  rows={3}
                  placeholder="例如：手机号和邮箱脱敏"
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
            </>
          )}

          {(editingRule || selectedParsedRule) && (
            <Form.Item
              name="name"
              label="规则名称"
              rules={[{ required: true, message: '请输入规则名称' }]}
            >
              <Input 
                placeholder="例如：过滤身份证号" 
                disabled={!!selectedParsedRule && !editingRule}
              />
            </Form.Item>
          )}

          {parsedRules.length > 0 && (
            <Card 
              title={`解析结果（${parsedRules.length} 条规则）`}
              size="small"
              style={{ marginBottom: 16 }}
              extra={
                parsedRules.length > 1 && (
                  <Button 
                    type="primary" 
                    size="small"
                    onClick={handleBatchCreateParsedRules}
                  >
                    一键创建全部
                  </Button>
                )
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {parsedRules.map((rule, index) => (
                  <Card
                    key={index}
                    size="small"
                    hoverable
                    style={{
                      cursor: 'pointer',
                      border: selectedParsedRule === rule ? '2px solid #1890ff' : '1px solid #d9d9d9',
                    }}
                    onClick={() => handleSelectParsedRule(rule)}
                  >
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <Text strong>{rule.name}</Text>
                        {selectedParsedRule === rule && (
                          <Tag color="blue" style={{ marginLeft: 8 }}>已选择</Tag>
                        )}
                      </div>
                      <Space wrap>
                        <Tag color={rule.mode === 'filter' ? 'red' : 'orange'}>
                          {rule.mode === 'filter' ? '完全过滤' : '脱敏处理'}
                        </Tag>
                        {rule.table_name && (
                          <>
                            <Text type="secondary" style={{ fontSize: '12px' }}>表：</Text>
                            <Tag color="blue" style={{ fontSize: '11px' }}>{rule.table_name}</Tag>
                          </>
                        )}
                        {rule.columns && rule.columns.length > 0 && (
                          <>
                            <Text type="secondary" style={{ fontSize: '12px' }}>列：</Text>
                            {rule.columns.map((col, idx) => (
                              <Tag key={idx} style={{ fontSize: '11px' }}>{col}</Tag>
                            ))}
                          </>
                        )}
                      </Space>
                    </Space>
                  </Card>
                ))}
                {parsedRules.length > 1 && (
                  <Alert
                    message={`识别到 ${parsedRules.length} 条规则`}
                    description="可以点击上方「一键创建全部」按钮批量创建，或点击单个规则卡片查看详情后单独保存"
                    type="info"
                    showIcon
                  />
                )}
                {parsedRules.length === 1 && (
                  <Alert
                    message="已自动选择该规则"
                    description="请确认规则信息后点击「确认创建」按钮"
                    type="success"
                    showIcon
                  />
                )}
              </Space>
            </Card>
          )}

          {(editingRule || selectedParsedRule) && (
            <>
              <Form.Item
                name="db_config_id"
                label="应用到数据库"
                extra={databases.length === 1 ? "已自动选择唯一的数据库" : "选择此规则应用的数据库配置（可选）"}
              >
                <Select
                  placeholder="选择数据库配置"
                  allowClear
                  disabled={databases.length === 1 || (!!selectedParsedRule && !editingRule)}
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
                <Select disabled={!!selectedParsedRule && !editingRule}>
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
                extra={selectedParsedRule && !editingRule ? "由AI自动识别的列名" : "多个列名用逗号分隔，例如：id_card, phone, email"}
              >
                <Input 
                  placeholder="id_card, phone" 
                  disabled={!!selectedParsedRule && !editingRule}
                />
              </Form.Item>

              <Form.Item
                name="pattern"
                label="匹配模式（可选）"
                extra={selectedParsedRule && !editingRule ? "脱敏模式" : "正则表达式，用于匹配特定格式的数据"}
              >
                <Input 
                  placeholder="例如：phone, id_card" 
                  disabled={!!selectedParsedRule && !editingRule}
                />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default SensitiveDataTab;
