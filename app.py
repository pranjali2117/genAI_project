import streamlit as st, sqlite3, bcrypt, requests, os, datetime
from dotenv import load_dotenv
from groq import Groq

# ---------------- Config ----------------
st.set_page_config(page_title="🏏 Sports genAI ", layout="wide")
st.markdown("""
<style>

.right-panel {
position: fixed;
top: 80px;
right: -320px;
width: 300px;
height: 80%;
background: #1e293b;
color: white;
padding: 20px;
border-radius: 12px 0 0 12px;
box-shadow: -4px 0 20px rgba(0,0,0,0.4);
transition: right 0.4s ease;
z-index: 999;
}

.right-panel.open {
right: 0;
}

.toggle-btn {
position: fixed;
right: 10px;
top: 120px;
background: #2563eb;
color: white;
border-radius: 20px;
padding: 8px 14px;
cursor: pointer;
}

</style>
""", unsafe_allow_html=True)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
CRIC_API_KEY = os.getenv("CRIC_API_KEY")

# ---------------- Database ----------------
conn = sqlite3.connect("sports_ai.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password TEXT)")
cur.execute("""CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,query TEXT,article TEXT,timestamp TEXT)""")
conn.commit()

# ---------------- Auth ----------------
def register(u,p):
    try:
        cur.execute("INSERT INTO users VALUES (?,?)",
        (u,bcrypt.hashpw(p.encode(),bcrypt.gensalt())))
        conn.commit(); return True
    except: return False

def login(u,p):
    cur.execute("SELECT password FROM users WHERE username=?",(u,))
    r=cur.fetchone()
    return r and bcrypt.checkpw(p.encode(),r[0])

# ---------------- History ----------------
def save_hist(u,q,a):
    cur.execute("INSERT INTO history(username,query,article,timestamp) VALUES (?,?,?,?)",
                (u,q,a,str(datetime.datetime.now())))
    conn.commit()

def load_hist(u):
    cur.execute("SELECT query,article,timestamp FROM history WHERE username=?",(u,))
    return cur.fetchall()

# ---------------- Live Matches ----------------
def get_matches():
    try:
        data=requests.get(
        f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}"
        ).json()
        return "\n".join([f"{m['name']} | {m['status']}" for m in data.get("data",[])[:3]])
    except:
        return "MI vs CSK | Live\nRCB vs RR | Upcoming\nPBKS vs GT | Completed"

# ---------------- AI Generation ----------------
def generate(query, match, style="ESPN Analysis"):

    style_instructions = {
        "ESPN Analysis":
            "Write like an ESPN analyst. Open dramatically, give deep tactical insight, end with a verdict.",
        "Match Recap":
            "Write a structured match recap: key moments, turning points, player ratings, final result.",
        "Twitter Thread":
            "Write as a Twitter/X thread. Number each tweet 1/, 2/, 3/ etc. Keep each tweet under 280 characters. Make it punchy and engaging.",
        "Cricket Tips":
            "Focus on fantasy cricket value. List top picks, differential picks, and players to avoid with reasons.",
        "Post-Match Press Conference":
            "Write as a simulated post-match press conference Q&A between a journalist and the winning captain.",
    }

    instruction = style_instructions.get(style, style_instructions["ESPN Analysis"])

    prompt = f"""Write a professional sports article about:
{query}

Using match info:
{match}

Style instructions: {instruction}"""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "You are an expert sports journalist and analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return r.choices[0].message.content

# ---------------- Session ----------------
if "user" not in st.session_state: st.session_state.user=None

# ---------------- Login UI ----------------
if not st.session_state.user:

    st.title("🚀 Login or Register")

    tab1,tab2=st.tabs(["Login","Register"])

    with tab1:
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("Login"):
            if login(u,p):
                st.session_state.user=u; st.rerun()
            else: st.error("Invalid credentials")

    with tab2:
        u=st.text_input("New Username")
        p=st.text_input("New Password",type="password")
        if st.button("Create Account"):
            st.success("Account created!") if register(u,p) else st.error("User exists")

# ---------------- Main App ----------------
else:
    st.sidebar.write(f"Welcome {st.session_state.user} \n")
    page=st.sidebar.radio("\nMenu",["Generate","History"])
    print("\n\n")
    if st.sidebar.button("Logout"):
        st.session_state.user=None; st.rerun()

    # -------- Generate --------
    if page == "Generate":

        st.title("🏏 Sports Content Generator")
        c1, c2 = st.columns([3, 1])

        # -------- LEFT COLUMN --------
        with c1:
            query = st.text_input("Enter topic")

            # ✅ NEW: Style / tone selector
            style = st.selectbox(
                "Article style",
                [
                    "ESPN Analysis",
                    "Match Recap",
                    "Twitter Thread",
                    "Fantasy Cricket Tips",
                    "Post-Match Press Conference",
                ],
            )

            if st.button("Generate Article"):
                if query:
                    # ✅ NEW: Step-by-step status messages
                    status = st.empty()

                    status.info("📡 Fetching live match data...")
                    match = get_matches()

                    status.info("🧠 Retrieving sports knowledge...")
                    import time; time.sleep(0.5)   # small pause so user sees the step

                    status.info("✍️ Writing your article...")
                    article = generate(query, match, style)   # pass style to generate()

                    status.empty()   # clear the status box when done

                    # ✅ NEW: Show article in a nice card
                    st.markdown(
                        f"""
                        <div style="
                            background: #1e293b;
                            border-radius: 12px;
                            padding: 24px 28px;
                            color: #f1f5f9;
                            line-height: 1.8;
                            font-size: 15px;
                            margin-top: 12px;
                        ">
                        {article.replace(chr(10), '<br>')}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # ✅ NEW: Download button
                    st.download_button(
                        label="⬇️ Download Article",
                        data=article,
                        file_name=f"{query[:30].replace(' ', '_')}_article.txt",
                        mime="text/plain",
                    )

                    save_hist(st.session_state.user, query, article)

                else:
                    st.warning("Enter a topic")

        # -------- RIGHT COLUMN --------
        with c2:
            st.markdown("### 🔥 Trending")
            matches = get_matches()
            for line in matches.split("\n"):
                if line.strip():
                    st.markdown(
                        f"""
                        <div style="
                            background: #1e293b;
                            border-radius: 8px;
                            padding: 10px 14px;
                            color: #f1f5f9;
                            font-size: 13px;
                            margin-bottom: 8px;
                        ">{line}</div>
                        """,
                        unsafe_allow_html=True,
                    )
       
    # -------- History --------
    if page=="History":
        st.title("📚 Article History")
        for q,a,t in load_hist(st.session_state.user):
            with st.expander(f"{q} ({t[:10]})"):
                st.write(a)
