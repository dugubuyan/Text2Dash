import api from '../utils/api';

// MCP Server configuration management
export const mcpService = {
  // Create MCP Server configuration
  createMCPServer: (data) => {
    return api.post('/mcp-servers', data);
  },

  // Get all MCP Server configurations
  getMCPServers: () => {
    return api.get('/mcp-servers');
  },

  // Get a single MCP Server configuration
  getMCPServer: (id) => {
    return api.get(`/mcp-servers/${id}`);
  },

  // Update MCP Server configuration
  updateMCPServer: (id, data) => {
    return api.put(`/mcp-servers/${id}`, data);
  },

  // Delete MCP Server configuration
  deleteMCPServer: (id) => {
    return api.delete(`/mcp-servers/${id}`);
  },

  // Test MCP Server connection
  testConnection: (id) => {
    return api.post(`/mcp-servers/${id}/test`);
  },

  // Get available tools from MCP Server
  getTools: (id) => {
    return api.get(`/mcp-servers/${id}/tools`);
  },
};

export default mcpService;
