import { useEffect, useRef, useState } from 'react';
import { Card, Button, Space, Modal, Input, Typography, Table, Dropdown } from 'antd';
import {
  SaveOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  PrinterOutlined,
  DownloadOutlined,
  EditOutlined,
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

    // Handle radar chart indicator
    if (config.radar && reportData.data && reportData.data.length > 0) {
      const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
      const numericColumns = columns.filter(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue === 'number';
      });
      
      // 如果radar.indicator是占位符或未定义，自动生成
      if (!config.radar.indicator || 
          (typeof config.radar.indicator === 'string' && 
           config.radar.indicator.includes('DATA_PLACEHOLDER'))) {
        
        // 计算每列的统计信息
        const columnStats = numericColumns.map(col => {
          // 过滤掉null、undefined和NaN值
          const values = reportData.data
            .map(row => row[col])
            .filter(val => val !== null && val !== undefined && !isNaN(val));
          
          if (values.length === 0) {
            return { col, minValue: 0, maxValue: 100, range: 100 };
          }
          
          const minValue = Math.min(...values);
          const maxValue = Math.max(...values);
          return { col, minValue, maxValue, range: maxValue - minValue };
        });
        
        // 检查是否需要归一化（不同列的数值范围差异很大）
        const ranges = columnStats.map(s => s.range);
        const maxRange = Math.max(...ranges);
        const minRange = Math.min(...ranges.filter(r => r > 0));
        const needsNormalization = maxRange / minRange > 10; // 差异超过10倍
        
        console.log(`MultiChartItem: 雷达图列统计:`, columnStats, `需要归一化: ${needsNormalization}`);
        
        if (needsNormalization) {
          // 归一化处理：将所有维度映射到0-100范围
          config.radar.indicator = columnStats.map(stat => ({
            name: `${stat.col}\n(${stat.minValue.toFixed(1)}-${stat.maxValue.toFixed(1)})`,
            max: 100
          }));
          
          // 更新series数据，进行归一化
          config.series = config.series.map(series => {
            if (series.type === 'radar' && Array.isArray(series.data)) {
              series.data = series.data.map(item => {
                const normalizedValue = item.value.map((val, idx) => {
                  // 处理null值
                  if (val === null || val === undefined || isNaN(val)) {
                    return 0; // null值显示为0
                  }
                  const stat = columnStats[idx];
                  if (stat.range === 0) return 50; // 避免除以0
                  return ((val - stat.minValue) / stat.range) * 100;
                });
                return {
                  ...item,
                  value: normalizedValue,
                  originalValue: item.value  // 保留原始值用于tooltip
                };
              });
            }
            return series;
          });
          
          console.log(`MultiChartItem: 雷达图数据已归一化`);
        } else {
          // 不需要归一化，使用原始max值
          config.radar.indicator = columnStats.map(stat => ({
            name: stat.col,
            max: stat.maxValue * 1.2  // 留20%余量
          }));
        }
      }
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
    if (!reportData.data || reportData.data.length === 0) {
      console.warn('MultiChartItem: 数据为空');
      return [];
    }
    
    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
    console.log(`MultiChartItem: 提取数据 - 图表类型=${series.type}, 列=${columns}`);
    
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
    
    // For scatter charts
    if (series.type === 'scatter') {
      if (columns.length >= 2) {
        // 找出所有数值列
        const numericColumns = columns.filter(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue === 'number';
        });
        
        // 找出第一个非数值列作为name（如专业名称）
        const nameColumn = columns.find(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue !== 'number';
        });
        
        console.log(`MultiChartItem: 散点图 - 所有列=${columns}, 数值列=${numericColumns}, name列=${nameColumn}`);
        
        // 如果有至少2个数值列，使用它们
        if (numericColumns.length >= 2) {
          const xCol = numericColumns[0];
          const yCol = numericColumns[1];
          const scatterData = reportData.data.map(row => {
            const dataPoint = {
              value: [row[xCol], row[yCol]],
              // 如果有name列，添加name属性
              ...(nameColumn ? { name: row[nameColumn] } : {}),
              // 保留所有原始数据用于tooltip
              ...row
            };
            return dataPoint;
          });
          console.log(`MultiChartItem: 散点图数据 - 列[${xCol}, ${yCol}], name=${nameColumn}`, scatterData);
          return scatterData;
        }
        
        // 否则使用前两列
        const scatterData = reportData.data.map(row => {
          const dataPoint = {
            value: [row[columns[0]], row[columns[1]]],
            ...(nameColumn ? { name: row[nameColumn] } : {}),
            ...row
          };
          return dataPoint;
        });
        console.log(`MultiChartItem: 散点图数据（默认） - 列[${columns[0]}, ${columns[1]}], name=${nameColumn}`, scatterData);
        return scatterData;
      }
    }
    
    // For radar charts
    if (series.type === 'radar') {
      // 找出所有数值列
      const numericColumns = columns.filter(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue === 'number';
      });
      
      // 找出第一个非数值列作为name
      const nameColumn = columns.find(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue !== 'number';
      });
      
      console.log(`MultiChartItem: 雷达图 - 所有列=${columns}, 数值列=${numericColumns}, name列=${nameColumn}`);
      
      // 雷达图数据：每行是一个数据项，包含多个维度的值
      const radarData = reportData.data.map((row, rowIdx) => {
        const values = numericColumns.map(col => {
          const val = row[col];
          console.log(`MultiChartItem: 雷达图提取 - 行${rowIdx}, 列${col}, 值=${val}, 类型=${typeof val}`);
          return val;
        });
        return {
          value: values,
          name: nameColumn ? row[nameColumn] : '',
          ...row  // 保留所有原始数据
        };
      });
      
      console.log(`MultiChartItem: 雷达图数据`, radarData);
      return radarData;
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
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState('');

  useEffect(() => {
    console.log('ReportDisplay 收到数据:', reportData);
    console.log('ReportDisplay 数据详情:', {
      hasReportData: !!reportData,
      hasChartConfig: !!reportData?.chart_config,
      chartConfigType: reportData?.chart_config ? typeof reportData.chart_config : 'undefined',
      hasData: !!reportData?.data,
      dataLength: reportData?.data?.length,
      summary: reportData?.summary
    });
    
    if (reportData && reportData.chart_config) {
      console.log('开始渲染图表, chart_config:', reportData.chart_config);
      
      // 检查是否是多图表类型
      if (reportData.chart_config?.charts && Array.isArray(reportData.chart_config.charts)) {
        console.log('检测到多图表类型，图表数量:', reportData.chart_config.charts.length);
        // 多图表类型，不在这里渲染，由 JSX 中的多个 div 处理
      } else if (chartRef.current) {
        // 单图表类型
        console.log('渲染单图表');
        renderChart();
      } else {
        console.log('chartRef.current 不存在');
      }
    } else {
      console.log('无法渲染图表:', {
        hasReportData: !!reportData,
        hasChartConfig: !!reportData?.chart_config,
        chartConfig: reportData?.chart_config
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

    // Enhance tooltip to show all data fields for bar/line/scatter charts
    if (chartConfig.tooltip && reportData.metadata?.columns) {
      const columns = reportData.metadata.columns;
      const chartType = chartConfig.series && chartConfig.series[0]?.type;
      
      if (chartType === 'bar' || chartType === 'line') {
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
      } else if (chartType === 'scatter') {
        chartConfig.tooltip.formatter = function (params) {
          if (Array.isArray(params)) {
            params = params[0];
          }

          // 显示name（如专业名称）
          let result = params.data.name ? `<strong>${params.data.name}</strong><br/>` : '';

          // 显示所有列的数据
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

    // Handle radar chart indicator
    if (chartConfig.radar && reportData.data && reportData.data.length > 0) {
      const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
      const numericColumns = columns.filter(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue === 'number';
      });
      
      // 如果radar.indicator是占位符或未定义，自动生成
      if (!chartConfig.radar.indicator || 
          (typeof chartConfig.radar.indicator === 'string' && 
           chartConfig.radar.indicator.includes('DATA_PLACEHOLDER'))) {
        
        // 计算每列的统计信息
        const columnStats = numericColumns.map(col => {
          // 过滤掉null、undefined和NaN值
          const values = reportData.data
            .map(row => row[col])
            .filter(val => val !== null && val !== undefined && !isNaN(val));
          
          if (values.length === 0) {
            return { col, minValue: 0, maxValue: 100, range: 100 };
          }
          
          const minValue = Math.min(...values);
          const maxValue = Math.max(...values);
          return { col, minValue, maxValue, range: maxValue - minValue };
        });
        
        // 检查是否需要归一化（不同列的数值范围差异很大）
        const ranges = columnStats.map(s => s.range);
        const maxRange = Math.max(...ranges);
        const minRange = Math.min(...ranges.filter(r => r > 0));
        const needsNormalization = maxRange / minRange > 10; // 差异超过10倍
        
        console.log(`ReportDisplay: 雷达图列统计:`, columnStats, `需要归一化: ${needsNormalization}`);
        
        if (needsNormalization) {
          // 归一化处理：将所有维度映射到0-100范围
          chartConfig.radar.indicator = columnStats.map(stat => ({
            name: `${stat.col}\n(${stat.minValue.toFixed(1)}-${stat.maxValue.toFixed(1)})`,
            max: 100
          }));
          
          // 更新series数据，进行归一化
          chartConfig.series = chartConfig.series.map(series => {
            if (series.type === 'radar' && Array.isArray(series.data)) {
              series.data = series.data.map(item => {
                const normalizedValue = item.value.map((val, idx) => {
                  // 处理null值
                  if (val === null || val === undefined || isNaN(val)) {
                    return 0; // null值显示为0
                  }
                  const stat = columnStats[idx];
                  if (stat.range === 0) return 50; // 避免除以0
                  return ((val - stat.minValue) / stat.range) * 100;
                });
                return {
                  ...item,
                  value: normalizedValue,
                  originalValue: item.value  // 保留原始值用于tooltip
                };
              });
            }
            return series;
          });
          
          console.log(`ReportDisplay: 雷达图数据已归一化`);
        } else {
          // 不需要归一化，使用原始max值
          chartConfig.radar.indicator = columnStats.map(stat => ({
            name: stat.col,
            max: stat.maxValue * 1.2  // 留20%余量
          }));
        }
      }
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
      console.warn('ReportDisplay: 数据为空');
      return [];
    }

    const columns = reportData.metadata?.columns || Object.keys(reportData.data[0]);
    console.log(`ReportDisplay: 提取数据 - 图表类型=${series.type}, 列=${columns}`);

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
        // 找出所有数值列
        const numericColumns = columns.filter(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue === 'number';
        });
        
        // 找出第一个非数值列作为name（如专业名称）
        const nameColumn = columns.find(col => {
          const firstValue = reportData.data[0][col];
          return typeof firstValue !== 'number';
        });
        
        console.log(`ReportDisplay: 散点图 - 所有列=${columns}, 数值列=${numericColumns}, name列=${nameColumn}`);
        
        // 如果有至少2个数值列，使用它们
        if (numericColumns.length >= 2) {
          const xCol = numericColumns[0];
          const yCol = numericColumns[1];
          const scatterData = reportData.data.map(row => {
            const dataPoint = {
              value: [row[xCol], row[yCol]],
              // 如果有name列，添加name属性
              ...(nameColumn ? { name: row[nameColumn] } : {}),
              // 保留所有原始数据用于tooltip
              ...row
            };
            return dataPoint;
          });
          console.log(`ReportDisplay: 散点图数据 - 列[${xCol}, ${yCol}], name=${nameColumn}`, scatterData);
          return scatterData;
        }
        
        // 否则使用前两列
        const scatterData = reportData.data.map(row => {
          const dataPoint = {
            value: [row[columns[0]], row[columns[1]]],
            ...(nameColumn ? { name: row[nameColumn] } : {}),
            ...row
          };
          return dataPoint;
        });
        console.log(`ReportDisplay: 散点图数据（默认） - 列[${columns[0]}, ${columns[1]}], name=${nameColumn}`, scatterData);
        return scatterData;
      }
    }

    // For radar charts
    if (series.type === 'radar') {
      // 找出所有数值列
      const numericColumns = columns.filter(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue === 'number';
      });
      
      // 找出第一个非数值列作为name
      const nameColumn = columns.find(col => {
        const firstValue = reportData.data[0][col];
        return typeof firstValue !== 'number';
      });
      
      console.log(`ReportDisplay: 雷达图 - 所有列=${columns}, 数值列=${numericColumns}, name列=${nameColumn}`);
      
      // 雷达图数据：每行是一个数据项，包含多个维度的值
      const radarData = reportData.data.map((row, rowIdx) => {
        const values = numericColumns.map(col => {
          const val = row[col];
          console.log(`ReportDisplay: 雷达图提取 - 行${rowIdx}, 列${col}, 值=${val}, 类型=${typeof val}`);
          return val;
        });
        return {
          value: values,
          name: nameColumn ? row[nameColumn] : '',
          ...row  // 保留所有原始数据
        };
      });
      
      console.log(`ReportDisplay: 雷达图数据`, radarData);
      return radarData;
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
      // 显示后端返回的错误信息
      showError('保存报表失败', error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExportPDF = async () => {
    try {
      setExporting(true);
      
      // 优先使用图表配置中的标题，其次使用报告总结
      let title = '数据报表';
      
      // 尝试从chart_config中获取标题
      if (reportData.chart_config?.title?.text) {
        title = reportData.chart_config.title.text;
      } else if (reportData.chart_config?.charts?.[0]?.title) {
        // 多图表情况，使用第一个图表的标题
        title = reportData.chart_config.charts[0].title;
      } else if (reportData.summary) {
        // 如果没有图表标题，使用报告总结
        title = reportData.summary.length > 50 
          ? reportData.summary.substring(0, 50) + '...' 
          : reportData.summary;
      }
      
      // 确保标题不会太长
      if (title.length > 50) {
        title = title.substring(0, 50) + '...';
      }
      
      // 将图表转换为图片
      let chartImage = null;
      if (chartRef.current) {
        try {
          const chartInstance = chartRef.current.getEchartsInstance();
          // 获取图表的base64图片数据
          const imageDataUrl = chartInstance.getDataURL({
            type: 'png',
            pixelRatio: 2, // 提高清晰度
            backgroundColor: '#fff'
          });
          // 将base64转换为blob
          const base64Data = imageDataUrl.split(',')[1];
          chartImage = base64Data;
        } catch (error) {
          console.warn('图表转换失败:', error);
        }
      }
      
      const response = await exportService.exportToPDF({
        title: title,
        summary: editedSummary || reportData.summary || '',
        chart_config: reportData.chart_config,
        chart_image: chartImage,
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
        summary: editedSummary || reportData.summary || '',
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
    // 使用浏览器打印功能，CSS媒体查询会自动隐藏不需要的元素
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
              onClick={() => {
                // 设置默认值
                // 报表名称：使用 chart_config.title.text
                const defaultName = reportData.chart_config?.title?.text || reportData.original_query || '未命名报表';
                setReportName(defaultName);
                
                // 报表描述：使用 summary
                const defaultDescription = reportData.summary || '';
                setReportDescription(defaultDescription);
                
                setSaveModalVisible(true);
              }}
            >
              保存为常用报表
            </Button>
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'pdf',
                    label: '导出PDF',
                    icon: <FilePdfOutlined />,
                    onClick: handleExportPDF,
                  },
                  {
                    key: 'excel',
                    label: '导出Excel',
                    icon: <FileExcelOutlined />,
                    onClick: handleExportExcel,
                  },
                ],
              }}
            >
              <Button icon={<DownloadOutlined />} loading={exporting}>
                导出
              </Button>
            </Dropdown>
            <Button
              icon={<PrinterOutlined />}
              onClick={handlePrint}
              className="no-print"
            >
              打印
            </Button>
            <Button
              icon={<EditOutlined />}
              onClick={() => {
                setIsEditing(!isEditing);
                if (!isEditing) {
                  setEditedSummary(reportData.summary || '');
                }
              }}
              type={isEditing ? 'primary' : 'default'}
              className="no-print"
            >
              {isEditing ? '完成编辑' : '编辑'}
            </Button>
          </Space>
        }
      >
        {reportData.summary && (
          <div style={{ marginBottom: 24 }} className="report-summary">
            <Title level={4}>报告总结</Title>
            {isEditing ? (
              <TextArea
                value={editedSummary}
                onChange={(e) => setEditedSummary(e.target.value)}
                rows={4}
                style={{ fontSize: 16, lineHeight: 1.8 }}
                placeholder="请输入报告总结"
              />
            ) : (
              <Paragraph style={{ fontSize: 16, lineHeight: 1.8 }}>
                {editedSummary || reportData.summary}
              </Paragraph>
            )}
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
          <div style={{ marginTop: 24 }} className="report-metadata no-print">
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
