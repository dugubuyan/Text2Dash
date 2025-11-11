import api from '../utils/api';

// Model management
export const modelService = {
  // Get available models
  getModels: () => {
    return api.get('/models');
  },
};

export default modelService;
