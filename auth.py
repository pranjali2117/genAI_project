import streamlit as st
import sqlite3
import bcrypt

# ---- DB Setup ----
conn = sqlite3.connect("sports_ai.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    username TEXT PRIMARY KEY,
    password BLOB
)
""")
conn.commit()

# ---- Register ----
def register(username, password):
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cur.execute("INSERT INTO users VALUES (?, ?)", (username, hashed))
        conn.commit()
        return True
    except:
        return False

# ---- Login ----
def login(username, password):
    cur.execute("SELECT password FROM users WHERE username=?", (username,))
    result = cur.fetchone()
    if result:
        return bcrypt.checkpw(password.encode(), result[0])
    return False

# ---- Auth Page UI ----                        
def show_auth_page():
    st.markdown("""
    <style>
    /* Hide default streamlit header/footer */
    #MainMenu, footer, header {visibility: hidden;}

    /* Center the whole block */
    .block-container {
        max-width: 480px !important;
        margin: auto !important;
        padding-top: 60px !important;
    }

    /* Style all input boxes */
    .stTextInput > div > div > input {
        background: #1e293b !important;
        color: #f1f5f9 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    /* Style buttons */
    .stButton > button {
        width: 100%;
        background: #2563eb !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px !important;
        font-size: 15px !important;
        margin-top: 6px;
    }
    .stButton > button:hover {
        background: #1d4ed8 !important;
    }

    /* Card wrapper using page background */
    section.main > div {
        background: #0f172a;
        border-radius: 16px;
        border: 1px solid #1e293b;
        padding: 40px !important;
        box-shadow: 0px 0px 30px rgba(0,0,0,0.6);
    }
    </style>
    """, unsafe_allow_html=True)

    # ---- Header ----
    st.markdown("## 🚀 SportsGPT")
    st.markdown("#### Welcome back! Please login or register.")
    st.markdown("---")

    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "Login"

    # ---- Tab Switcher ----
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑  Login", use_container_width=True):
            st.session_state.auth_tab = "Login"
    with col2:
        if st.button("📝  Register", use_container_width=True):
            st.session_state.auth_tab = "Register"

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Login Tab ----
    if st.session_state.auth_tab == "Login":
        st.markdown("### Login")
        u = st.text_input("Username", key="login_user", placeholder="Enter your username")
        p = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Login Now ➜", use_container_width=True):
            if login(u, p):
                st.session_state.user = u
                st.rerun()
            else:
                st.error("❌ Invalid credentials")

    # ---- Register Tab ----
    else:
        st.markdown("### Create Account")
        u = st.text_input("Username", key="reg_user", placeholder="Choose a username")
        p = st.text_input("Password", type="password", key="reg_pass", placeholder="Choose a password")
        c = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Repeat your password")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Account ➜", use_container_width=True):
            if p != c:
                st.error("❌ Passwords do not match")
            elif register(u, p):
                st.success("✅ Account created! Please login.")
                st.session_state.auth_tab = "Login"
                st.rerun()
            else:
                st.error("❌ Username already exists")            
                
