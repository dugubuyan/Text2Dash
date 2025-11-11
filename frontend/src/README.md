# Frontend Structure

## Directory Structure

```
src/
├── layouts/          # Layout components
│   └── MainLayout.jsx
├── services/         # API service modules
│   ├── index.js
│   ├── reportService.js
│   ├── sessionService.js
│   ├── databaseService.js
│   ├── mcpService.js
│   ├── sensitiveRuleService.js
│   ├── exportService.js
│   └── modelService.js
├── utils/            # Utility functions
│   ├── api.js        # Axios instance with interceptors
│   └── notification.js  # Notification utilities
├── hooks/            # Custom React hooks
│   └── useNotification.js
├── App.jsx           # Main application component
└── main.jsx          # Application entry point
```

## Key Features Implemented

### 1. Main Layout (Task 12.1)
- **MainLayout.jsx**: Ant Design Layout with sidebar, header, and content area
- Collapsible sidebar with navigation menu
- Three main menu items: Home, Saved Reports, Settings
- Responsive design with proper styling

### 2. API Client (Task 12.2)
- **api.js**: Axios instance with base configuration
  - Base URL: `http://localhost:8000/api` (configurable via env)
  - 30-second timeout
  - Request/response interceptors
  - Proxy configuration in vite.config.js

- **Service Modules**: Organized API calls by domain
  - `reportService`: Report generation and management
  - `sessionService`: Session management
  - `databaseService`: Database configuration
  - `mcpService`: MCP Server configuration
  - `sensitiveRuleService`: Sensitive data rules
  - `exportService`: PDF/Excel export with download helper
  - `modelService`: Model management

### 3. Error Notification (Task 12.3)
- **notification.js**: Comprehensive notification utilities
  - Message functions: success, error, warning, info, loading
  - Notification functions: with title and description
  - API error handler with status code mapping
  - Operation helpers for common CRUD operations

- **useNotification.js**: Custom React hook
  - Convenient access to notification functions in components
  - Memoized callbacks for performance

## Usage Examples

### Using API Services

```javascript
import { reportService } from './services';
import { handleApiError, operationSuccess } from './utils/notification';

// Generate report
try {
  const response = await reportService.generateReport({
    query: "显示所有学生的平均成绩",
    model: "gemini/gemini-2.0-flash",
    session_id: sessionId,
    data_source_ids: [dbId]
  });
  operationSuccess.create('报表');
} catch (error) {
  handleApiError(error, '生成报表失败');
}
```

### Using Notifications in Components

```javascript
import useNotification from './hooks/useNotification';

function MyComponent() {
  const { success, error, handleError, operationSuccess } = useNotification();
  
  const handleSave = async () => {
    try {
      await saveData();
      operationSuccess.save('配置');
    } catch (err) {
      handleError(err, '保存失败');
    }
  };
  
  return <button onClick={handleSave}>Save</button>;
}
```

### Using Main Layout

```javascript
import MainLayout from './layouts/MainLayout';

function App() {
  return (
    <MainLayout>
      <YourContent />
    </MainLayout>
  );
}
```

## Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_BASE_URL=http://localhost:8000/api
```

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Dependencies

- **react**: ^19.1.1
- **react-dom**: ^19.1.1
- **antd**: UI component library
- **axios**: HTTP client
- **echarts**: Charting library
- **@ant-design/icons**: Icon library
