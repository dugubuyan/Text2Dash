import api from '../utils/api';

// Session management
export const sessionService = {
  // Create a new session
  createSession: (userId) => {
    return api.post('/sessions', { user_id: userId });
  },

  // Get session details
  getSession: (id) => {
    return api.get(`/sessions/${id}`);
  },

  // Get session history
  getSessionHistory: (id) => {
    return api.get(`/sessions/${id}/history`);
  },
};

export default sessionService;
