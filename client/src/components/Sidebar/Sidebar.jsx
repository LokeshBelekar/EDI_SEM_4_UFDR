import React, { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useCase } from "../../context/CaseContext";
import { forensicsApi } from "../../services/api";

import styles from "./Sidebar.module.css";

const Sidebar = () => {
  const { selectedCase, selectCase } = useCase();
  const [availableCases, setAvailableCases] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch cases on mount to populate the selector
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const cases = await forensicsApi.getCases();
        // Defensive fallback to empty array
        setAvailableCases(cases || []);
      } catch (error) {
        console.error("Failed to load forensic cases:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchCases();
  }, []);

  const handleCaseChange = (e) => {
    selectCase(e.target.value);
  };

  return (
    <aside className={styles.sidebar}>
      {/* Branding Section */}
      <div className={styles.brandContainer}>
        <h1 className={styles.logo}>
          UFDR <span className={styles.logoAccent}>AI</span>
        </h1>
        <div className={styles.systemStatus}>
          <span className={styles.statusDot}></span>
          AGENT v3.1.0 ONLINE
        </div>
      </div>

      <hr className={styles.divider} />

      {/* Global Case Selector */}
      <div className={styles.selectorSection}>
        <label htmlFor="case-select" className={styles.label}>
          INVESTIGATION CONTEXT
        </label>
        <select
          id="case-select"
          className={styles.caseDropdown}
          value={selectedCase || ""}
          onChange={handleCaseChange}
          disabled={loading}
        >
          <option value="" disabled>
            {loading ? "INITIALIZING..." : "SELECT CASE ID"}
          </option>
          {availableCases.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </div>

      {/* Navigation Links */}
      <nav className={styles.navLinks}>
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            isActive ? styles.navItemActive : styles.navItem
          }
        >
          COMMAND DASHBOARD
        </NavLink>

        <NavLink
          to="/investigation"
          className={({ isActive }) =>
            isActive ? styles.navItemActive : styles.navItem
          }
        >
          AI INVESTIGATION
        </NavLink>

        <NavLink
          to="/cases"
          className={({ isActive }) =>
            isActive ? styles.navItemActive : styles.navItem
          }
        >
          CASE REPOSITORY
        </NavLink>
      </nav>

      {/* Footer Info */}
      <div className={styles.sidebarFooter}>
        <div className={styles.terminalInfo}>NODE: LOCAL_STATION_01</div>
        <div className={styles.authStatus}>AUTH: LEVEL_4_ACCESS</div>
      </div>
    </aside>
  );
};

export default Sidebar;
