import axios from "axios";

// Changed to relative path to utilize the Vite Proxy
// This ensures the browser treats it as a same-origin request
const API_BASE_URL = "/api";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const forensicsApi = {
  /**
   * Fetches all case identifiers from the backend.
   * Scans the evidence repository folders.
   */
  getCases: async () => {
    const response = await apiClient.get("/cases");
    // Your backend returns { "cases": [...] }
    return response.data.cases;
  },

  /**
   * Retrieves the threat matrix for a specific case.
   * Fuses NLP risk and Graph centrality metrics.
   */
  getThreatMatrix: async (caseId) => {
    const response = await apiClient.get(`/poi`, {
      params: { case_id: caseId },
    });
    // Your backend returns { "case_id": id, "entity_count": n, "rankings": [...] }
    return response.data;
  },

  /**
   * Retrieves the persistent conversational history between the user and the AI.
   * @param {string} caseId
   * @returns {Promise<Array>} Array of message objects sorted chronologically.
   */
  getChatHistory: async (caseId) => {
    const response = await apiClient.get(`/chat/history/${caseId}`);
    return response.data;
  },

  /**
   * Permanently deletes the chat history for a specific case from the PostgreSQL database.
   * @param {string} caseId
   * @returns {Promise<Object>} Status of the deletion.
   */
  clearCaseMemory: async (caseId) => {
    const response = await apiClient.delete(`/chat/${caseId}`);
    return response.data;
  },

  /**
   * Sends a query to the Autonomous LangChain Agent.
   * The Agent automatically determines tools, executes them, and returns a synthesized report.
   * @param {string} caseId
   * @param {string} query
   * @returns {Promise<Object>} The AI's forensic report and metadata.
   */
  queryForensicAI: async (caseId, query) => {
    const response = await apiClient.post("/chat", {
      case_id: caseId,
      query: query,
    });
    // Your backend returns the ChatResponse model
    return response.data;
  },
};

export default apiClient;
