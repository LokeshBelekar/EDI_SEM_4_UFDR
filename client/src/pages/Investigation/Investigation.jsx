import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { useCase } from "../../context/CaseContext";
import { forensicsApi } from "../../services/api";
import styles from "./Investigation.module.css";

const Investigation = () => {
  const { selectedCase } = useCase();
  const [query, setQuery] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  // 1. Auto-scroll logic for terminal output
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatLog, isProcessing]);

  // 2. Recover focus after processing finishes
  useEffect(() => {
    if (!isProcessing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isProcessing]);

  // 3. Fetch Persistent Chat History when a Case is Selected
  useEffect(() => {
    if (!selectedCase) return;

    const loadHistory = async () => {
      setIsProcessing(true);
      try {
        const history = await forensicsApi.getChatHistory(selectedCase);

        // Map the backend history schema to the frontend UI schema
        const formattedHistory = history.map((msg) => {
          if (msg.role === "ai") {
            return {
              role: "ai",
              intent: "AUTONOMOUS_AGENT",
              report: msg.content,
              entities: {},
              timestamp: msg.timestamp,
            };
          }
          return msg;
        });

        setChatLog(formattedHistory);
      } catch (err) {
        console.error("Failed to load chat history:", err);
        setChatLog([]);
      } finally {
        setIsProcessing(false);
      }
    };

    loadHistory();
  }, [selectedCase]);

  // 4. Handle Persistent Memory Clearing (Backend & Frontend)
  const handleClearMemory = async () => {
    if (!selectedCase || isProcessing) return;

    const confirmClear = window.confirm("PERMANENTLY CLEAR CASE MEMORY?");
    if (!confirmClear) return;

    setIsProcessing(true);
    try {
      await forensicsApi.clearCaseMemory(selectedCase);
      setChatLog([]);
    } catch (err) {
      console.error("Failed to clear memory:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  // 5. Submit New Query to the Autonomous Agent
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || !selectedCase || isProcessing) return;

    const userMessage = {
      role: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString(),
    };

    setChatLog((prev) => [...prev, userMessage]);
    setQuery("");
    setIsProcessing(true);

    try {
      const response = await forensicsApi.queryForensicAI(selectedCase, query);

      const aiResponse = {
        role: "ai",
        intent: response.intent_detected,
        report: response.forensic_report,
        entities: response.entities_extracted,
        timestamp: new Date().toLocaleTimeString(),
      };

      setChatLog((prev) => [...prev, aiResponse]);
    } catch (err) {
      console.error("Forensic AI Failure:", err);
      setChatLog((prev) => [
        ...prev,
        {
          role: "error",
          content:
            "CRITICAL_COMM_FAILURE: Agent Engine unreachable or Context Timeout.",
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!selectedCase) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.terminalIcon}>&gt;_</div>
        <h2 className={styles.emptyTitle}>Awaiting Case Context</h2>
        <p className={styles.emptyText}>
          Initialize investigative terminal by selecting a Case ID from the
          command sidebar.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.investigationWrapper}>
      <header className={styles.chatHeader}>
        <div className={styles.headerInfo}>
          <span className={styles.statusLabel}>TERMINAL_SESSION_ACTIVE</span>
          <h2 className={styles.caseTitle}>INVESTIGATION: {selectedCase}</h2>
        </div>
        <div className={styles.sessionMeta}>
          <span className={styles.encryptionBadge}>SECURE_TUNNEL: AES-256</span>
          <button
            className={styles.clearBtn}
            onClick={handleClearMemory}
            disabled={isProcessing}
          >
            RESET BUFFER
          </button>
        </div>
      </header>

      <div className={styles.chatDisplay} ref={scrollRef}>
        {chatLog.length === 0 && !isProcessing && (
          <div className={styles.introMessage}>
            <div className={styles.systemBanner}>
              UFDR AI FORENSIC ANALYZER v3.1.0
            </div>
            <p>
              READY FOR INPUT. QUERY AUTONOMOUS AGENT FOR RELATIONAL OR
              BEHAVIORAL PATTERNS.
            </p>
          </div>
        )}

        {chatLog.map((msg, idx) => (
          <div key={idx} className={`${styles.messageRow} ${styles[msg.role]}`}>
            {msg.role === "user" ? (
              <div className={styles.userMessage}>
                <span className={styles.prompt}>INVESTIGATOR@LOCAL:~$</span>{" "}
                {msg.content}
              </div>
            ) : msg.role === "ai" ? (
              <div className={styles.aiMessage}>
                <div className={styles.aiHeader}>
                  <span className={styles.intentBadge}>[{msg.intent}]</span>
                  <span className={styles.msgTime}>{msg.timestamp}</span>
                </div>

                <div className={styles.reportContent}>
                  <div className={styles.markdownWrapper}>
                    <ReactMarkdown>{msg.report}</ReactMarkdown>
                  </div>
                </div>

                {Object.keys(msg.entities || {}).some(
                  (k) => msg.entities[k]?.length > 0,
                ) && (
                  <div className={styles.entityContainer}>
                    <div className={styles.entityLabel}>
                      EXTRACTED_ENTITIES:
                    </div>
                    <div className={styles.entityTagCloud}>
                      {Object.entries(msg.entities).map(([key, val]) => {
                        if (!val || (Array.isArray(val) && val.length === 0))
                          return null;
                        return (
                          <div key={key} className={styles.entityTag}>
                            <span className={styles.tagKey}>
                              {key.toUpperCase()}:
                            </span>
                            <span className={styles.tagVal}>
                              {Array.isArray(val) ? val.join(", ") : val}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.errorMessage}>
                <span className={styles.errorIcon}>[!]</span> {msg.content}
              </div>
            )}
          </div>
        ))}

        {isProcessing && (
          <div className={styles.processingState}>
            <div className={styles.loaderLine}></div>
            <span className={styles.processingText}>
              ANALYZING EVIDENCE NODES...
            </span>
          </div>
        )}
      </div>

      <footer className={styles.footerInput}>
        <form className={styles.inputArea} onSubmit={handleSubmit}>
          <span className={styles.inputPrefix}>&gt;</span>
          <input
            ref={inputRef}
            type="text"
            className={styles.chatInput}
            placeholder="Execute query (e.g., 'Identify high-risk communication clusters')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isProcessing}
          />
          <button
            type="submit"
            className={styles.sendButton}
            disabled={isProcessing}
          >
            {isProcessing ? "PROCESSING..." : "EXECUTE"}
          </button>
        </form>
      </footer>
    </div>
  );
};

export default Investigation;
