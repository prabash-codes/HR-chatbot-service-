import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

conn = pyodbc.connect(os.getenv("SQL_CONN_STRING"))
cursor = conn.cursor()

cursor.execute(
    "SELECT TOP 5 * FROM dbo.ChatHistory ORDER BY Timestamp DESC"
)
for row in cursor.fetchall():
    print(
        f"User: {row.UserID} | Role: {row.MessageRole} | "
        f"Text: {row.MessageText}"
    )

conn.close()