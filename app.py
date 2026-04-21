import streamlit as st, sqlite3, requests, os, datetime, time
from dotenv import load_dotenv
from auth import show_auth_page
from groq import Groq

# ---------------- Config ----------------
st.set_page_config(page_title="🏏 SportsGPT", layout="wide")
st.markdown("""
<style>
.right-panel {
    position: fixed; top: 80px; right: -320px; width: 300px; height: 80%;
    background: #1e293b; color: white; padding: 20px;
    border-radius: 12px 0 0 12px; box-shadow: -4px 0 20px rgba(0,0,0,0.4);
    transition: right 0.4s ease; z-index: 999;
}
.right-panel.open { right: 0; }
.toggle-btn {
    position: fixed; right: 10px; top: 120px; background: #2563eb;
    color: white; border-radius: 20px; padding: 8px 14px; cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
CRIC_API_KEY = os.getenv("CRIC_API_KEY")

# ---------------- Database ----------------
conn = sqlite3.connect("sports_ai.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT)")
cur.execute("""CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT, query TEXT, article TEXT, timestamp TEXT)""")
conn.commit()

# ---------------- History ----------------
def save_hist(u, q, a):
    cur.execute("INSERT INTO history(username,query,article,timestamp) VALUES (?,?,?,?)",
                (u, q, a, str(datetime.datetime.now())))
    conn.commit()

def load_hist(u):
    cur.execute("SELECT query,article,timestamp FROM history WHERE username=?", (u,))
    return cur.fetchall()

# ---------------- Live Matches ----------------
def get_matches():
    """Returns a list of match dicts. Falls back to dummy data on error."""
    try:
        data = requests.get(
            f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}"
        ).json()
        matches = data.get("data", [])[:5]
        # Normalise to the fields we actually use
        return [
            {
                "name":   m.get("name", "Unknown"),
                "status": m.get("status", ""),
                "teams":  m.get("teams", []),
                "venue":  m.get("venue", "TBD"),
                "date":   m.get("dateTimeGMT", "")[:16],   # "YYYY-MM-DDTHH:MM" → strip seconds/Z
            }
            for m in matches
        ]
    except:
        # Fallback dummy data so the UI never crashes
        now = datetime.datetime.now()
        fmt = "%Y-%m-%dT%H:%M"
        return [
            {"name": "MI vs CSK",   "status": "Live",      "teams": ["MI", "CSK"],   "venue": "Wankhede",    "date": now.strftime(fmt)},
            {"name": "RCB vs RR",   "status": "Upcoming",  "teams": ["RCB", "RR"],   "venue": "Chinnaswamy", "date": (now + datetime.timedelta(hours=3)).strftime(fmt)},
            {"name": "PBKS vs GT",  "status": "Completed", "teams": ["PBKS", "GT"],  "venue": "Mohali",      "date": (now - datetime.timedelta(hours=5)).strftime(fmt)},
        ]

def matches_as_text(matches):
    """Plain-text summary used as context for the AI prompt."""
    return "\n".join([f"{m['name']} | {m['status']}" for m in matches])

# ---------------- AI Generation ----------------
def generate(query, match_text, style="ESPN Analysis"):
    style_instructions = {
        "ESPN Analysis": """
Write like an elite ESPN sports analyst.
- Start with a dramatic, powerful opening.
- Provide deep tactical insights (strategy, key moments, matchups).
- Explain WHY the result happened, not just what happened.
- Highlight key players and critical decisions.
- End with a strong, confident verdict.
""",
        "Match Recap": """
Write a structured match recap.
Include:
- Match Summary
- Key Moments (chronological highlights)
- Turning Points
- Player Performances
- Player Ratings (out of 10 with short reasons)
- Final Result
Keep it clear, factual, and well-organized.
""",
        "Twitter Thread": """
Write as a Twitter/X thread.
- Format as: 1/, 2/, 3/ ...
- Each tweet must be under 280 characters.
- Keep it punchy, engaging, and slightly dramatic.
- Use strong hooks and concise insights.
- Make it highly shareable.
""",
        "Match Tips": """
Act as a fantasy Sports expert.
Provide:
- Top Picks (reliable players with reasons)
- Differential Picks (underrated/high-upside players)
- Players to Avoid (risky or out-of-form players with reasons)
Consider pitch, form, and match conditions.
Keep it practical and decision-focused.
""",
        "Post-Match Press Conference": """
Simulate a post-match press conference.
- Format as a Q&A between journalist and winning captain.
- Include at least 6–8 questions.
- Cover match performance, strategy, key moments.
- Keep answers realistic, professional, and insightful.
"""
    }

    prompt = f"""
You are a professional sports content generator.

MATCH CONTEXT:
{match_text}

USER QUERY:
{query}

STYLE:
{style}

INSTRUCTIONS:
{style_instructions.get(style, "")}

Rules:
- Do NOT mix styles
- Keep output clean and well formatted
- Use real player/team names if available
- Do NOT mention instructions

Generate the response now.
"""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "You are an expert sports analyst and content writer. Adapt tone and structure strictly based on the requested style."},
            {"role": "user", "content": prompt},
        ],
    )
    return r.choices[0].message.content

# ---------------- Session Guard ----------------
if "user" not in st.session_state or not st.session_state.user:
    show_auth_page()  
    st.stop()

# ---------------- Main App ----------------
st.sidebar.write(f"Welcome {st.session_state.user}")
page = st.sidebar.radio("Menu", ["Generate", "History"])

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

# -------- Generate --------
if page == "Generate":
    st.title("🏏 SportsGPT")
    st.subheader("Sports Content Generator")
    c1, c2 = st.columns([3, 1])

    # -------- LEFT COLUMN --------
    with c1:
        query = st.text_input("Enter topic")
        style = st.selectbox(
            "Article style",
            ["ESPN Analysis", "Match Recap", "Twitter Thread", "Match Tips", "Post-Match Press Conference"],
        )

        if st.button("Generate Article"):
            if query:
                status = st.empty()

                status.info("📡 Fetching live match data...")
                matches = get_matches()                        # list of dicts

                status.info("🧠 Retrieving sports knowledge...")
                time.sleep(0.5)

                status.info("✍️ Writing your article...")
                article = generate(query, matches_as_text(matches), style)

                status.empty()

                st.markdown(
                    f"""
                    <div style="
                        background:#1e293b; border-radius:12px; padding:24px 28px;
                        color:#f1f5f9; line-height:1.8; font-size:15px; margin-top:12px;
                    ">
                    {article.replace(chr(10), '<br>')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.download_button(
                    label="⬇️ Download Article",
                    data=article,
                    file_name=f"{query[:30].replace(' ', '_')}_article.txt",
                    mime="text/plain",
                )

                save_hist(st.session_state.user, query, article)
            else:
                st.warning("Enter a topic")
    
# -------- History --------
if page == "History":
    st.title("📚 Article History")
    for q, a, t in load_hist(st.session_state.user):
        with st.expander(f"{q} ({t[:10]})"):
            st.write(a)
