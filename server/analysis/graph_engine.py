# File: analysis/graph_engine.py
import logging
import networkx as nx
from typing import Dict, Any, List, Optional
from db.neo4j import neo4j_conn

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
        Utilizes edge weights (communication frequency) for higher forensic accuracy.
        """
        if not self.driver:
            return None

        G = nx.Graph()
        
        # Optimized Cypher query to aggregate weights between nodes for this specific case
        query = """
        MATCH (p1:Person {case_id: $case_id})-[r:COMMUNICATED_WITH]-(p2:Person {case_id: $case_id})
        RETURN p1.name AS source, p2.name AS target, sum(r.weight) AS total_weight
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, case_id=case_id)
                for record in result:
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
        Identifies key influencers and potential leaders within the network.
        """
        G = self._build_networkx_graph(case_id)
        if G is None or G.number_of_nodes() == 0:
            return {}

        try:
            # 1. Degree Centrality: Volume of direct contacts
            degree = nx.degree_centrality(G)
            
            # 2. Betweenness Centrality: Influence as a broker or bridge
            betweenness = nx.betweenness_centrality(G)
            
            # 3. Closeness Centrality: Speed of information spread
            closeness = nx.closeness_centrality(G)
            
            # 4. PageRank: Overall influence accounting for interaction volume
            pagerank = nx.pagerank(G, weight='weight')

            # Consolidate metrics per entity
            metrics = {}
            for node in G.nodes():
                metrics[node] = {
                    "degree": round(degree.get(node, 0.0), 4),
                    "betweenness": round(betweenness.get(node, 0.0), 4),
                    "closeness": round(closeness.get(node, 0.0), 4),
                    "pagerank": round(pagerank.get(node, 0.0), 4)
                }
            
            logger.info(f"Centrality analysis completed for case: {case_id}")
            return metrics
        except Exception as e:
            logger.error(f"Error during centrality calculation for {case_id}: {e}")
            return {}

    def detect_communities(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Identifies isolated sub-groups or 'cells' within the communication 
        network using modularity maximization algorithms.
        """
        G = self._build_networkx_graph(case_id)
        if G is None or G.number_of_nodes() == 0:
            return []

        try:
            from networkx.algorithms import community
            # Utilizing edge weights for accurate community (cell) detection
            communities = list(community.greedy_modularity_communities(G, weight='weight'))
            
            formatted_communities = []
            for i, comm in enumerate(communities):
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

    def get_full_network_data(self, case_id: str) -> Dict[str, Any]:
        """
        Extracts the complete topology of the case network.
        Fuses relationship types from Neo4j with mathematical metrics from NetworkX.
        Formatted specifically for frontend visualization and Agentic reasoning.
        """
        if not self.driver:
            return {"nodes": [], "edges": []}

        # Retrieve analytical metrics to enrich node metadata
        centrality = self.get_advanced_centrality(case_id)
        communities = self.detect_communities(case_id)

        # Create lookup map for community assignments
        person_to_community = {}
        for comm in communities:
            for member in comm["members"]:
                person_to_community[member] = comm["community_id"]

        nodes = []
        edges = []
        added_nodes = set()

        # Query Neo4j for all relationship types (Calls, Messages, Media Sharing)
        query = """
        MATCH (n:Person {case_id: $case_id})-[r]->(m:Person {case_id: $case_id})
        RETURN n.name AS source, m.name AS target, type(r) AS rel_type, 
               r.weight AS weight, r.total_duration AS duration
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, case_id=case_id)
                for record in result:
                    source = record["source"]
                    target = record["target"]
                    rel_type = record["rel_type"]
                    weight = record["weight"] or 1
                    duration = record["duration"] or 0
                    
                    edges.append({
                        "source": source,
                        "target": target,
                        "type": rel_type,
                        "weight": weight,
                        "duration": duration
                    })
                    
                    # Ensure source and target nodes are represented with full metrics
                    for node_id in [source, target]:
                        if node_id not in added_nodes:
                            added_nodes.add(node_id)
                            metrics = centrality.get(node_id, {})
                            nodes.append({
                                "id": node_id,
                                "label": node_id,
                                "community": person_to_community.get(node_id, "Standalone"),
                                "pagerank": metrics.get("pagerank", 0.0),
                                "betweenness": metrics.get("betweenness", 0.0),
                                "degree": metrics.get("degree", 0.0)
                            })
                        
            logger.info(f"Full network data extracted for {case_id}: {len(nodes)} nodes, {len(edges)} edges.")
            return {"nodes": nodes, "edges": edges}
            
        except Exception as e:
            logger.error(f"Failed to fetch full network data for {case_id}: {e}")
            return {"nodes": [], "edges": []}

# Singleton instance
graph_engine = GraphEngine()