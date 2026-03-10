from neo4j import GraphDatabase

URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "Lokesh@12345"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

with driver.session(database="forensic-graph") as session:
    session.run(
        "CREATE (p:Person {name:$name})",
        name="John"
    )

print("Neo4j connection successful and node created!")

driver.close()