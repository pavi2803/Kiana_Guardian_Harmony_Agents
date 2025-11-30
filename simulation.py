import os
import json
from datetime import datetime
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText

# --- Initialize Firebase ---
if not firebase_admin._apps:
    f = st.secrets["firebase"]
    cred_dict = dict(f)
    cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()


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

        if hr < 50 or hr > 105 or temp < 33 or temp > 40 or o2 < 92:
            abnormal_entries.append({
                "employee_id": row['employee_id'],
                "employee_name": row['employee_name'],
                "heart_rate_bpm": hr,
                "temperature_c": temp,
                "spo2_percent": o2,
                "date": str(row['date'])
            })

    if abnormal_entries:
        full_message = "Abnormal Health Metrics Detected:\n\n" + \
                       "\n".join([f"{e['employee_name']} HR={e['heart_rate_bpm']} Temp={e['temperature_c']} O2={e['spo2_percent']}" for e in abnormal_entries])
        
        send_email_alert(manager_emails, "Abnormal Health Alert", full_message)

        # --- Save locally ---
        os.makedirs("data", exist_ok=True)
        with open("data/abnormal_metrics.json", "w") as f:
            json.dump(abnormal_entries, f, indent=2)

        # --- Save to Firestore ---
        collection_ref = db.collection("abnormal_metrics")
        today_str = datetime.today().strftime("%Y-%m-%d")

        # Check if today's entry already exists
        existing = collection_ref.where("date", "==", today_str).get()
        if not existing:
            collection_ref.add({
                "date": today_str,
                "entries": abnormal_entries
            })
            st.success("Abnormal metrics saved to database and locally.")
        else:
            st.info("Metrics for today already exist in the database.")

    else:
        st.info("No abnormal metrics detected.")
