import React, { createContext, useState, useContext, useEffect } from "react";

const CaseContext = createContext();

/**
 * Global Case Provider
 * Handles the persistent state of the active investigation case_id.
 * Essential for maintaining context across the Dashboard and Autonomous Agent terminal.
 */
export const CaseProvider = ({ children }) => {
  // Initialize from localStorage to persist case selection on page refresh
  const [selectedCase, setSelectedCase] = useState(() => {
    return localStorage.getItem("active_case_id") || null;
  });

  // Update localStorage whenever the case changes
  useEffect(() => {
    if (selectedCase) {
      localStorage.setItem("active_case_id", selectedCase);
      // Helpful debug trace for monitoring Agent context switching
      console.log(`[SYS] Agent Global Context Switched: ${selectedCase}`);
    } else {
      localStorage.removeItem("active_case_id");
      console.log(`[SYS] Agent Global Context Cleared`);
    }
  }, [selectedCase]);

  const selectCase = (caseId) => {
    setSelectedCase(caseId);
  };

  const clearCase = () => {
    setSelectedCase(null);
  };

  return (
    <CaseContext.Provider value={{ selectedCase, selectCase, clearCase }}>
      {children}
    </CaseContext.Provider>
  );
};

/**
 * Custom hook for accessing investigation context
 */
export const useCase = () => {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error(
      "useCase must be used within a CaseProvider. Ensure your router is wrapped properly.",
    );
  }
  return context;
};
