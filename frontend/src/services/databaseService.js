import api from '../utils/api';

// Database configuration management
export const databaseService = {
  // Create database configuration
  createDatabase: (data) => {
    return api.post('/databases', data);
  },

  // Get all database configurations
  getDatabases: () => {
    return api.get('/databases');
  },

  // Get a single database configuration
  getDatabase: (id) => {
    return api.get(`/databases/${id}`);
  },

  // Update database configuration
  updateDatabase: (id, data) => {
    return api.put(`/databases/${id}`, data);
  },

  // Delete database configuration
  deleteDatabase: (id) => {
    return api.delete(`/databases/${id}`);
  },

  // Test database connection
  testConnection: (id) => {
    return api.post(`/databases/${id}/test`);
  },
};

export default databaseService;
