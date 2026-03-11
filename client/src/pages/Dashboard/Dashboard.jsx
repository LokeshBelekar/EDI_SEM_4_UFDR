import React, { useEffect, useState } from "react";
import { useCase } from "../../context/CaseContext";
import { forensicsApi } from "../../services/api";
import styles from "./Dashboard.module.css";

const Dashboard = () => {
  const { selectedCase } = useCase();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!selectedCase) return;

    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await forensicsApi.getThreatMatrix(selectedCase);
        console.log("Forensic Threat Matrix Received:", result);
        setData(result);
      } catch (err) {
        setError(
          "DATA_RETRIEVAL_FAILURE: Check backend connectivity or CORS settings.",
        );
        console.error("Dashboard Fetch Error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [selectedCase]);

  // UI state logic (Empty/Loading/Error)
  if (!selectedCase) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>[ ! ]</div>
        <h2 className={styles.emptyTitle}>Awaiting Case Context</h2>
        <p className={styles.emptyText}>
          Select a target case from the Command Center to initialize analysis.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.dashboardContainer}>
        <div className={styles.skeletonHeader}></div>
        <div className={styles.skeletonGrid}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={styles.skeletonCard}></div>
          ))}
        </div>
        <div className={styles.skeletonTable}></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <span className={styles.errorCode}>ERR_CONNECTION_REFUSED</span>
        <p>{error}</p>
        <button
          onClick={() => window.location.reload()}
          className={styles.retryBtn}
        >
          RETRY SYSTEM LINK
        </button>
      </div>
    );
  }

  // --- Calculations based on Backend 0-1000 scale ---
  const HIGH_RISK_THRESHOLD = 700;

  return (
    <div className={styles.dashboardContainer}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <span className={styles.breadcrumb}>
            INTELLIGENCE / ANALYTICS / {selectedCase}
          </span>
          <h2 className={styles.viewTitle}>COMMAND DASHBOARD</h2>
        </div>
        <div className={styles.headerActions}>
          <div className={styles.timestamp}>
            LAST SCAN: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </header>

      {/* Investigation Statistics Grid */}
      <section className={styles.metricsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>HIGH RISK ENTITIES</span>
          <span className={`${styles.metricValue} ${styles.danger}`}>
            {data?.rankings?.filter((r) => r.threat_score > HIGH_RISK_THRESHOLD)
              .length || 0}
          </span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>TOTAL EVIDENCE NODES</span>
          <span className={styles.metricValue}>
            {/* Added optional chaining and fallback to 0 for missing node data */}
            {data?.rankings?.reduce(
              (acc, curr) =>
                acc +
                (curr.risk_indicators?.behavioral_analysis?.message_volume ||
                  0),
              0,
            ) || 0}
          </span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>NETWORK LINKS</span>
          <span className={styles.metricValue}>
            {(data?.entity_count * 1.5).toFixed(0)}
          </span>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>DETECTED INTENTS</span>
          <span className={styles.metricValue}>
            {/* Added fallback to empty array to prevent flatMap crashes on ghost nodes */}
            {[
              ...new Set(
                data?.rankings?.flatMap(
                  (r) =>
                    r.risk_indicators?.behavioral_analysis?.detected_intents ||
                    [],
                ),
              ),
            ].length || 0}
          </span>
        </div>
      </section>

      {/* POI Threat Ranking Table */}
      <section className={styles.tableSection}>
        <div className={styles.tableHeader}>
          <h3>POI THREAT MATRIX</h3>
          <span className={styles.tableSubtitle}>
            RANKED BY WEIGHTED RISK VECTOR
          </span>
        </div>
        <table className={styles.poiTable}>
          <thead>
            <tr>
              <th>ENTITY IDENTIFIER</th>
              <th>THREAT SCORE</th>
              <th>BROKERAGE RANK</th>
              <th>MSG VOLUME</th>
              <th>INTENT CONFIDENCE</th>
            </tr>
          </thead>
          <tbody>
            {data?.rankings
              ?.sort((a, b) => b.threat_score - a.threat_score)
              .map((poi, idx) => {
                const scorePercentage = (poi.threat_score / 10).toFixed(1);

                return (
                  <tr
                    key={idx}
                    className={
                      poi.threat_score > HIGH_RISK_THRESHOLD
                        ? styles.highRiskRow
                        : ""
                    }
                  >
                    <td className={styles.entityCell}>
                      <span className={styles.entityName}>
                        {poi.entity_name}
                      </span>
                      <span className={styles.entityUid}>UID-{idx + 1042}</span>
                    </td>
                    <td>
                      <div className={styles.scoreBarContainer}>
                        <div
                          className={styles.scoreBar}
                          style={{
                            width: `${scorePercentage}%`,
                            backgroundColor:
                              poi.threat_score > HIGH_RISK_THRESHOLD
                                ? "var(--accent-danger)"
                                : "var(--accent-primary)",
                          }}
                        ></div>
                        <span className={styles.scoreText}>
                          {scorePercentage}%
                        </span>
                      </div>
                    </td>
                    <td className={styles.monoText}>
                      {poi.risk_indicators?.network_influence?.brokerage_rank?.toFixed(
                        4,
                      ) || "0.0000"}
                    </td>
                    <td className={styles.monoText}>
                      {poi.risk_indicators?.behavioral_analysis
                        ?.message_volume || 0}
                    </td>
                    <td>
                      <span className={styles.intentBadge}>
                        {poi.risk_indicators?.behavioral_analysis?.intent_confidence_sum?.toFixed(
                          2,
                        ) || "0.00"}
                      </span>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </section>
    </div>
  );
};

export default Dashboard;
