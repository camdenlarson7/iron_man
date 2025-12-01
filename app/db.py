import psycopg2
import psycopg2.extras


def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="triathlon_db",
        user="tri_user",
        password="Soccercam57@",
    )
    return conn


def test_connection():
    try:
        conn = get_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT 1 AS test;")
                row = cur.fetchone()
                print("Test query result:", row["test"])
    except Exception as e:
        print("Error connecting to database:", e)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    test_connection()
