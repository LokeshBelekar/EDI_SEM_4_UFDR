import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

// Context
import { CaseProvider } from "./context/CaseContext";

// Components
import Sidebar from "./components/Sidebar/Sidebar";

// Pages
import CaseExplorer from "./pages/CaseExplorer/CaseExplorer";
import Dashboard from "./pages/Dashboard/Dashboard";
import Investigation from "./pages/Investigation/Investigation";

const App = () => {
  return (
    <CaseProvider>
      <Router>
        {/* Main Application Layout */}
        <div
          style={{
            display: "flex",
            height: "100vh",
            width: "100vw",
            overflow: "hidden",
          }}
        >
          {/* Sidebar is rendered globally outside the Routes so it never unmounts */}
          <Sidebar />

          {/* Main Content Area */}
          <main style={{ flexGrow: 1, overflowY: "auto" }}>
            <Routes>
              {/* Default redirect to the Case Repository on load */}
              <Route path="/" element={<Navigate to="/cases" replace />} />

              {/* Core Application Routes */}
              <Route path="/cases" element={<CaseExplorer />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/investigation" element={<Investigation />} />

              {/* Fallback for unknown URLs */}
              <Route path="*" element={<Navigate to="/cases" replace />} />
            </Routes>
          </main>
        </div>
      </Router>
    </CaseProvider>
  );
};

export default App;
