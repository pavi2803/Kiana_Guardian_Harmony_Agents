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

    
    

st.markdown("<h2 style='text-align:center;'>Harmony Agent</h2>", unsafe_allow_html=True)

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
        st.success(f"Email sent to Health Department Managers")

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


#----------------GUARDIAN --------------------

import numpy as np

def load_guardian_data():
    df = pd.read_csv("mustering_person_level.csv")  
    # df["ts"] = pd.to_datetime(df["ts"])
    df['ts'] = pd.to_datetime(df['ts'], format='ISO8601')
    return df

def get_muster_points(df):
    muster_df = (
        df[["nearest_muster_name", "nearest_muster_lat", "nearest_muster_lon", "zone_name"]]
        .drop_duplicates()
        .rename(columns={
            "nearest_muster_name": "muster_name",
            "nearest_muster_lat": "muster_lat",
            "nearest_muster_lon": "muster_lon",
            "zone_name": "muster_zone"
        })
    )
    return muster_df


def get_latest_positions(df):
    # Sort by timestamp and take the latest row per macid
    df_sorted = df.sort_values("ts")
    latest = df_sorted.groupby("macid").tail(1)
    return latest


from math import radians, sin, cos, asin, sqrt

def haversine(lat1, lon1, lat2, lon2):
    # all args in degrees, returns distance in meters
    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c

def send_guardian_email(routes_df, unsafe_zones):
    subject = "Guardian Evacuation Plan - Optimal Routes"

    summary_lines = []
    summary_lines.append(f"Unsafe zones: {', '.join(unsafe_zones)}\n")
    summary_lines.append("Evacuation instructions by origin zone:\n")

    # Group by origin zone → assigned zone
    zone_routes = routes_df.groupby(
        ["current_zone", "assigned_muster_zone"]
    ).agg(
        avg_distance=("distance_m", "mean")
    ).reset_index()

    # For each origin zone, list all assigned targets
    for origin_zone in sorted(zone_routes["current_zone"].dropna().unique()):
        summary_lines.append(f"Optimal paths from {origin_zone}:")
        targets = zone_routes[zone_routes["current_zone"] == origin_zone]

        for _, row in targets.iterrows():
            target = row["assigned_muster_zone"] if pd.notna(row["assigned_muster_zone"]) else "Unknown"
            distance = f"{int(row['avg_distance'])} m" if pd.notna(row["avg_distance"]) else "unknown"
            summary_lines.append(f"  - {target} (~{distance})")
        summary_lines.append("")  # empty line for spacing

    body = "\n".join(summary_lines)

    manager_emails = st.secrets["email"]["manager_emails"]

    send_email_alert(
        to_emails=manager_emails,
        subject=subject,
        body=body,
    )
    st.success(f"Evacuation Plan - Optimal Routes Info Sent")


def compute_evacuation_routes(evac_df, unsafe_zones):

    evac_df = evac_df.dropna(subset=["lat", "lon", "zone_name", "macid"])
    latest = get_latest_positions(evac_df)
    muster_df = get_muster_points(evac_df)

    # Clean muster df
    muster_df = muster_df.dropna(subset=["muster_lat", "muster_lon", "muster_zone"])


    # # evac_df = full dataset with 670k rows
    # latest = get_latest_positions(evac_df)  # one row per macid
    # muster_df = get_muster_points(evac_df)

    # Filter muster points to only safe zones
    safe_musters = muster_df[~muster_df["muster_zone"].isin(unsafe_zones)].reset_index(drop=True)
    if safe_musters.empty:
        st.error("No safe muster zones available. Please adjust unsafe zones.")
        return None

    # For each person, compute distance to each safe muster and choose minimum
    assignments = []

    for _, row in latest.iterrows():
        macid = row["macid"]
        cur_zone = row["zone_name"]
        cur_lat = row["lat"]
        cur_lon = row["lon"]

        if pd.isna(cur_lat) or pd.isna(cur_lon):
            assignments.append({
                "macid": macid,
                "current_zone": cur_zone,
                "assigned_muster_name": "No valid position",
                "assigned_muster_zone": "Unknown",
                "distance_m": np.nan
            })
            continue

        # Distance to SAFE muster zones
        dists = haversine(
            cur_lat,
            cur_lon,
            safe_musters["muster_lat"].values,
            safe_musters["muster_lon"].values,
        )

        # If all distances NaN → all invalid or out of bounds
        if np.isnan(dists).all():
            assignments.append({
                "macid": macid,
                "current_zone": cur_zone,
                "assigned_muster_name": "No reachable safe muster",
                "assigned_muster_zone": "None",
                "distance_m": np.nan
            })
            continue

        idx_min = int(np.nanargmin(dists))
        best_muster = safe_musters.iloc[idx_min]

        assignments.append({
            "macid": macid,
            "current_zone": cur_zone,
            "current_lat": cur_lat,
            "current_lon": cur_lon,
            "assigned_muster_name": best_muster["muster_name"],
            "assigned_muster_zone": best_muster["muster_zone"],
            "muster_lat": best_muster["muster_lat"],
            "muster_lon": best_muster["muster_lon"],
            "distance_m": float(dists[idx_min]),
        })

    routes_df = pd.DataFrame(assignments)
    return routes_df

df = load_guardian_data()


def save_guardian_routes_to_firestore(routes_df):
    # --- Save locally ---
    os.makedirs("data", exist_ok=True)
    local_path = "data/guardian_routes.json"
    routes_df.to_json(local_path, orient="records", indent=2)

    # --- Save to Firestore ---
    collection_ref = db.collection("guardian_routes")
    today_str = datetime.today().strftime("%Y-%m-%d")

    # Convert DataFrame to list of dicts for Firestore
    routes_list = routes_df.to_dict(orient="records")

    # Check if today's entry already exists
    existing = collection_ref.where("date", "==", today_str).get()
    if not existing:
        collection_ref.add({
            "date": today_str,
            "routes": routes_list
        })
        st.success("Guardian routes saved to database and locally.")
    else:
        st.info("Guardian routes for today already exist in the database.")

st.markdown("<h2 style='text-align:center;'>Guardian: Evacuation Routes</h2>", unsafe_allow_html=True)
    # Let user choose which zones are unsafe
all_zones = sorted(df["zone_name"].dropna().unique())
unsafe_zones = st.multiselect("Select unsafe zones (fire, oil leak, etc.):", all_zones)

if st.button("Run Guardian Simulation"):
    if not unsafe_zones:
        st.warning("Select at least one unsafe zone to run Guardian simulation.")
    else:
        evac_routes = compute_evacuation_routes(df, unsafe_zones)

        if evac_routes is not None:
            st.success("Guardian evacuation routes computed.")

            # --- Save full routes locally (optional) ---
            os.makedirs("data", exist_ok=True)
            evac_routes.to_csv("data/evacuation_routes.csv", index=False)

            save_guardian_routes_to_firestore(evac_routes)

            # --- Send zone-level email summary only ---
            send_guardian_email(evac_routes, unsafe_zones)