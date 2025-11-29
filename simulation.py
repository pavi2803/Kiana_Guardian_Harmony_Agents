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
    page_title="Guardian & Harmony Simulation Tasks",
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

import os
import json
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
        # send_email_alert(manager_emails, "Abnormal Health Alert", full_message)

        os.makedirs("data", exist_ok=True)  # make folder if it doesn't exist
        with open("data/abnormal_metrics.json", "w") as f:
            json.dump(abnormal_entries, f)

    else:
        st.info("No abnormal metrics detected.")
