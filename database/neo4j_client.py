from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "Lokesh@12345"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def create_message_relationship(sender, receiver, content, timestamp):

    with driver.session() as session:
        session.run(
            """
            MERGE (s:Person {name:$sender})
            MERGE (r:Person {name:$receiver})
            CREATE (s)-[:MESSAGED {
                content:$content,
                timestamp:$timestamp
            }]->(r)
            """,
            sender=sender,
            receiver=receiver,
            content=content,
            timestamp=timestamp
        )


def create_call_relationship(caller, receiver, duration, timestamp):

    with driver.session() as session:
        session.run(
            """
            MERGE (c:Person {name:$caller})
            MERGE (r:Person {name:$receiver})
            CREATE (c)-[:CALLED {
                duration:$duration,
                timestamp:$timestamp
            }]->(r)
            """,
            caller=caller,
            receiver=receiver,
            duration=duration,
            timestamp=timestamp
        )