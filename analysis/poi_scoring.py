from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "Lokesh@12345"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


suspicious_keywords = [
    "crypto",
    "bitcoin",
    "transfer",
    "payment",
    "wallet"
]


def get_people():

    with driver.session() as session:

        result = session.run(
            """
            MATCH (p:Person)
            RETURN p.name AS name
            """
        )

        return [record["name"] for record in result]


def communication_frequency(person):

    with driver.session() as session:

        result = session.run(
            """
            MATCH (p:Person {name:$name})-[r]->()
            RETURN count(r) AS freq
            """,
            name=person
        )

        return result.single()["freq"]


def network_connections(person):

    with driver.session() as session:

        result = session.run(
            """
            MATCH (p:Person {name:$name})-[r]-()
            RETURN count(r) AS connections
            """,
            name=person
        )

        return result.single()["connections"]


def suspicious_messages(person):

    with driver.session() as session:

        result = session.run(
            """
            MATCH (p:Person {name:$name})-[r:MESSAGED]->()
            RETURN r.content AS message
            """,
            name=person
        )

        count = 0

        for record in result:

            message = record["message"]

            # skip if message is None
            if message is None:
                continue

            message = message.lower()

            for word in suspicious_keywords:
                if word in message:
                    count += 1
                    break

        return count


def compute_poi_scores():

    people = get_people()

    scores = []

    for person in people:

        freq = communication_frequency(person)
        connections = network_connections(person)
        suspicious = suspicious_messages(person)

        score = (
            freq * 0.4 +
            connections * 0.3 +
            suspicious * 0.3
        )

        scores.append({
            "person": person,
            "frequency": freq,
            "connections": connections,
            "suspicious_msgs": suspicious,
            "poi_score": round(score, 2)
        })

    scores.sort(key=lambda x: x["poi_score"], reverse=True)

    return scores


if __name__ == "__main__":

    results = compute_poi_scores()

    print("\nPerson of Interest Ranking\n")

    for r in results:
        print(r)