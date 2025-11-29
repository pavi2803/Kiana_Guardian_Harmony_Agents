# login_app.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import smtplib
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Page config ---
st.set_page_config(
    page_title="Guardian & Harmony",
    page_icon="🛡️",
    layout="centered",
)

# --- Harmony Simulation Button ---
st.markdown("---")
# st.subheader("Harmony Simulation: Abnormal Health Detection")

def send_email_alert(to_emails, subject, body):
    from_email = st.secrets["email"]["from_email"]
    password = st.secrets["email"]["password"]

    # Make sure to_emails is a list
    if isinstance(to_emails, str):
        to_emails = [to_emails]

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ", ".join(to_emails)  

    # Send all in one go
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(from_email, password)
    server.sendmail(from_email, to_emails, msg.as_string())  
    server.quit()

    
    st.success(f"Email sent to Health Department Managers.")


if st.button("Run Harmony Simulation"):
    df = pd.read_csv("health_metrics.csv")
    manager_emails = st.secrets["email"]["manager_emails"]

    abnormal_entries = []
    for _, row in df.iterrows():
        hr = row['heart_rate_bpm']
        temp = row['body_temperature_c']
        o2 = row['spo2_percent']

        if hr < 50 or hr > 105 or temp < 33 or temp > 40 or o2<92:
            abnormal_entries.append(
                f"Employee {row['employee_id']} ({row['employee_name']}): "
                f"Heart Rate={hr} BPM, Temp={temp}°C, Oxygen Level ={o2}%"
            )

    if abnormal_entries:
        full_message = "Abnormal Health Metrics Detected:\n\n" + "\n".join(abnormal_entries)
        send_email_alert(manager_emails, "Abnormal Health Alert", full_message)
    else:
        st.info("No abnormal metrics detected.")




def dashboard():
    import smtplib
    from email.mime.text import MIMEText
    import pandas as pd

    import streamlit as st
    import pandas as pd
    import matplotlib.pyplot as plt

    @st.cache_data
    def load_data():
        
        df = pd.read_csv("health_metrics.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df

    # 1. Load data
    df = load_data()

    # 2. KPI Section
    st.markdown("<h2 style='color:#000000; text-align:center;'>🔎 Key Metrics</h2>", unsafe_allow_html=True)

    # 3. Employee-level Average Metrics (replacing the old zone-wise section)
    st.markdown("<h3 style='color:#000000; text-align:center;'>Employee Wise Health Metrics</h3>", unsafe_allow_html=True)
    employee_group = df.groupby("employee_name").mean(numeric_only=True)

    st.markdown("<h3 style='color:#000000; text-align:center;'>Average SpO2 by Employee</h3>", unsafe_allow_html=True)
    st.bar_chart(employee_group["spo2_percent"])

    st.markdown("<h3 style='color:#000000; text-align:center;'>Average Heart Rate By Employee</h3>", unsafe_allow_html=True)
    st.bar_chart(employee_group["heart_rate_bpm"])

    # 4. Distribution Charts
    st.markdown("<h2 style='color:#000000; text-align:center;'>Distribution Charts</h2>", unsafe_allow_html=True)

    # Stress Level Distribution
    st.markdown("<h2 style='color:#000000; text-align:center;'>Stress Level Distribution</h2>", unsafe_allow_html=True)
    stress_counts = df["stress_level"].value_counts().sort_index()
    fig1, ax1 = plt.subplots()
    ax1.pie(stress_counts, labels=stress_counts.index, autopct="%1.1f%%")
    ax1.set_title("Stress Levels")
    st.pyplot(fig1)

    # Sleep Hours Distribution (bucketed ranges)
    st.markdown("<h2 style='color:#000000; text-align:center;'>Sleep hours Distribution</h2>", unsafe_allow_html=True)
    sleep_category = pd.cut(
        df["sleep_hours"],
        bins=[0, 5, 7, 9, 24],
        labels=["<5h", "5–7h", "7–9h", "9h+"],
        include_lowest=True
    )
    sleep_counts = sleep_category.value_counts().sort_index()
    fig2, ax2 = plt.subplots()
    ax2.pie(sleep_counts, labels=sleep_counts.index, autopct="%1.1f%%")
    ax2.set_title("Sleep Hours Categories")
    st.pyplot(fig2)

    # 5. Filter + Detailed Table (filter by employee)
    st.markdown("<h2 style='color:#000000; text-align:center;'>Explore and Filter by Employee </h2>", unsafe_allow_html=True)
    selected_employee = st.selectbox("Select an employee:", df["employee_name"].unique())
    st.dataframe(df[df["employee_name"] == selected_employee])


# --- Initialize Firebase only once ---
if not firebase_admin._apps:
    f = st.secrets["firebase"]

    # Make a mutable copy and fix newlines
    cred_dict = dict(f)
    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()


st.markdown(
    "<h1 style='color:#000000; text-align:center;'>🛡️ Guardian and Harmony</h1>",
    unsafe_allow_html=True
)

# --- Page style ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5f5f5;
        font-family: 'Helvetica', sans-serif;
    }
    .login-box {
        background-color: #f0f0f0;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        height: 3em;
        width: 100%;
        border-radius: 8px;
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def authenticate_user(username, password):
    users_ref = db.collection("users")
    query = users_ref.where("username", "==", username).stream()
    for doc in query:
        user = doc.to_dict()
        if user.get("password") == password:
            return user
    return None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user"] = None


def logout():
    st.session_state["logged_in"] = False
    st.session_state["user"] = None

# Check if user is logged in
if st.session_state["logged_in"]:
    # Show dashboard
    dashboard()

    if st.button("Logout"):
        logout()
else:
    # Show login form
    st.markdown("<h3 style='color:#000000; text-align:center;'> Login to your Dashboard</h3>", unsafe_allow_html=True)
    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state["logged_in"] = True
            st.session_state["user"] = user
            st.success(f"Welcome {user['First_name']} {user['Last_name']}")
        else:
            st.error("❌ Invalid username or password")


