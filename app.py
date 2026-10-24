"""
Streamlit Web Dashboard for Job Hunt Autopilot.
Track every application. Catch every fake offer.
"""

import os
import sys
from datetime import datetime, timezone

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import streamlit as st
import pandas as pd

from job_autopilot.models import StageEnum
from job_autopilot.parser import load_inbox, load_from_json, load_from_mbox
from job_autopilot.classifier import classify_email
from job_autopilot.tracker import JobHuntTracker

# Streamlit Page Configuration
st.set_page_config(
    page_title="Job Hunt Autopilot",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for High Contrast and Red Scam Highlights
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .scam-alert-box {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
    }
    .badge-scam {
        background-color: #dc2626;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .badge-offer {
        background-color: #16a34a;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .badge-interview {
        background-color: #0284c7;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .badge-applied {
        background-color: #64748b;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
    }
    .badge-rejected {
        background-color: #475569;
        color: #cbd5e1;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
    }
    .followup-box {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/isometric/100/airplane-take-off.png", width=64)
st.sidebar.title("Job Hunt Autopilot")
st.sidebar.caption("Track every application. Catch every fake offer.")

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Inbox Source")

data_source = st.sidebar.radio(
    "Choose Data Source:",
    ["Sample Inbox (JSON)", "Sample Inbox (.mbox)", "Upload Custom File"],
    index=0
)

uploaded_file = None
if data_source == "Upload Custom File":
    uploaded_file = st.sidebar.file_uploader(
        "Upload .json or .mbox file",
        type=["json", "mbox", "eml"]
    )

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Demo Story Context")
st.sidebar.info(
    "**Candidate:** Alex Chen (Full Stack Engineer)\n\n"
    "**Situation:** Impacted by tech layoffs 14 days ago. Applied to 20+ roles across tech startups, "
    "FAANG, and remote job boards.\n\n"
    "**Challenge:** Sifting genuine leads from predatory scammers targeting vulnerable job seekers."
)

st.sidebar.markdown("---")
reference_date_choice = st.sidebar.date_input(
    "Reference Date (for 7-day follow-up calc):",
    value=datetime(2026, 10, 24).date()
)
ref_datetime = datetime.combine(reference_date_choice, datetime.min.time()).replace(tzinfo=timezone.utc)

# Load emails
json_sample_path = os.path.join(ROOT_DIR, "data", "sample_inbox.json")
mbox_sample_path = os.path.join(ROOT_DIR, "data", "sample_inbox.mbox")

emails = []
if data_source == "Sample Inbox (JSON)":
    emails = load_from_json(json_sample_path)
elif data_source == "Sample Inbox (.mbox)":
    emails = load_from_mbox(mbox_sample_path)
elif uploaded_file is not None:
    content = uploaded_file.read()
    if uploaded_file.name.endswith(".json"):
        emails = load_from_json(content)
    else:
        emails = load_from_mbox(content)
else:
    st.warning("Please upload a file or switch to sample data.")
    st.stop()

# Run Pipeline
tracker = JobHuntTracker(reference_date=ref_datetime)
records = tracker.process_emails(emails)
stats = tracker.get_stats()

# Header Area
st.title("✈️ Job Hunt Autopilot")
st.markdown(
    "**Unified Post-Layoff Job Pipeline:** Automatically tracks applications, schedules 7-day follow-ups, "
    "and intercepts predatory scam offers asking for fees or sensitive documents."
)

# Top Metrics Row
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Total Emails", stats.total_emails)
with c2:
    st.metric("Applications", stats.total_applications)
with c3:
    st.metric("💬 Interviews", stats.interviews_scheduled)
with c4:
    st.metric("🎉 Legit Offers", stats.offers_received)
with c5:
    st.metric("⏰ Follow-ups Due", stats.follow_ups_due)
with c6:
    st.metric("🚨 Fake Offers Flagged", stats.scams_flagged, delta="BLOCKED", delta_color="inverse")

st.markdown("---")

# Main Content Tabs
tab_scam, tab_followup, tab_tracker, tab_reader, tab_export = st.tabs([
    f"🚨 Fake Offers Flagged ({stats.scams_flagged})",
    f"⏰ 7-Day Follow-Up Due ({stats.follow_ups_due})",
    "📋 Application Pipeline Tracker",
    "🔍 Email Deep Dive",
    "💾 Export & Reporting"
])

# ----------------- TAB 1: SCAM RADAR -----------------
with tab_scam:
    st.subheader("🚨 Scam Radar: Caught Fake Offers & Predatory Traps")
    st.error(
        f"**Safety Alert:** {stats.scams_flagged} fraudulent emails detected targeting your job hunt. "
        "These schemes mimic real recruiters to steal money, personal identity (SSN/Aadhaar), or execute check-cashing fraud."
    )

    scam_records = [r for r in records if r.is_scam]
    for s in scam_records:
        with st.container():
            st.markdown(f"""
            <div class="scam-alert-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4 style="color:#b91c1c; margin:0;">🚫 Fake Offer Intercepted: {s.company} ({s.role})</h4>
                    <span class="badge-scam">SCAM BLOCKED</span>
                </div>
                <p style="margin-top:6px; margin-bottom:8px; color:#4b5563; font-size:0.9rem;">
                    <strong>Sender:</strong> <code>{s.sender_email or s.sender}</code> &nbsp;|&nbsp; 
                    <strong>Date:</strong> {s.application_date.strftime("%B %d, %Y")}
                </p>
                <div style="background-color:#ffffff; padding:12px; border-radius:6px; border:1px solid #fecaca;">
                    <strong style="color:#991b1b;">Why this was flagged:</strong>
                    <ul style="margin:4px 0 0 16px; color:#7f1d1d; font-size:0.92rem;">
                        {"".join([f"<li>{r}</li>" for r in s.scam_reasons])}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"View Raw Fraudulent Email ({s.latest_subject})"):
                st.write(f"**Subject:** {s.latest_subject}")
                st.text(s.raw_body)
                st.warning("⚠️ Recommendation: Report to FTC/Cyber Crime and DO NOT wire money or provide identity documents.")

# ----------------- TAB 2: 7-DAY FOLLOW-UP -----------------
with tab_followup:
    st.subheader("⏰ Follow-Up Radar: Applications Silent for 7+ Days")
    st.info(
        "Recruiters are busy. Following up after 7 days of silence dramatically increases interview conversion rates "
        "without being perceived as aggressive."
    )

    follow_up_records = [r for r in records if r.follow_up_due]
    if not follow_up_records:
        st.success("All applications are currently active or within their initial 7-day window.")
    else:
        for fu in follow_up_records:
            st.markdown(f"""
            <div class="followup-box">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h4 style="margin:0; color:#92400e;">🏢 {fu.company} — {fu.role}</h4>
                    <span style="background-color:#d97706; color:white; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.8rem;">
                        {fu.days_elapsed} DAYS OF SILENCE (THRESHOLD: 7d)
                    </span>
                </div>
                <p style="margin:6px 0; font-size:0.88rem; color:#78350f;">
                    Applied on <strong>{fu.application_date.strftime('%b %d, %Y')}</strong>. Recruiter: <code>{fu.sender_email or fu.sender}</code>
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"✉️ 1-Click Follow-Up Template for {fu.company}"):
                st.text_area(
                    label="Ready-to-send email draft:",
                    value=fu.follow_up_template,
                    height=200,
                    key=f"fu_area_{fu.id}"
                )
                st.caption("Tip: You can copy and paste this directly into your email client.")

# ----------------- TAB 3: COMPLETE PIPELINE -----------------
with tab_tracker:
    st.subheader("📋 Application Pipeline Tracker")
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        stage_filter = st.selectbox(
            "Filter by Stage:",
            ["All Stages", "Legit Offers", "Active Interviews", "Applied / Pending", "Rejected", "Scams Flagged"]
        )
    with col_filter2:
        search_query = st.text_input("Search company or role:", "")

    filtered = records
    if stage_filter == "Legit Offers":
        filtered = [r for r in filtered if r.current_stage == StageEnum.OFFER]
    elif stage_filter == "Active Interviews":
        filtered = [r for r in filtered if r.current_stage == StageEnum.INTERVIEW]
    elif stage_filter == "Applied / Pending":
        filtered = [r for r in filtered if r.current_stage == StageEnum.APPLIED]
    elif stage_filter == "Rejected":
        filtered = [r for r in filtered if r.current_stage == StageEnum.REJECTED]
    elif stage_filter == "Scams Flagged":
        filtered = [r for r in filtered if r.current_stage == StageEnum.SCAM]

    if search_query:
        q = search_query.lower()
        filtered = [r for r in filtered if q in r.company.lower() or q in r.role.lower()]

    table_data = []
    for r in filtered:
        status_label = ""
        if r.current_stage == StageEnum.OFFER:
            status_label = "🎉 Formal Offer"
        elif r.current_stage == StageEnum.INTERVIEW:
            status_label = "💬 Screen / Loop Active"
        elif r.current_stage == StageEnum.REJECTED:
            status_label = "Archived"
        elif r.current_stage == StageEnum.SCAM:
            status_label = "🚨 BLOCKED SCAM"
        elif r.current_stage == StageEnum.APPLIED:
            status_label = f"⚠️ Follow-up Due ({r.days_elapsed}d)" if r.follow_up_due else f"In Review ({r.days_elapsed}d)"

        table_data.append({
            "Stage": r.current_stage.value.upper(),
            "Company": r.company,
            "Role": r.role,
            "Date": r.application_date.strftime("%Y-%m-%d"),
            "Days Elapsed": r.days_elapsed,
            "Status": status_label,
            "Sender": r.sender_email or r.sender
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ----------------- TAB 4: EMAIL READER -----------------
with tab_reader:
    st.subheader("🔍 Email Deep Dive & Classification Explainability")
    
    email_titles = [f"{idx+1}. [{r.current_stage.value.upper()}] {r.company} - {r.latest_subject[:45]}" for idx, r in enumerate(records)]
    selected_idx = st.selectbox("Select an email to inspect:", range(len(records)), format_func=lambda i: email_titles[i])

    selected_rec = records[selected_idx]

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.write(f"**Company:** {selected_rec.company}")
        st.write(f"**Role:** {selected_rec.role}")
        st.write(f"**Stage Classified:** `{selected_rec.current_stage.value}`")
    with col_meta2:
        st.write(f"**Sender:** `{selected_rec.sender}`")
        st.write(f"**Date:** {selected_rec.application_date.strftime('%Y-%m-%d %H:%M UTC')}")
        st.write(f"**Days Elapsed:** {selected_rec.days_elapsed} days")

    st.markdown("#### Message Subject:")
    st.code(selected_rec.latest_subject, language="text")

    st.markdown("#### Email Body:")
    st.text_area("", value=selected_rec.raw_body, height=220, disabled=True)

    if selected_rec.is_scam:
        st.error(f"🚨 **Scam Reasons Detected:**\n" + "\n".join([f"- {r}" for r in selected_rec.scam_reasons]))

# ----------------- TAB 5: EXPORT -----------------
with tab_export:
    st.subheader("💾 Export Application Tracker")
    st.write("Export your unified tracking database to CSV or JSON format for your records or spreadsheet tools.")

    export_rows = [{
        "id": r.id,
        "company": r.company,
        "role": r.role,
        "stage": r.current_stage.value,
        "days_elapsed": r.days_elapsed,
        "follow_up_due": r.follow_up_due,
        "is_scam": r.is_scam,
        "scam_reasons": " | ".join(r.scam_reasons),
        "application_date": r.application_date.isoformat(),
        "latest_subject": r.latest_subject,
        "sender": r.sender_email or r.sender
    } for r in records]

    export_df = pd.DataFrame(export_rows)

    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Tracker as CSV",
            data=csv_data,
            file_name="job_hunt_autopilot_tracker.csv",
            mime="text/csv"
        )
    with c_dl2:
        import json
        json_str = json.dumps(export_rows, indent=2).encode("utf-8")
        st.download_button(
            label="📥 Download Tracker as JSON",
            data=json_str,
            file_name="job_hunt_autopilot_tracker.json",
            mime="application/json"
        )
