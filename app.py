import streamlit as st
import requests

st.set_page_config(page_title="HR Chatbot", page_icon="🏢")

# 1. IDENTITY: Use official headers for Azure Authentication [cite: 81]
user_id = st.context.headers.get("X-Ms-Client-Principal-Name")

# Fallback for local testing
if not user_id:
    user_id = st.sidebar.text_input("User ID (Testing)", value="test_user")

st.sidebar.write(f"Logged in as: {user_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about HR policies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. POST REQUEST
    try:
        # Update with your new backend URL
        backend_url = "https://hr-chatbot-backendservice.azurewebsites.net/chat"
        payload = {"user_id": user_id, "question": prompt}
        
        res = requests.post(backend_url, json=payload, timeout=60)
        if res.status_code == 200:
            answer = res.json()["answer"]
            with st.chat_message("assistant"):
                st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.error(f"Error: {res.text}")
    except Exception as e:
        st.error(f"Connection Failed: {e}")