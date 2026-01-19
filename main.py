import os
import pyodbc
from fastapi import FastAPI, Request, HTTPException
from openai import AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

# 1. Load Environment Variables from your .env file
load_dotenv()

app = FastAPI(title="HR Policy Chatbot Service")

class ChatRequest(BaseModel):
    user_id: str
    question: str

# 2. Initialize Azure OpenAI Client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
client2 = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY2"),
    api_version="2024-12-01-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT2")
)

def get_db_connection():
    # Uses the connection string from your .env
    print(f"DEBUGGING CONNECTION STRING: {os.getenv('SQL_CONN_STRING')}")
    return pyodbc.connect(os.getenv("SQL_CONN_STRING"))

def get_ai_response(user_id: str, question: str):
    print(f"Processing question for user {user_id}: {question}")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # A. RECALL: Get the last 6 messages for this specific user
        cursor.execute(
            "SELECT TOP 6 MessageRole, MessageText FROM dbo.ChatHistory WHERE UserID = ? ORDER BY Timestamp ASC", 
            (user_id,)
        )
        history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

        # B. VECTORIZE: Turn the user's question into a vector
        q_embeddings = client.embeddings.create(input=[question], model="text-embedding-3-small")
        q_vector = str(q_embeddings.data[0].embedding)

        # C. RETRIEVE: Search HR_Knowledge for relevant policy chunks
        # Note: Ensure your SQL supports the VECTOR_DISTANCE function as in your notebook
        search_query = """
        SELECT TOP 3 Content, SourceFile 
        FROM dbo.HR_Knowledge 
        ORDER BY VECTOR_DISTANCE('cosine', CAST(CAST(? AS NVARCHAR(MAX)) AS VECTOR(1536)), Embedding)
        """
        cursor.execute(search_query, (q_vector,))
        context_rows = cursor.fetchall()
        context_text = "\n\n".join([f"Source: {r[1]}\n{r[0]}" for r in context_rows])

        # D. GENERATE: Construct the message list for GPT-4o
        messages = [
            {"role": "system", "content": "You are a professional HR Assistant. Answer questions based ONLY on the provided context and conversation history."}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": f"Context from Policies:\n{context_text}\n\nUser Question: {question}"})

        response = client2.chat.completions.create(model="gpt-4o", messages=messages)
        answer = response.choices[0].message.content

        # E. STORE: Save this exchange to ChatHistory for next time
        cursor.execute(
            "INSERT INTO dbo.ChatHistory (UserID, MessageRole, MessageText) VALUES (?, 'user', ?), (?, 'assistant', ?)",
            (user_id, question, user_id, answer)
        )
        conn.commit()

        return answer

    except Exception as e:
        print(f"Error in RAG Pipeline: {e}")
        raise HTTPException(status_code=500, detail="Internal AI Processing Error")
    finally:
        conn.close()

# 3. The Web Endpoint
@app.post("/chat")
async def chat(data: ChatRequest):
    try:
        # This triggers the entire RAG flow and the database save
        final_answer = get_ai_response(data.user_id, data.question)
        
        return {
            "user_id": data.user_id, 
            "question": data.question,
            "answer": final_answer  # This will now show in your Swagger response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "online", "service": "HR Bot"}