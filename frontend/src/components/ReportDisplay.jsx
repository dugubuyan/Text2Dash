import { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Modal, Input, Typography, Table } from 'antd';
import {
  SaveOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  PrinterOutlined,
} from '@ant-design/icons';
import * as echarts from 'echarts';
import { reportService, exportService } from '../services';
import { showSuccess, showError } from '../utils/notification';

const { TextArea } = Input;
const { Title, Paragraph } = Typography;

// 多图表中的单个图表组件
const MultiChartItem = ({ chartConfig, reportData, index }) => {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  useEffect(() => {
    if (chartRef.current && chartConfig) {
      renderSingleChart();
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose();
        chartInstanceRef.current = null;
      }
    };
  }, [chartConfig, reportData]);

  const renderSingleChart = () => {
    // Dispose existing chart instance
    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose();
    }

    // Clone chart config
    const config = JSON.parse(JSON.stringify(chartConfig));

    // Replace data placeholders with actual data
    if (config.series && reportData.data) {
      config.series = config.series.map(series => {
        if (typeof series.data === 'string' && series.data.includes('DATA_PLACEHOLDER')) {
          const actualData = extractDataForSeries(series, config, reportData);
          return { ...series, data: actualData };
        }
        return { ...series, data: Array.isArray(series.data) ? series.data : [] };
      });
    }

    // Replace xAxis data placeholder
    if (config.xAxis && typeof config.xAxis.data === 'string' && 
        config.xAxis.data.includes('DATA_PLACEHOLDER')) {
      config.xAxis.data = extractXAxisData(reportData);
    }

    console.log(`渲染图表 ${index}:`, config);

    // Initialize chart
    chartInstanceRef.current = echarts.init(chartRef.current);
    chartInstanceRef.current.setOption(config);

    // Handle resize
    const handleResize = () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.resize();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  };

  const extractXAxisData = (reportData) => {
    if (!reportData.data || reportData.data.length === 0) return [];
    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
    const firstColumn = columns[0];
    return reportData.data.map(row => row[firstColumn]);
  };

  const extractDataForSeries = (series, chartConfig, reportData) => {
    if (!reportData.data || reportData.data.length === 0) return [];
    
    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
    
    // For bar/line charts
    if (series.type === 'bar' || series.type === 'line') {
      let valueColumn = null;
      if (columns.length === 2) {
        valueColumn = columns[1];
      } else {
        const numericColumns = columns.filter(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue === 'number';
        });
        if (numericColumns.length > 0) {
          valueColumn = numericColumns[0];
        }
      }
      
      if (valueColumn) {
        return reportData.data.map(row => ({
          value: row[valueColumn],
          ...row
        }));
      }
    }
    
    // For pie charts
    if (series.type === 'pie') {
      if (columns.length >= 2) {
        return reportData.data.map(row => ({
          name: row[columns[0]],
          value: row[columns[1]]
        }));
      }
    }
    
    // Default
    if (columns.length >= 2) {
      return reportData.data.map(row => row[columns[1]]);
    }
    
    return [];
  };

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: 400 }}
      className="report-chart"
    />
  );
};

const ReportDisplay = ({ reportData, onSave }) => {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [reportName, setReportName] = useState('');
  const [reportDescription, setReportDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    console.log('ReportDisplay 收到数据:', reportData);
    if (reportData && reportData.chart_config) {
      console.log('开始渲染图表');
      
      // 检查是否是多图表类型
      if (reportData.chart_config?.charts && Array.isArray(reportData.chart_config.charts)) {
        console.log('检测到多图表类型，图表数量:', reportData.chart_config.charts.length);
        // 多图表类型，不在这里渲染，由 JSX 中的多个 div 处理
      } else if (chartRef.current) {
        // 单图表类型
        renderChart();
      }
    } else {
      console.log('无法渲染图表:', {
        hasReportData: !!reportData,
        hasChartConfig: !!reportData?.chart_config
      });
    }

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose();
        chartInstanceRef.current = null;
      }
    };
  }, [reportData]);

  const renderChart = () => {
    // Dispose existing chart instance
    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose();
    }

    // Validate chart config
    if (!reportData.chart_config) {
      console.error('Chart config is missing');
      return;
    }

    // Clone chart config
    const chartConfig = JSON.parse(JSON.stringify(reportData.chart_config));

    // Replace data placeholders with actual data
    if (chartConfig.series && reportData.data) {
      chartConfig.series = chartConfig.series.map(series => {
        // Check if data is a placeholder string
        if (typeof series.data === 'string' && series.data.includes('DATA_PLACEHOLDER')) {
          // Extract data from reportData based on chart type
          const actualData = extractDataForSeries(series, chartConfig);
          return {
            ...series,
            data: actualData
          };
        }
        // If data is already an array, keep it
        return {
          ...series,
          data: Array.isArray(series.data) ? series.data : []
        };
      });
    }

    // Enhance tooltip to show all data fields for bar/line charts
    if (chartConfig.tooltip && reportData.metadata?.columns) {
      const columns = reportData.metadata.columns;
      if (chartConfig.series && chartConfig.series[0]?.type === 'bar' || chartConfig.series[0]?.type === 'line') {
        chartConfig.tooltip.formatter = function (params) {
          if (Array.isArray(params)) {
            params = params[0];
          }

          let result = `<strong>${params.name}</strong><br/>`;

          // Show all columns from the data
          columns.forEach(col => {
            if (params.data && params.data[col] !== undefined) {
              const value = params.data[col];
              // Format numbers to 2 decimal places
              const displayValue = typeof value === 'number' ? value.toFixed(2) : value;
              result += `${col}: ${displayValue}<br/>`;
            }
          });

          return result;
        };
      }
    }

    // Replace xAxis data placeholder if exists
    if (chartConfig.xAxis && typeof chartConfig.xAxis.data === 'string' &&
      chartConfig.xAxis.data.includes('DATA_PLACEHOLDER')) {
      chartConfig.xAxis.data = extractXAxisData();
    }

    console.log('渲染图表配置:', chartConfig);

    // Initialize new chart
    chartInstanceRef.current = echarts.init(chartRef.current);
    chartInstanceRef.current.setOption(chartConfig);

    // Handle window resize
    const handleResize = () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.resize();
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  };

  const extractXAxisData = () => {
    // Extract x-axis data (usually the first column or a category column)
    if (!reportData.data || reportData.data.length === 0) {
      return [];
    }

    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
    const firstColumn = columns[0];

    return reportData.data.map(row => row[firstColumn]);
  };

  const extractDataForSeries = (series, chartConfig) => {
    // Extract data for a series based on chart type and data structure
    if (!reportData.data || reportData.data.length === 0) {
      return [];
    }

    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);

    // For bar/line charts: return objects with value and all other data
    if (series.type === 'bar' || series.type === 'line') {
      // Find the main numeric column for the value
      let valueColumn = null;

      if (columns.length === 2) {
        valueColumn = columns[1];
      } else {
        // Try to find numeric columns
        const numericColumns = columns.filter(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue === 'number';
        });
        if (numericColumns.length > 0) {
          valueColumn = numericColumns[0];
        }
      }

      if (valueColumn) {
        // Return data as objects with value and all original data
        return reportData.data.map(row => ({
          value: row[valueColumn],
          ...row  // Include all columns for tooltip
        }));
      }
    }

    // For pie charts: extract name-value pairs
    if (series.type === 'pie') {
      if (columns.length >= 2) {
        const nameColumn = columns[0];
        const valueColumn = columns[1];
        return reportData.data.map(row => ({
          name: row[nameColumn],
          value: row[valueColumn]
        }));
      }
    }

    // For scatter charts: extract x-y pairs
    if (series.type === 'scatter') {
      if (columns.length >= 2) {
        return reportData.data.map(row => [row[columns[0]], row[columns[1]]]);
      }
    }

    // Default: return the second column values
    if (columns.length >= 2) {
      return reportData.data.map(row => row[columns[1]]);
    }

    return [];
  };

  const handleSaveReport = async () => {
    if (!reportName.trim()) {
      showError('请输入报表名称');
      return;
    }

    try {
      setSaving(true);
      await reportService.saveReport({
        name: reportName.trim(),
        description: reportDescription.trim(),
        query_plan: reportData.query_plan || {},
        chart_config: reportData.chart_config || null,
        summary: reportData.summary || '',
        original_query: reportData.original_query || '',
        data_source_ids: reportData.data_source_ids || [],
      });

      showSuccess('报表保存成功');
      setSaveModalVisible(false);
      setReportName('');
      setReportDescription('');

      if (onSave) {
        onSave();
      }
    } catch (error) {
      showError('保存报表失败', error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      setExporting(true);
      const response = await exportService.exportToPDF({
        title: reportData.original_query || '报表',
        summary: reportData.summary || '',
        chart_config: reportData.chart_config,
        data: reportData.data,
        metadata: reportData.metadata,
        sql_query: reportData.sql_query || null,
      });

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `report_${Date.now()}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showSuccess('PDF导出成功');
    } catch (error) {
      console.error('PDF导出错误:', error);
      showError('导出PDF失败', error.response?.data?.detail || error.message);
    } finally {
      setExporting(false);
    }
  };

  const handleExportExcel = async () => {
    try {
      setExporting(true);
      const response = await exportService.exportToExcel({
        title: reportData.original_query || '报表',
        summary: reportData.summary || '',
        chart_config: reportData.chart_config,
        data: reportData.data,
        metadata: reportData.metadata,
        sql_query: reportData.sql_query || null,
      });

      // Create download link
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `report_${Date.now()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      showSuccess('Excel导出成功');
    } catch (error) {
      console.error('Excel导出错误:', error);
      showError('导出Excel失败', error.response?.data?.detail || error.message);
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (!reportData) {
    return null;
  }

  return (
    <>
      <Card
        title="报表结果"
        className="report-display"
        extra={
          <Space>
            <Button
              icon={<SaveOutlined />}
              onClick={() => setSaveModalVisible(true)}
            >
              保存为常用报表
            </Button>
            <Button
              icon={<FilePdfOutlined />}
              onClick={handleExportPDF}
              loading={exporting}
            >
              导出PDF
            </Button>
            <Button
              icon={<FileExcelOutlined />}
              onClick={handleExportExcel}
              loading={exporting}
            >
              导出Excel
            </Button>
            <Button
              icon={<PrinterOutlined />}
              onClick={handlePrint}
              className="no-print"
            >
              打印
            </Button>
          </Space>
        }
      >
        {reportData.summary && (
          <div style={{ marginBottom: 24 }} className="report-summary">
            <Title level={4}>报告总结</Title>
            <Paragraph style={{ fontSize: 16, lineHeight: 1.8 }}>
              {reportData.summary}
            </Paragraph>
          </div>
        )}

        {/* 判断是单图表还是多图表 */}
        {reportData.chart_config?.charts && Array.isArray(reportData.chart_config.charts) ? (
          // 多图表显示
          <div className="multiple-charts">
            {reportData.chart_config.charts.map((chartItem, index) => (
              <div key={index} style={{ marginBottom: index < reportData.chart_config.charts.length - 1 ? 32 : 0 }}>
                {chartItem.title && (
                  <Title level={5} style={{ marginBottom: 16 }}>{chartItem.title}</Title>
                )}
                <MultiChartItem
                  chartConfig={chartItem.config}
                  reportData={reportData}
                  index={index}
                />
              </div>
            ))}
          </div>
        ) : reportData.chart_config ? (
          // 单图表显示
          <div
            ref={chartRef}
            style={{ width: '100%', height: 500 }}
            className="report-chart"
          />
        ) : null}

        {reportData.data && reportData.data.length > 0 && (
          <div style={{ marginTop: 32 }} className="report-data-table">
            <Title level={4}>数据详情</Title>
            <Table
              dataSource={reportData.data.map((row, index) => ({ ...row, key: index }))}
              columns={
                reportData.metadata?.columns.map(col => ({
                  title: col,
                  dataIndex: col,
                  key: col,
                  sorter: (a, b) => {
                    const aVal = a[col];
                    const bVal = b[col];
                    if (typeof aVal === 'number' && typeof bVal === 'number') {
                      return aVal - bVal;
                    }
                    return String(aVal).localeCompare(String(bVal));
                  },
                })) || Object.keys(reportData.data[0]).map(col => ({
                  title: col,
                  dataIndex: col,
                  key: col,
                }))
              }
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条数据`,
              }}
              scroll={{ x: 'max-content' }}
              size="middle"
            />
          </div>
        )}

        {reportData.metadata && (
          <div style={{ marginTop: 24 }} className="report-metadata">
            <Title level={5}>数据信息</Title>
            <Paragraph>
              <strong>数据行数：</strong> {reportData.metadata.row_count}
            </Paragraph>
            <Paragraph>
              <strong>数据列：</strong> {reportData.metadata.columns.join(', ')}
            </Paragraph>
            {reportData.model && (
              <Paragraph>
                <strong>使用模型：</strong> {reportData.model}
              </Paragraph>
            )}
          </div>
        )}
      </Card>

      <Modal
        title="保存为常用报表"
        open={saveModalVisible}
        onOk={handleSaveReport}
        onCancel={() => setSaveModalVisible(false)}
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
              rows={3}
              style={{ marginTop: 8 }}
            />
          </div>
        </Space>
      </Modal>


    </>
  );
};

export default ReportDisplay;
