import streamlit as st
import requests
import pandas as pd
import threading
import time
import uuid
import os
import sys

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="EmoTrace – Mental Health Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark background */
.stApp {
    background: linear-gradient(135deg, #0d0d1a 0%, #1a0a2e 50%, #0d1a2e 100%);
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(15, 10, 30, 0.95);
    border-right: 1px solid rgba(124, 58, 237, 0.3);
}
[data-testid="stSidebar"] .stMarkdown { color: #a78bfa; }

/* Glassmorphism cards */
.glass-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
    backdrop-filter: blur(10px);
}

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, rgba(124,58,237,0.15), rgba(16,185,129,0.1));
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-value { font-size: 2.4rem; font-weight: 800; color: #a78bfa; }
.metric-label { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }

/* Risk badge */
.risk-low    { background: rgba(16,185,129,0.2);  border: 1px solid #10b981; color:#10b981; border-radius:8px; padding:6px 16px; display:inline-block; }
.risk-mild   { background: rgba(251,191,36,0.2);  border: 1px solid #fbbf24; color:#fbbf24; border-radius:8px; padding:6px 16px; display:inline-block; }
.risk-mod    { background: rgba(249,115,22,0.2);  border: 1px solid #f97316; color:#f97316; border-radius:8px; padding:6px 16px; display:inline-block; }
.risk-elev   { background: rgba(239,68,68,0.2);   border: 1px solid #ef4444; color:#ef4444; border-radius:8px; padding:6px 16px; display:inline-block; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
    transition: all 0.3s ease;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(124,58,237,0.45);
}

/* Input fields */
.stTextInput > div > div > input, .stSelectbox > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(124,58,237,0.35) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* Section header */
.section-header {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a78bfa, #60a5fa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}
.section-sub { color: #94a3b8; margin-bottom: 24px; font-size: 0.95rem; }

/* Progress bar */
.stProgress > div > div > div { background: linear-gradient(90deg, #7c3aed, #10b981) !important; }

/* Alert */
.stAlert { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE INIT ───────────────────────────────────────────────────────
for key, default in {
    "authenticated": False,
    "token": None,
    "email": None,
    "otp_sent": False,
    "chatbot_score": None,
    "session_summary": None,
    "chatbot_running": False,
    "eye_running": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def api_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def risk_badge(level):
    cls = {"Low": "risk-low", "Mild": "risk-mild", "Moderate": "risk-mod", "Elevated": "risk-elev"}.get(level, "risk-low")
    return f'<span class="{cls}">⚠ {level} Risk</span>'


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧠 EmoTrace")
        st.markdown("*Temporal Behavioral Analysis*")
        st.divider()

        if st.session_state.authenticated:
            st.success(f"✅ {st.session_state.email}")
            st.divider()
            pages = {
                "🏠 Dashboard": "dashboard",
                "🎙️ Voice Chatbot": "chatbot",
                "👁️ Behavioral Analysis": "eye",
                "🔍 Face Detection": "face",
            }
            if "page" not in st.session_state:
                st.session_state.page = "dashboard"

            for label, key in pages.items():
                if st.button(label, key=f"nav_{key}"):
                    st.session_state.page = key
                    st.rerun()

            st.divider()
            if st.button("🚪 Logout"):
                for k in ["authenticated", "token", "email", "otp_sent", "chatbot_score", "session_summary", "page"]:
                    st.session_state[k] = False if k == "authenticated" else None
                st.rerun()
        else:
            st.info("Please login to continue.")


# ─── AUTH PAGE ────────────────────────────────────────────────────────────────
def page_auth():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<p class="section-header">🧠 EmoTrace</p>', unsafe_allow_html=True)
        st.markdown('<p class="section-sub">Temporal Behavioral Analysis for Early Mental Risk Detection</p>', unsafe_allow_html=True)

        email = st.text_input("📧 Email Address", placeholder="your@email.com", key="auth_email")

        if not st.session_state.otp_sent:
            if st.button("📨 Send OTP"):
                if email:
                    try:
                        r = requests.post(f"{API_BASE}/auth/send-otp", json={"email": email}, timeout=10)
                        if r.status_code == 200:
                            st.session_state.otp_sent = True
                            st.session_state.email = email
                            st.success("✅ OTP sent! Check your email.")
                            st.rerun()
                        else:
                            st.error(f"Failed: {r.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"⚠️ Cannot reach API server. Is it running?\n\n`{e}`")
                else:
                    st.warning("Please enter your email first.")
        else:
            otp = st.text_input("🔑 Enter OTP", max_chars=6, placeholder="6-digit code", key="auth_otp")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Verify OTP"):
                    if otp:
                        try:
                            r = requests.post(f"{API_BASE}/auth/verify-otp", json={"email": st.session_state.email, "otp": otp}, timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.authenticated = True
                                st.session_state.page = "dashboard"
                                st.success("🎉 Logged in!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid or expired OTP.")
                        except Exception as e:
                            st.error(f"API Error: {e}")
                    else:
                        st.warning("Enter the OTP first.")
            with col_b:
                if st.button("🔄 Resend OTP"):
                    st.session_state.otp_sent = False
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown('<p class="section-header">🏠 Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="section-sub">Welcome back, <b>{st.session_state.email}</b></p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        score = st.session_state.chatbot_score
        st.markdown(f'''<div class="metric-card">
            <div class="metric-value">{round(score,2) if score else "—"}</div>
            <div class="metric-label">🎙️ Chatbot Score</div>
        </div>''', unsafe_allow_html=True)

    with col2:
        summary = st.session_state.session_summary
        mri = round(summary["mental_risk_score"], 1) if summary else "—"
        st.markdown(f'''<div class="metric-card">
            <div class="metric-value">{mri}</div>
            <div class="metric-label">👁️ Mental Risk Score</div>
        </div>''', unsafe_allow_html=True)

    with col3:
        risk = summary["dominant_risk"] if summary else "—"
        st.markdown(f'''<div class="metric-card">
            <div class="metric-value" style="font-size:1.5rem;">{risk}</div>
            <div class="metric-label">⚠️ Dominant Risk</div>
        </div>''', unsafe_allow_html=True)

    st.divider()

    if st.session_state.session_summary:
        summary = st.session_state.session_summary
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Latest Session Report")
        st.markdown(f"**Recommendation:** {summary['recommendation']}")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Avg Blink Rate", f"{summary['avg_blink_rate']} /min")
        col_b.metric("Eye Engagement (EAR)", summary['avg_eye_engagement'])
        col_c.metric("Facial Activity", summary['avg_facial_activity'])

        risk_df = pd.DataFrame(
            list(summary["risk_distribution"].items()),
            columns=["Risk Level", "Percentage"]
        )
        st.bar_chart(risk_df.set_index("Risk Level"))
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.info("👉 Run the **Voice Chatbot** and **Behavioral Analysis** to populate your dashboard.")
        st.markdown('</div>', unsafe_allow_html=True)


# ─── CHATBOT PAGE ─────────────────────────────────────────────────────────────
def page_chatbot():
    st.markdown('<p class="section-header">🎙️ Voice Chatbot</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Answer spoken mental health questions. Ensure your microphone is connected.</p>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    age_group = st.selectbox("Select Age Group", ["under18", "youth", "adult"], key="age_group_select",
                              format_func=lambda x: {"under18": "Under 18", "youth": "Youth (18–25)", "adult": "Adult (25+)"}[x])

    st.info("ℹ️ After clicking **Start**, a voice session will begin. Answer each spoken question out loud. The session completes automatically after all questions.")

    if st.session_state.chatbot_score is not None:
        score = st.session_state.chatbot_score
        level = "Low" if score < 1.5 else ("Mild" if score < 2.0 else ("Moderate" if score < 2.5 else "Elevated"))
        st.success(f"✅ Last session score: **{round(score, 2)}** — {level} concern")
        st.progress(min(score / 4.0, 1.0))

    if not st.session_state.chatbot_running:
        if st.button("🎙️ Start Voice Session"):
            st.session_state.chatbot_running = True
            st.session_state.chatbot_score = None
            st.rerun()
    else:
        st.warning("🎤 Voice session is running in the background. Please answer all questions spoken to you. **Do not close this window.**")
        placeholder = st.empty()
        placeholder.info("⏳ Running chatbot session...")

        def run_chatbot_thread():
            # Add project root to path so imports work
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from modules.chatbot import run_chatbot
            score = run_chatbot(st.session_state.get("age_group_select", "youth"))
            st.session_state.chatbot_score = score
            st.session_state.chatbot_running = False

        t = threading.Thread(target=run_chatbot_thread, daemon=True)
        t.start()
        t.join()  # blocks until done

        st.session_state.chatbot_running = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─── EYE MODULE PAGE ──────────────────────────────────────────────────────────
def page_eye():
    st.markdown('<p class="section-header">👁️ Behavioral Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Real-time eye tracking & facial movement analysis using your webcam.</p>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("📷 A webcam window will open. Look naturally at the camera. **Press `q`** on that window to end the session and upload results.")

    if st.session_state.session_summary:
        summary = st.session_state.session_summary
        st.markdown("#### 📊 Latest Analysis Result")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'Mental Risk Score: <span style="color:#a78bfa;font-size:2rem;font-weight:800">{summary["mental_risk_score"]}</span> / 100', unsafe_allow_html=True)
            st.markdown(risk_badge(summary["dominant_risk"]), unsafe_allow_html=True)
        with col2:
            st.metric("Session Duration", f"{summary['duration_seconds']}s")
            st.metric("Total Frames", summary["total_frames"])
        st.markdown(f"**💬 Recommendation:** {summary['recommendation']}")
        st.divider()

    if not st.session_state.eye_running:
        if st.button("🚀 Launch Eye Tracking"):
            st.session_state.eye_running = True
            st.session_state.session_summary = None
            st.rerun()
    else:
        st.warning("📷 Camera window is open. Press **`q`** on it to finish. This page will update automatically when done.")

        def run_eye_and_upload():
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from modules.eye_tracker import start_system
            start_system()  # blocks until 'q' is pressed

            # Upload CSV to backend
            csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "session_data.csv"))
            if os.path.exists(csv_path):
                with open(csv_path, "r") as f:
                    csv_content = f.read()
                session_id = f"session_{uuid.uuid4().hex[:8]}"
                try:
                    r = requests.post(
                        f"{API_BASE}/session/upload-csv/{session_id}",
                        content=csv_content,
                        headers={**api_headers(), "Content-Type": "text/plain"},
                        timeout=15,
                    )
                    if r.status_code == 200:
                        st.session_state.session_summary = r.json()
                except Exception as e:
                    print(f"Upload error: {e}")
            st.session_state.eye_running = False

        t = threading.Thread(target=run_eye_and_upload, daemon=True)
        t.start()
        t.join()  # blocks streamlit until camera is closed

        st.session_state.eye_running = False
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─── FACE DETECTION PAGE ──────────────────────────────────────────────────────
def page_face():
    st.markdown('<p class="section-header">🔍 Face Detection</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub">Test live face detection with bounding boxes using MediaPipe.</p>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.info("📷 A webcam window will open showing face detection bounding boxes. Press **`q`** to close.")

    if st.button("🔍 Launch Face Detection"):
        st.warning("📷 Face detection window is open. Press **`q`** to close.")
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from modules.face_detector import start_face_detection
        start_face_detection()  # blocks until 'q'
        st.success("✅ Face detection session ended.")
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─── ROUTER ───────────────────────────────────────────────────────────────────
render_sidebar()

if not st.session_state.authenticated:
    page_auth()
else:
    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        page_dashboard()
    elif page == "chatbot":
        page_chatbot()
    elif page == "eye":
        page_eye()
    elif page == "face":
        page_face()
