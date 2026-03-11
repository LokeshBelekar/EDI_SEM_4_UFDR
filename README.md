# UFDR AI Forensic Analyzer (v3.1.0)

The UFDR AI Forensic Analyzer is an enterprise-grade digital evidence processing suite. It leverages an Autonomous LangChain Agent to fuse PostgreSQL relational data, Neo4j graph networks, and Hugging Face NLP behavioral analytics into structured forensic intelligence.

---

## Frontend Setup (React + Vite)

### Prerequisites
* **Node.js**: v18.0 or higher.
* **Package Manager**: npm or yarn.

### Installation
1. Navigate to the client directory:
   ```bash
   cd client
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
   *Note: Dependencies include `react-router-dom` for navigation, `axios` for API communication, and `react-markdown` for forensic report rendering.*

### Configuration
The frontend utilizes a Vite Proxy to communicate with the FastAPI backend to prevent CORS conflicts.
* **Vite Config**: Ensure `vite.config.js` is configured to proxy `/api` requests to `http://localhost:8000`.
* **Environment**: Create a `.env` file in the client root if you need to override `VITE_API_BASE_URL`.

### Execution
```bash
npm run dev
```
The interface will be accessible at `http://localhost:5173`.

---

## Backend Setup (FastAPI + LangChain)

### Prerequisites
* **Python**: 3.10 or higher.
* **PostgreSQL**: Local or cloud instance.
* **Neo4j**: v4.x or v5.x.
* **Groq API Key**: Required for the Llama-3 model.

### Installation
1. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/macOS
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Create a `.env` file in the server root directory with the following variables:

**PostgreSQL & Neo4j**
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=forensics

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

**AI Model (Groq)**
```env
GROQ_API_KEY=your_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

---

## Database and Data Ingestion

### 1. Initialize Schemas
Before running the system, initialize the database schemas and constraints. 
**Warning**: This action will truncate existing data.
```bash
python -m database.init_schema
```

### 2. Ingest Forensic Evidence
Place case folders (containing `messages.csv`, `call_logs.csv`, etc.) in the `/touse` directory and execute the pipeline:
```bash
python -m pipeline.ingestion
```

---

## System Execution

1.  **Start the Backend**:
    ```bash
    uvicorn main:app --reload
    ```
    The API will be live at `http://localhost:8000`.

2.  **Start the Frontend**:
    ```bash
    npm run dev
    ```
    The UI will be live at `http://localhost:5173`.

---

## System Architecture Notes

* **Autonomous Agent**: The system utilizes a persistent LangChain agent. Intent routing is handled automatically based on natural language queries.
* **Memory Persistence**: Chat history is stored in PostgreSQL and can be cleared via the "Reset Buffer" action in the UI.
* **Threat Matrix**: Person of Interest (POI) rankings are calculated using a weighted matrix:
    $$ThreatScore = 0.40(NLP_{Risk}) + 0.35(G_{Betweenness}) + 0.15(G_{Degree}) + 0.10(G_{Closeness})$$
