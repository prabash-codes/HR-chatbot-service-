import os
import pyodbc
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from openai import AzureOpenAI
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="HR Chatbot Backend")

# Model for incoming requests
class ChatRequest(BaseModel):
    user_id: str
    question: str

# Azure OpenAI Clients
client_embed = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
client_chat = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY2"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT2")
)

def get_db_conn():
    return pyodbc.connect(os.getenv("SQL_CONN_STRING"))

@app.post("/chat")
async def chat(data: ChatRequest):
    # 1. VALIDATION: Prevent blank UserID rows 
    if not data.user_id or not data.user_id.strip():
        raise HTTPException(status_code=400, detail="User ID is required")
    
    clean_user_id = data.user_id.strip()
    conn = get_db_conn()
    cursor = conn.cursor()

    try:
        # 2. RECALL: Get history ONLY for this user 
        cursor.execute(
            "SELECT TOP 6 MessageRole, MessageText FROM dbo.ChatHistory WHERE UserID = ? ORDER BY Timestamp ASC",
            (clean_user_id,)
        )
        history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

        # 3. VECTORIZE & RETRIEVE (RAG)
        q_embeddings = client_embed.embeddings.create(input=[data.question], model="text-embedding-3-small")
        q_vector = str(q_embeddings.data[0].embedding)
        
        search_query = """
        SELECT TOP 3 Content FROM dbo.HR_Knowledge 
        ORDER BY VECTOR_DISTANCE('cosine', CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(1536)), Embedding)
        """
        cursor.execute(search_query, (q_vector,))
        context = "\n".join([r[0] for r in cursor.fetchall()])

        # 4. GENERATE
        messages = [
            {"role": "system", "content": "You are a McLarens HR Assistant. Answer using ONLY the provided context."},
            *history,
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {data.question}"}
        ]
        response = client_chat.chat.completions.create(model="gpt-4o", messages=messages)
        answer = response.choices[0].message.content

        # 5. STORE: Save with Timestamp 
        now = datetime.now()
        cursor.execute(
            "INSERT INTO dbo.ChatHistory (UserID, MessageRole, MessageText, Timestamp) VALUES (?, 'user', ?, ?), (?, 'assistant', ?, ?)",
            (clean_user_id, data.question, now, clean_user_id, answer, now)
        )
        conn.commit()
        return {"answer": answer}

    finally:
        conn.close()