import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="forensics",
        user="postgres",
        password="Lokesh@12345",
        port="5432"
    )
    return conn