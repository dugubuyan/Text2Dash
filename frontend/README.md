# 商业报表生成器 - 前端应用

基于 React + Vite 的现代化数据分析前端应用，提供直观的用户界面和丰富的数据可视化功能。

## 技术栈

- **框架**: React 18+
- **构建工具**: Vite
- **UI 组件库**: Ant Design 5.x
- **图表库**: Apache ECharts 5.x
- **HTTP 客户端**: Axios
- **路由**: React Router v6
- **状态管理**: React Hooks
- **样式**: CSS Modules + Ant Design

## 目录结构

```
frontend/
├── public/                    # 静态资源
├── src/
│   ├── App.jsx               # 应用主组件
│   ├── App.css               # 全局样式
│   ├── main.jsx              # 应用入口
│   │
│   ├── components/           # 可复用组件
│   │   ├── QueryInput.jsx            # 查询输入框
│   │   ├── ReportDisplay.jsx         # 报表展示
│   │   ├── SessionHistory.jsx        # 会话历史
│   │   ├── DatabaseConfigTab.jsx     # 数据库配置
│   │   ├── MCPServerConfigTab.jsx    # MCP Server 配置
│   │   └── index.js                  # 组件导出
│   │
│   ├── pages/                # 页面组件
│   │   ├── HomePage.jsx              # 主页
│   │   ├── SavedReportsPage.jsx      # 常用报表页
│   │   └── SettingsPage.jsx          # 设置页
│   │
│   ├── layouts/              # 布局组件
│   │   └── MainLayout.jsx            # 主布局
│   │
│   ├── services/             # API 服务
│   │   ├── reportService.js          # 报表服务
│   │   ├── sessionService.js         # 会话服务
│   │   ├── exportService.js          # 导出服务
│   │   └── index.js                  # 服务导出
│   │
│   └── utils/                # 工具函数
│       ├── api.js                    # API 客户端
│       └── dateFormatter.js          # 日期格式化
│
├── package.json              # 项目配置
├── vite.config.js            # Vite 配置
└── README.md                 # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 配置后端 API 地址

编辑 `src/utils/api.js`，确保 `baseURL` 指向正确的后端地址：

```javascript
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
});
```

### 3. 启动开发服务器

```bash
npm run dev
```

应用将运行在 `http://localhost:5173` 或 `http://localhost:5174`

### 4. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录

### 5. 预览生产版本

```bash
npm run preview
```

## 核心功能

### 1. 自然语言查询

在主页输入自然语言查询，系统自动：
- 生成 SQL 查询或 MCP 工具调用
- 执行查询并获取数据
- 推荐合适的图表类型
- 生成数据分析总结

**示例查询：**
- "显示2023年所有学生的平均成绩"
- "按专业分组统计学生人数"
- "查询最近一周的销售数据"

### 2. 数据可视化

支持多种图表类型：
- 柱状图 (Bar Chart)
- 折线图 (Line Chart)
- 饼图 (Pie Chart)
- 散点图 (Scatter Chart)
- 雷达图 (Radar Chart)
- 表格 (Table)

图表基于 ECharts，支持：
- 交互式操作（缩放、平移、数据筛选）
- 响应式设计
- 主题定制
- 数据导出

### 3. 会话管理

- **上下文追问**: 基于之前的查询继续提问
- **会话历史**: 查看和恢复历史查询
- **会话切换**: 管理多个会话
- **临时表**: 引用上一次查询结果

**示例对话：**
```
用户: 显示所有学生的平均成绩
系统: [显示结果]

用户: 按专业分组
系统: [基于上一次结果分组显示]
```

### 4. 常用报表

- **保存报表**: 将常用查询保存为模板
- **快速执行**: 一键执行保存的报表
- **定时刷新**: 定期更新报表数据
- **报表管理**: 编辑、删除、分类管理

### 5. 数据源配置

#### 数据库配置
- 支持 MySQL、PostgreSQL、SQLite
- 连接测试
- Schema 预览
- 敏感信息加密存储

#### MCP Server 配置
- 配置外部数据源
- 工具列表查看
- 连接测试
- 认证管理

### 6. 敏感信息保护

- **自然语言规则**: 用自然语言描述脱敏规则
- **预定义模式**: 手机号、邮箱、身份证等
- **自定义规则**: 灵活的 JSON 配置
- **实时预览**: 查看脱敏效果

**示例规则：**
- "手机号只显示前3位和后4位"
- "隐藏身份证号"
- "银行卡号保留前4位和后4位"

### 7. 报表导出

- **PDF 导出**: 包含图表和数据表
- **Excel 导出**: 多工作表，包含元信息
- **自定义选项**: 选择导出内容

## 组件说明

### QueryInput
查询输入组件，支持：
- 自然语言输入
- 数据源选择
- 模型选择
- 历史查询快速填充

### ReportDisplay
报表展示组件，包含：
- 图表渲染（ECharts）
- 数据表格
- 分析总结
- SQL 查询展示
- 导出按钮

### SessionHistory
会话历史组件，显示：
- 历史查询列表
- 查询时间
- 快速恢复
- 删除操作

### DatabaseConfigTab
数据库配置组件，功能：
- 添加/编辑数据库
- 连接测试
- Schema 查看
- 删除确认

### MCPServerConfigTab
MCP Server 配置组件，功能：
- 添加/编辑 MCP Server
- 工具列表查看
- 连接测试
- 认证配置

## API 集成

### 报表服务 (reportService.js)

```javascript
// 生成报表
await reportService.generateReport({
  query: "显示学生成绩",
  dataSourceIds: ["db-001"],
  sessionId: "session-123"
});

// 保存常用报表
await reportService.saveReport(reportData);

// 执行常用报表
await reportService.runSavedReport(reportId);
```

### 会话服务 (sessionService.js)

```javascript
// 创建会话
const session = await sessionService.createSession();

// 获取会话历史
const history = await sessionService.getSessionHistory(sessionId);

// 删除会话
await sessionService.deleteSession(sessionId);
```

### 导出服务 (exportService.js)

```javascript
// 导出为 PDF
await exportService.exportToPDF(reportData);

// 导出为 Excel
await exportService.exportToExcel(reportData);
```

## 样式定制

### 主题配置

在 `App.jsx` 中配置 Ant Design 主题：

```javascript
<ConfigProvider
  theme={{
    token: {
      colorPrimary: '#1890ff',
      borderRadius: 4,
    },
  }}
>
  {/* 应用内容 */}
</ConfigProvider>
```

### 自定义样式

使用 CSS Modules 或全局样式：

```css
/* App.css */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
```

## 开发指南

### 添加新页面

1. 在 `src/pages/` 创建页面组件
2. 在 `App.jsx` 中添加路由
3. 在导航菜单中添加链接

### 添加新组件

1. 在 `src/components/` 创建组件文件
2. 在 `src/components/index.js` 中导出
3. 在需要的地方导入使用

### 添加新的 API 服务

1. 在 `src/services/` 创建服务文件
2. 使用 `api` 实例发起请求
3. 在 `src/services/index.js` 中导出

### 调试技巧

```javascript
// 开启 React DevTools
// 安装浏览器扩展：React Developer Tools

// 查看 API 请求
// 在 api.js 中添加拦截器
api.interceptors.request.use(config => {
  console.log('Request:', config);
  return config;
});
```

## 性能优化

- **代码分割**: 使用 React.lazy 和 Suspense
- **图表优化**: 大数据集使用数据采样
- **缓存**: 缓存常用数据和配置
- **懒加载**: 按需加载组件和资源

## 浏览器兼容性

- Chrome (推荐)
- Firefox
- Safari
- Edge

建议使用最新版本的现代浏览器。

## 故障排查

### 问题：npm install 失败
**解决方案**: 
- 检查 Node.js 版本 (需要 18+)
- 清除缓存：`npm cache clean --force`
- 删除 `node_modules` 和 `package-lock.json` 后重试

### 问题：API 请求失败
**解决方案**:
- 检查后端服务是否运行
- 检查 `api.js` 中的 `baseURL` 配置
- 查看浏览器控制台的网络请求

### 问题：图表不显示
**解决方案**:
- 检查数据格式是否正确
- 查看浏览器控制台错误
- 确认 ECharts 已正确加载

### 问题：样式错乱
**解决方案**:
- 清除浏览器缓存
- 检查 Ant Design 版本兼容性
- 查看 CSS 冲突

## 构建和部署

### 开发环境

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

### 部署到静态服务器

```bash
# 构建
npm run build

# 部署 dist/ 目录到服务器
# 例如：Nginx, Apache, Vercel, Netlify
```

### 环境变量

创建 `.env` 文件配置环境变量：

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

在代码中使用：

```javascript
const apiUrl = import.meta.env.VITE_API_BASE_URL;
```

## 相关文档

- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)
- [Ant Design 文档](https://ant.design/)
- [ECharts 文档](https://echarts.apache.org/)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
