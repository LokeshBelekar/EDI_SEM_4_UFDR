import { useState, useEffect, useCallback } from 'react';
import { forensicsApi } from '../services/api';
import { useCase } from '../context/CaseContext';

export const useForensics = () => {
  const { selectedCase } = useCase();
  const [threatData, setThreatData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch Threat Matrix whenever the case changes
  const fetchThreatMatrix = useCallback(async () => {
    if (!selectedCase) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await forensicsApi.getThreatMatrix(selectedCase);
      setThreatData(data);
    } catch (err) {
      setError("THREAT_MATRIX_SYNC_ERROR: Data integrity check failed.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedCase]);

  useEffect(() => {
    fetchThreatMatrix();
  }, [fetchThreatMatrix]);

  // Execute AI Investigation Query
  const runAIInvestigation = async (query) => {
    if (!selectedCase) throw new Error("NO_CASE_CONTEXT");
    
    try {
      const response = await forensicsApi.queryForensicAI(selectedCase, query);
      return response;
    } catch (err) {
      console.error("AI_EXECUTION_FAILURE", err);
      throw err;
    }
  };

  return {
    threatData,
    loading,
    error,
    refreshData: fetchThreatMatrix,
    runAIInvestigation
  };
};