import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Input,
  Popconfirm,
  Tag,
  Dropdown,
  Typography,
} from 'antd';
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  DownOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { reportService } from '../services';
import { showSuccess, showError } from '../utils/notification';
import ReportDisplay from '../components/ReportDisplay';

const { TextArea } = Input;
const { Title } = Typography;

const SavedReportsPage = () => {
  const [savedReports, setSavedReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingReport, setEditingReport] = useState(null);
  const [reportName, setReportName] = useState('');
  const [reportDescription, setReportDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [executing, setExecuting] = useState(null);
  const [reportResult, setReportResult] = useState(null);

  useEffect(() => {
    loadSavedReports();
  }, []);

  const loadSavedReports = async () => {
    try {
      setLoading(true);
      const response = await reportService.getSavedReports();
      setSavedReports(response.data || []);
    } catch (error) {
      showError('加载常用报表失败', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteReport = async (reportId, withAnalysis) => {
    try {
      setExecuting(reportId);
      setReportResult(null);
      const response = await reportService.runSavedReport(reportId, withAnalysis);
      setReportResult(response.data);
      showSuccess(
        withAnalysis ? '报表执行成功（含分析）' : '报表执行成功'
      );
    } catch (error) {
      showError('执行报表失败', error.message);
    } finally {
      setExecuting(null);
    }
  };

  const handleEditReport = (report) => {
    setEditingReport(report);
    setReportName(report.name);
    setReportDescription(report.description || '');
    setEditModalVisible(true);
  };

  const handleSaveEdit = async () => {
    if (!reportName.trim()) {
      showError('请输入报表名称');
      return;
    }

    try {
      setSaving(true);
      await reportService.updateSavedReport(editingReport.id, {
        name: reportName.trim(),
        description: reportDescription.trim(),
      });

      showSuccess('报表更新成功');
      setEditModalVisible(false);
      setEditingReport(null);
      setReportName('');
      setReportDescription('');
      loadSavedReports();
    } catch (error) {
      showError('更新报表失败', error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteReport = async (reportId) => {
    try {
      await reportService.deleteSavedReport(reportId);
      showSuccess('报表删除成功');
      loadSavedReports();
      // Clear report result if the deleted report was being displayed
      if (reportResult && reportResult.report_id === reportId) {
        setReportResult(null);
      }
    } catch (error) {
      showError('删除报表失败', error.message);
    }
  };

  const getExecuteMenuItems = (record) => [
    {
      key: 'execute-fast',
      label: '快速执行（无分析）',
      icon: <PlayCircleOutlined />,
      onClick: () => handleExecuteReport(record.id, false),
    },
    {
      key: 'execute-analysis',
      label: '执行并分析',
      icon: <PlayCircleOutlined />,
      onClick: () => handleExecuteReport(record.id, true),
    },
  ];

  const columns = [
    {
      title: '报表名称',
      dataIndex: 'name',
      key: 'name',
      width: '25%',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: '35%',
      render: (text) => text || <span style={{ color: '#999' }}>无描述</span>,
    },
    {
      title: '数据源',
      dataIndex: 'data_source_ids',
      key: 'data_source_ids',
      width: '15%',
      render: (sources) => (
        <Space size={[0, 4]} wrap>
          {sources && sources.length > 0 ? (
            sources.map((source, index) => (
              <Tag key={index} color="blue">
                {source}
              </Tag>
            ))
          ) : (
            <Tag>默认</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (text) => {
        if (!text) return '-';
        const date = new Date(text);
        return date.toLocaleString('zh-CN');
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: '10%',
      render: (_, record) => (
        <Space size="small">
          <Dropdown
            menu={{ items: getExecuteMenuItems(record) }}
            trigger={['click']}
          >
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={executing === record.id}
            >
              执行 <DownOutlined />
            </Button>
          </Dropdown>
          <Button
            icon={<EditOutlined />}
            onClick={() => handleEditReport(record)}
          />
          <Popconfirm
            title="确认删除"
            description="确定要删除这个常用报表吗？"
            onConfirm={() => handleDeleteReport(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '0 24px' }}>
      <Card
        title={
          <Space>
            <Title level={3} style={{ margin: 0 }}>
              常用报表管理
            </Title>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={loadSavedReports}
            loading={loading}
          >
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={savedReports}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          locale={{
            emptyText: '暂无常用报表，请在首页生成报表后保存',
          }}
        />
      </Card>

      {reportResult && (
        <div style={{ marginTop: 24 }}>
          <ReportDisplay reportData={reportResult} />
        </div>
      )}

      <Modal
        title="编辑报表"
        open={editModalVisible}
        onOk={handleSaveEdit}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingReport(null);
          setReportName('');
          setReportDescription('');
        }}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <label style={{ fontWeight: 500 }}>报表名称 *</label>
            <Input
              value={reportName}
              onChange={(e) => setReportName(e.target.value)}
              placeholder="请输入报表名称"
              style={{ marginTop: 8 }}
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>报表描述</label>
            <TextArea
              value={reportDescription}
              onChange={(e) => setReportDescription(e.target.value)}
              placeholder="请输入报表描述（可选）"
              rows={4}
              style={{ marginTop: 8 }}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default SavedReportsPage;
