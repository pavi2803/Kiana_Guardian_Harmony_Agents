import toml
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import os

# --- Page config ---
st.set_page_config(page_title="Guardian & Harmony", page_icon="🛡️", layout="centered")

# SECRET_FILE_PATH = "/etc/secrets/secret.toml"  # path where Render mounts it
SECRET_FILE_PATH = ".streamlit/secret.toml"  # path where Render mounts it

if not os.path.exists(SECRET_FILE_PATH):
    st.error("Secret file missing inside container. Check Render secret mount path.")
    st.stop()

try:
    secrets = toml.load(SECRET_FILE_PATH)
except Exception as e:
    st.error(f"Failed to load TOML: {e}")
    st.stop()


# secrets = toml.load(SECRET_FILE_PATH)

# --- Initialize Firebase ---
if not firebase_admin._apps:
    f = secrets["firebase"]
    cred_dict = dict(f)
    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# # --- Session state for page ---
# if "page" not in st.session_state:
#     st.session_state.page = "login"

# if "logged_in" not in st.session_state:
#     st.session_state.logged_in = False
#     st.session_state.user = None

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
# def meta_agent():
#     from llama_cpp import Llama
#     import google.generativeai as genai
#     import streamlit as st
#     from firebase_admin import firestore
#     from datetime import datetime, timedelta

#     llm = Llama(model_path="./models/tinyllama.gguf", n_ctx=512)

#     # --- Fetch last N abnormal metrics from Firestore ---
#     db = firestore.client()
#     max_entries = 5  # number of recent abnormal entries to include

#     # Assume you store abnormal metrics in collection "abnormal_metrics"
#     # and each document has fields: "date" (timestamp) and "entries" (list of strings)
#     abnormal_entries = []

#     try:
#         metrics_ref = db.collection("abnormal_metrics").order_by("date", direction=firestore.Query.DESCENDING).limit(max_entries).stream()
#         for doc in metrics_ref:
#             data = doc.to_dict()
#             entries = data.get("entries", [])
#             abnormal_entries.extend(entries)
#     except Exception as e:
#         st.warning(f"Could not fetch abnormal metrics from Firestore: {e}")

#     flat_entries = []

#     for entry in abnormal_entries[-max_entries:]:
#         if isinstance(entry, dict):
#             # Convert dict to string
#             flat_entries.append(", ".join(f"{k}: {v}" for k, v in entry.items()))
#         else:
#             flat_entries.append(str(entry))

#     truncated_context = "\n".join(flat_entries) if flat_entries else "No abnormal health metrics recorded."

#     # --- Prepare truncated RAG context ---
#     # truncated_context = "\n".join(abnormal_entries[-max_entries:]) if abnormal_entries else "No abnormal health metrics recorded."

#     if "messages" not in st.session_state:
#         st.session_state.messages = []

#     st.markdown("<h2 style='text-align:center;'>Meta Agent - What's on your mind?</h2>", unsafe_allow_html=True)

#     # Display previous messages
#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     if user_input := st.chat_input("Type your message here..."):
#         st.session_state.messages.append({"role": "user", "content": user_input})

#         # Prepare conversation prompt including RAG context
#         recent_messages = st.session_state.messages[-4:]
#         conversation_text = ""
#         for m in recent_messages:
#             if m["role"] == "user":
#                 conversation_text += f"### Instruction:\n{m['content']}\n### Response:\n"
#             else:
#                 conversation_text += f"{m['content']}\n"

#         prompt = truncated_context + "\n\n" + conversation_text

#         # Generate response
#         output = llm(prompt=prompt, max_tokens=200)
#         bot_reply = output['choices'][0]['text'].strip()
#         st.session_state.messages.append({"role": "assistant", "content": bot_reply})

#         with st.chat_message("assistant"):
#             st.markdown(bot_reply)

#     if st.button("Back to Dashboard"):
#         go_to_dashboard()


def meta_agent():
    from llama_cpp import Llama
    import streamlit as st
    from firebase_admin import firestore
    from datetime import datetime, timedelta

    llm = Llama(model_path="./models/tinyllama.gguf", n_ctx=512)

    db = firestore.client()
    max_entries = 5

    # --- Fetch abnormal metrics ---
    abnormal_entries = []
    try:
        metrics_ref = db.collection("abnormal_metrics").order_by("date", direction=firestore.Query.DESCENDING).limit(max_entries).stream()
        for doc in metrics_ref:
            data = doc.to_dict()
            entries = data.get("entries", [])
            abnormal_entries.extend(entries)
    except Exception as e:
        st.warning(f"Could not fetch abnormal metrics: {e}")

    # --- Fetch guardian evacuation routes ---
    guardian_entries = []
    try:
        guardian_ref = db.collection("guardian_routes").order_by("date", direction=firestore.Query.DESCENDING).limit(max_entries).stream()
        for doc in guardian_ref:
            data = doc.to_dict()
            routes = data.get("routes", [])
            guardian_entries.extend(routes)
    except Exception as e:
        st.warning(f"Could not fetch Guardian routes: {e}")

    # --- Flatten entries ---
    flat_abnormal = []
    for entry in abnormal_entries[-max_entries:]:
        if isinstance(entry, dict):
            flat_abnormal.append(", ".join(f"{k}: {v}" for k, v in entry.items()))
        else:
            flat_abnormal.append(str(entry))

    flat_guardian = []
    for entry in guardian_entries[-max_entries:]:
        if isinstance(entry, dict):
            flat_guardian.append(", ".join(f"{k}: {v}" for k, v in entry.items()))
        else:
            flat_guardian.append(str(entry))

    # --- Combine RAG context ---
    truncated_context = ""
    if flat_abnormal:
        truncated_context += "Abnormal Health Metrics:\n" + "\n".join(flat_abnormal) + "\n\n"
    if flat_guardian:
        truncated_context += "Guardian Evacuation Routes:\n" + "\n".join(flat_guardian)

    if not truncated_context:
        truncated_context = "No relevant metrics or routes recorded."

    # --- Streamlit chat interface ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown("<h2 style='text-align:center;'>Meta Agent - What's on your mind?</h2>", unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})

        recent_messages = st.session_state.messages[-4:]
        conversation_text = ""
        for m in recent_messages:
            if m["role"] == "user":
                conversation_text += f"### Instruction:\n{m['content']}\n### Response:\n"
            else:
                conversation_text += f"{m['content']}\n"

        prompt = truncated_context + "\n\n" + conversation_text
        output = llm(prompt=prompt, max_tokens=200)
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

    st.markdown("<h2 style='text-align:center;'> Key Metrics</h2>", unsafe_allow_html=True)
    employee_group = df.groupby("employee_name").mean(numeric_only=True)
    st.bar_chart(employee_group["spo2_percent"])
    st.bar_chart(employee_group["heart_rate_bpm"])

    st.markdown("<h2 style='text-align:center;'>Explore and Filter by Employee</h2>", unsafe_allow_html=True)
    selected_employee = st.selectbox("Select an employee:", df["employee_name"].unique())
    st.dataframe(df[df["employee_name"] == selected_employee])

    st.markdown("<h3 style='text-align:center;'>Health Composition Pie Chart</h3>", unsafe_allow_html=True)

    # Compute averages for the selected employee
    emp_df = df[df["employee_name"] == selected_employee]

    avg_spo2 = emp_df["spo2_percent"].mean()
    avg_sleep = emp_df["sleep_hours"].mean()
    avg_stress = emp_df["stress_level"].mean()

    # Pie chart data
    pie_labels = ["SpO₂ %", "Sleep Hours", "Stress Level"]
    pie_values = [avg_spo2, avg_sleep, avg_stress]

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.pie(pie_values, labels=pie_labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")

    st.pyplot(fig)

    if st.button("Open Meta Agent"):
        go_to_meta_agent()

# --- Login Page ---
# --- Initialize session state ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"  # default page is login

# --- Login Page ---
def login_page():
    st.markdown("<h2 style='text-align:center;'> 🛡️ Guardian and Harmony</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Login to your Dashboard</h3>", unsafe_allow_html=True)

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        users_ref = db.collection("users")
        query = users_ref.where("username", "==", username).stream()
        user_found = False
        for doc in query:
            user = doc.to_dict()
            if user.get("password") == password:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.page = "dashboard"
                st.success(f"Welcome {user['First_name']} {user['Last_name']}")
                user_found = True
                break
        if not user_found:
            st.error("❌ Invalid username or password")


# --- Page Router ---
if st.session_state.logged_in:
    if st.session_state.page == "dashboard":
        dashboard()
    elif st.session_state.page == "meta_agent":
        meta_agent()
else:
    login_page()
