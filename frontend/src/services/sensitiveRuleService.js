import api from '../utils/api';

// Sensitive data rule management
export const sensitiveRuleService = {
  // Create sensitive rule
  createRule: (data) => {
    return api.post('/sensitive-rules', data);
  },

  // Get all sensitive rules
  getRules: () => {
    return api.get('/sensitive-rules');
  },

  // Update sensitive rule
  updateRule: (id, data) => {
    return api.put(`/sensitive-rules/${id}`, data);
  },

  // Delete sensitive rule
  deleteRule: (id) => {
    return api.delete(`/sensitive-rules/${id}`);
  },

  // Parse natural language to structured rule
  parseRule: (naturalLanguage, dbConfigId = null) => {
    return api.post('/sensitive-rules/parse', { 
      natural_language: naturalLanguage,
      db_config_id: dbConfigId
    });
  },
};

export default sensitiveRuleService;
