import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="forensics",
    user="postgres",
    password="Lokesh@12345",
    port="5432"
)

print("PostgreSQL connection successful")

conn.close()