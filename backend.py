import sqlite3
import bcrypt
import datetime
import os
import requests
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq

# -----------------------------
# Database
# -----------------------------

conn = sqlite3.connect("sports_ai.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
username TEXT PRIMARY KEY,
password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
query TEXT,
article TEXT,
timestamp TEXT
)
""")

conn.commit()

# -----------------------------
# Authentication
# -----------------------------

def register_user(username, password):

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    try:
        cursor.execute(
            "INSERT INTO users VALUES (?,?)",
            (username, hashed)
        )
        conn.commit()
        return True
    except:
        return False


def login_user(username, password):

    cursor.execute(
        "SELECT password FROM users WHERE username=?",
        (username,)
    )

    result = cursor.fetchone()

    if result:
        return bcrypt.checkpw(password.encode(), result[0])

    return False


# -----------------------------
# History
# -----------------------------

def save_history(user, query, article):

    cursor.execute(
        "INSERT INTO history(username,query,article,timestamp) VALUES (?,?,?,?)",
        (user, query, article, str(datetime.datetime.now()))
    )

    conn.commit()


def load_history(user):

    cursor.execute(
        "SELECT query,article,timestamp FROM history WHERE username=?",
        (user,)
    )

    return cursor.fetchall()


# -----------------------------
# Sports API
# -----------------------------

CRIC_API_KEY = os.getenv("CRIC_API_KEY")

def get_match_data():

    url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}&offset=0"

    response = requests.get(url)

    data = response.json()

    matches = []

    for match in data["data"][:3]:

        info = f"""
Match: {match['name']}
Status: {match['status']}
Teams: {match['teams']}
Venue: {match['venue']}
"""

        matches.append(info)

    return "\n".join(matches)


# -----------------------------
# VectorDB Memory
# -----------------------------

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.Client()

collection = client.get_or_create_collection("sports_memory")

sports_docs = [
"Virat Kohli is famous for chasing targets.",
"Rohit Sharma is known for explosive starts.",
"Australia relies heavily on pace bowling.",
"India has strong spin bowling in middle overs."
]

embeddings = embedding_model.encode(sports_docs).tolist()

collection.add(
documents=sports_docs,
embeddings=embeddings,
ids=[str(i) for i in range(len(sports_docs))]
)

def retrieve_context(query):

    q_embed = embedding_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=q_embed,
        n_results=2
    )

    return results["documents"][0]


# -----------------------------
# AI Generation (Groq)
# -----------------------------

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_article(query, match_data):

    context = retrieve_context(query)

    prompt = f"""
Sports knowledge:
{context}

Live match data:
{match_data}

Write a professional sports article.
"""

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role":"system","content":"You are a sports journalist"},
            {"role":"user","content":prompt}
        ]
    )

    return response.choices[0].message.content