import axios from 'axios';

// Create axios instance with base configuration
// In development, use proxy (just /api)
// In production, use full URL from environment variable
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 120000, // 增加到 120 秒，因为 LLM 调用可能需要较长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // You can add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Error handling is done in components using notification utilities
    // This allows for more flexible error handling per request
    return Promise.reject(error);
  }
);

export default api;
