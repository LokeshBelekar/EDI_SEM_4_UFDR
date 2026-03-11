import logging
import networkx as nx
from typing import Dict, Any, List, Optional
from database.neo4j_db import neo4j_conn

# Configure professional logging
logger = logging.getLogger("GraphEngine")

class GraphEngine:
    """
    Advanced Graph Analysis Engine providing forensic network metrics.
    Combines Neo4j graph persistence with NetworkX for complex 
    centrality, weighted PageRank, and community detection algorithms.
    """

    def __init__(self):
        self.driver = neo4j_conn.get_driver()
        if not self.driver:
            logger.error("Neo4j driver not initialized. Graph analysis will be unavailable.")

    def _build_networkx_graph(self, case_id: str) -> Optional[nx.Graph]:
        """
        Projects a Neo4j case subgraph into an in-memory NetworkX object.
        Now utilizes edge weights (communication frequency) for higher accuracy.
        """
        if not self.driver:
            return None

        G = nx.Graph()
        
        # Optimized Cypher query to aggregate weights between nodes
        query = """
        MATCH (p1:Person {case_id: $case_id})-[r:COMMUNICATED_WITH]-(p2:Person {case_id: $case_id})
        RETURN p1.name AS source, p2.name AS target, sum(r.weight) AS total_weight
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, case_id=case_id)
                for record in result:
                    # Ensure we have a valid weight, default to 1 if missing
                    weight = record["total_weight"] or 1
                    G.add_edge(record["source"], record["target"], weight=weight)
            
            logger.info(f"Memory graph built for {case_id}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
            return G
        except Exception as e:
            logger.error(f"Failed to project graph into NetworkX for {case_id}: {e}")
            return None

    def get_advanced_centrality(self, case_id: str) -> Dict[str, Dict[str, float]]:
        """
        Calculates multi-dimensional centrality metrics including Weighted PageRank.
        """
        G = self._build_networkx_graph(case_id)
        if G is None or G.number_of_nodes() == 0:
            return {}

        try:
            # 1. Degree Centrality: Volume of direct contacts (normalized topological reach)
            degree = nx.degree_centrality(G)
            
            # 2. Betweenness Centrality: Influence as a 'bridge' or broker (unweighted topological)
            betweenness = nx.betweenness_centrality(G)
            
            # 3. Closeness Centrality: How quickly information spreads (unweighted topological)
            closeness = nx.closeness_centrality(G)
            
            # 4. PageRank: Overall influence accounting for edge weights (communication volume)
            pagerank = nx.pagerank(G, weight='weight')

            # Consolidate metrics per person
            metrics = {}
            for node in G.nodes():
                metrics[node] = {
                    "degree": round(degree.get(node, 0.0), 4),
                    "betweenness": round(betweenness.get(node, 0.0), 4),
                    "closeness": round(closeness.get(node, 0.0), 4),
                    "pagerank": round(pagerank.get(node, 0.0), 4) # Added PageRank
                }
            
            logger.info(f"Centrality analysis completed for case: {case_id}")
            return metrics
        except Exception as e:
            logger.error(f"Error during centrality calculation for {case_id}: {e}")
            return {}

    def detect_communities(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Identifies isolated sub-groups or 'cells' within the communication 
        network using greedy modularity maximization, now utilizing edge weights.
        """
        G = self._build_networkx_graph(case_id)
        if G is None or G.number_of_nodes() == 0:
            return []

        try:
            from networkx.algorithms import community
            # Utilizing edge weights for highly accurate community (cell) detection
            communities = list(community.greedy_modularity_communities(G, weight='weight'))
            
            formatted_communities = []
            for i, comm in enumerate(communities):
                # Format as isolated network cells
                formatted_communities.append({
                    "community_id": f"Cell-{i + 1}",
                    "size": len(comm),
                    "members": sorted(list(comm))
                })
            
            logger.info(f"Detected {len(formatted_communities)} behavioral cells in case: {case_id}")
            return formatted_communities
        except Exception as e:
            logger.error(f"Community detection failed for {case_id}: {e}")
            return []

# Singleton instance
graph_engine = GraphEngine()