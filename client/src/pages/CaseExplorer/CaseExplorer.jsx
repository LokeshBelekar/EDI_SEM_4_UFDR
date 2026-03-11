import React, { useEffect, useState } from "react";
import { useCase } from "../../context/CaseContext";
import { forensicsApi } from "../../services/api";
import styles from "./CaseExplorer.module.css";

const CaseExplorer = () => {
  const { selectedCase, selectCase } = useCase();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadCases = async () => {
      setLoading(true);
      try {
        const data = await forensicsApi.getCases();
        // Fallback to empty array just in case the backend returns undefined
        setCases(data || []);
      } catch (err) {
        setError(
          "FAILED_TO_ACCESS_ARCHIVE: Connection to Case Management Service lost.",
        );
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadCases();
  }, []);

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.pulseDisk}></div>
        <p className={styles.loadingText}>ACCESSING SECURE ARCHIVE...</p>
      </div>
    );
  }

  if (error) {
    return <div className={styles.errorMessage}>{error}</div>;
  }

  return (
    <div className={styles.explorerWrapper}>
      <header className={styles.explorerHeader}>
        <div className={styles.headerInfo}>
          <span className={styles.breadcrumb}>SYSTEM / ARCHIVE / VOLUMES</span>
          <h2 className={styles.viewTitle}>CASE REPOSITORY</h2>
        </div>
        <div className={styles.repoStats}>
          <div className={styles.statBox}>
            <span className={styles.statLabel}>AVAILABLE_VOLUMES</span>
            <span className={styles.statValue}>{cases.length}</span>
          </div>
        </div>
      </header>

      {cases.length === 0 ? (
        <div className={styles.noDataState}>
          <p>NO ACTIVE VOLUMES DETECTED IN BACKEND STORAGE.</p>
        </div>
      ) : (
        <div className={styles.caseGrid}>
          {cases.map((caseId) => (
            <div
              key={caseId}
              className={`${styles.caseCard} ${selectedCase === caseId ? styles.activeCard : ""}`}
              onClick={() => selectCase(caseId)}
            >
              <div className={styles.cardGlow}></div>
              <div className={styles.cardHeader}>
                <div className={styles.folderIcon}>
                  <div className={styles.folderTab}></div>
                  <div className={styles.folderBody}></div>
                </div>
                <div className={styles.caseIdGroup}>
                  <span className={styles.caseIdLabel}>CASE_IDENTIFIER</span>
                  <span className={styles.caseIdValue}>{caseId}</span>
                </div>
              </div>

              <div className={styles.cardBody}>
                <div className={styles.dataPoint}>
                  <span className={styles.pLabel}>CLASSIFICATION:</span>
                  <span className={styles.pValue}>UNCLASSIFIED_LEO</span>
                </div>
                <div className={styles.dataPoint}>
                  <span className={styles.pLabel}>PROCESSING CORE:</span>
                  <span className={styles.pValue}>LANGCHAIN_AGENT_v3</span>
                </div>
              </div>

              <div className={styles.cardFooter}>
                <button
                  className={styles.activateBtn}
                  disabled={selectedCase === caseId}
                >
                  {selectedCase === caseId
                    ? "AGENT_CONTEXT_ACTIVE"
                    : "INITIALIZE_AGENT"}
                </button>
                {selectedCase === caseId && (
                  <span className={styles.activePulse}></span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CaseExplorer;
