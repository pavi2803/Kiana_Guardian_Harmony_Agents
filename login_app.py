import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText

# --- Page config ---
st.set_page_config(page_title="Guardian & Harmony", page_icon="🛡️", layout="centered")

# --- Initialize Firebase ---
if not firebase_admin._apps:
    f = st.secrets["firebase"]
    cred_dict = dict(f)
    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Session state for page ---
if "page" not in st.session_state:
    st.session_state.page = "login"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# --- Page Navigation Functions ---
def go_to_dashboard():
    st.session_state.page = "dashboard"

def go_to_meta_agent():
    st.session_state.page = "meta_agent"

def logout():
    st.session_state.page = "login"
    st.session_state.logged_in = False
    st.session_state.user = None

# --- Meta Agent Function ---
def meta_agent():
    from llama_cpp import Llama
    import google.generativeai as genai
    import json
    import os

    llm = Llama(model_path="./models/tinyllama.gguf", n_ctx=512)

    try:
        with open("data/abnormal_metrics.json") as f:
            abnormal_metrics = json.load(f)
    except FileNotFoundError:
        abnormal_metrics = []

    # Combine abnormal metrics into a single context string
    context = "\n".join(abnormal_metrics) if abnormal_metrics else "No abnormal health metrics recorded."

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown("<h2 style='text-align:center;'>Meta Agent - What's on your mind?</h2>", unsafe_allow_html=True)

    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


    if user_input := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Prepare conversation prompt including RAG context
        conversation_text = f"### Context from Health Metrics:\n{context}\n\n"
        for m in st.session_state.messages:
            if m["role"] == "user":
                conversation_text += f"### Instruction:\n{m['content']}\n### Response:\n"
            else:
                conversation_text += f"{m['content']}\n"

        # Generate response
        output = llm(prompt=conversation_text, max_tokens=200)
        bot_reply = output['choices'][0]['text'].strip()
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

        with st.chat_message("assistant"):
            st.markdown(bot_reply)

    if st.button("Back to Dashboard"):
        go_to_dashboard()


# --- Dashboard Function ---
def dashboard():
    @st.cache_data
    def load_data():
        df = pd.read_csv("health_metrics.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df

    df = load_data()

    st.markdown("<h2 style='text-align:center;'>🔎 Key Metrics</h2>", unsafe_allow_html=True)
    employee_group = df.groupby("employee_name").mean(numeric_only=True)
    st.bar_chart(employee_group["spo2_percent"])
    st.bar_chart(employee_group["heart_rate_bpm"])

    st.markdown("<h2 style='text-align:center;'>Explore and Filter by Employee</h2>", unsafe_allow_html=True)
    selected_employee = st.selectbox("Select an employee:", df["employee_name"].unique())
    st.dataframe(df[df["employee_name"] == selected_employee])

    if st.button("Open Meta Agent"):
        go_to_meta_agent()

# --- Login Page ---
def login_page():
    st.markdown("<h3 style='text-align:center;'>Login to your Dashboard</h3>", unsafe_allow_html=True)
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")
    if st.button("Login"):
        users_ref = db.collection("users")
        query = users_ref.where("username", "==", username).stream()
        for doc in query:
            user = doc.to_dict()
            if user.get("password") == password:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.page = "dashboard"
                st.success(f"Welcome {user['First_name']} {user['Last_name']}")
                return
        st.error("❌ Invalid username or password")

# --- Page Router ---
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "dashboard":
    dashboard()
elif st.session_state.page == "meta_agent":
    meta_agent()
