import api from '../utils/api';

// Export service
export const exportService = {
  // Export report to PDF
  exportToPDF: (data) => {
    return api.post('/export/pdf', data, {
      responseType: 'blob',
    });
  },

  // Export report to Excel
  exportToExcel: (data) => {
    return api.post('/export/excel', data, {
      responseType: 'blob',
    });
  },

  // Helper function to download file
  downloadFile: (blob, filename) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

export default exportService;
