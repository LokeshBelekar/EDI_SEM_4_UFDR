from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "Lokesh@12345"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def get_top_contacts():

    with driver.session() as session:

        result = session.run(
            """
            MATCH (a)-[r]->(b)
            RETURN a.name AS person1,
                   b.name AS person2,
                   count(r) AS interaction_count
            ORDER BY interaction_count DESC
            """
        )

        contacts = []

        for record in result:
            contacts.append({
                "person1": record["person1"],
                "person2": record["person2"],
                "interaction_count": record["interaction_count"]
            })

        return contacts

def find_most_connected_people():

    with driver.session() as session:

        result = session.run(
            """
            MATCH (p:Person)-[r]-()
            RETURN p.name AS person,
                   count(r) AS connections
            ORDER BY connections DESC
            """
        )

        return [record.data() for record in result]
    


if __name__ == "__main__":

    contacts = get_top_contacts()

    for c in contacts:
        print(c)

    people = find_most_connected_people()

    for p in people:
        print(p)