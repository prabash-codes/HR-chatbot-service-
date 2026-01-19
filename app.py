import streamlit as st
import requests

# Page Configuration
st.set_page_config(page_title="McLarens HR Assistant", page_icon="🏢", layout="centered")

# Custom Styling
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stApp { background-color: #0739a6; }
    </style>
""", unsafe_allow_html=True)

st.title("🏢 McLarens HR Assistant")
st.caption("Ask me anything about company policies, medical OPD, or leave procedures.")

# Sidebar for User Settings
with st.sidebar:
    st.header("Settings")
    user_id = st.text_input("User ID", value="ushara_test")
    if st.button("Clear Chat History"):
        st.session_state.messages = []

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display existing chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("How can I help you today?"):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call your FastAPI Backend
    with st.chat_message("assistant"):
        with st.spinner("Searching policies..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={"user_id": user_id, "question": prompt}
                )
                if response.status_code == 200:
                    answer = response.json().get("answer")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")