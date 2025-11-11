import api from '../utils/api';

// Report generation and management
export const reportService = {
  // Generate report from natural language query
  generateReport: (data) => {
    return api.post('/reports/query', data);
  },

  // Save a report as saved report
  saveReport: (data) => {
    return api.post('/reports/saved', data);
  },

  // Get all saved reports
  getSavedReports: () => {
    return api.get('/reports/saved');
  },

  // Get a single saved report
  getSavedReport: (id) => {
    return api.get(`/reports/saved/${id}`);
  },

  // Update a saved report
  updateSavedReport: (id, data) => {
    return api.put(`/reports/saved/${id}`, data);
  },

  // Delete a saved report
  deleteSavedReport: (id) => {
    return api.delete(`/reports/saved/${id}`);
  },

  // Run a saved report
  runSavedReport: (id, withAnalysis = false) => {
    return api.post(`/reports/saved/${id}/run`, { with_analysis: withAnalysis });
  },
};

export default reportService;
