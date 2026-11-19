from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import sqlite3
import ollama
import os
import hashlib
import random
from functools import wraps

# ==========================================================
# Flask Configuration
# ==========================================================

app = Flask(__name__)
app.secret_key = "chemistry_laboratory_safety_key"

DATABASE = "chemistry_laboratory_safety.db"
EXCEL_FILE = "chemistry_laboratory_safety_knowledge_base.xlsx"

# ==========================================================
# Database Initialization
# ==========================================================

def init_db():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()

# ==========================================================
# Password Hashing
# ==========================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ==========================================================
# User Functions
# ==========================================================

def register_user(username, email, password):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO users(username,email,password)
        VALUES(?,?,?)
        """, (
            username,
            email,
            hash_password(password)
        ))

        conn.commit()
        return True

    except:

        return False

    finally:

        conn.close()


def verify_user(username, password):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT password
    FROM users
    WHERE username=?
    """, (username,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return False

    return row[0] == hash_password(password)


# ==========================================================
# Login Required Decorator
# ==========================================================

def login_required(f):

    @wraps(f)

    def decorated_function(*args, **kwargs):

        if "username" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


# ==========================================================
# Load Sentence Transformer
# ==========================================================

print("Loading embedding model...")

model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

print("Embedding model loaded.")


# ==========================================================
# Load Knowledge Base
# ==========================================================

print("Loading chemistry_laboratory_safety Knowledge Base...")

df = pd.read_excel(EXCEL_FILE)

required_columns = [
    "Question",
    "Answer",
    "Category"
]

for col in required_columns:

    if col not in df.columns:

        raise Exception(f"Missing column : {col}")

print("Knowledge Base Loaded")

# ==========================================================
# Generate Embeddings
# ==========================================================

print("Generating Embeddings...")

df["embedding"] = df["Question"].apply(
    lambda x: model.encode(
        str(x),
        convert_to_tensor=True
    )
)

print("Embeddings Ready")


# ==========================================================
# Retrieve Top K Results
# ==========================================================

def retrieve_relevant_context(user_query, top_k=3):

    query_embedding = model.encode(
        user_query,
        convert_to_tensor=True
    )

    similarities = []

    for index, row in df.iterrows():

        score = util.pytorch_cos_sim(
            query_embedding,
            row["embedding"]
        ).item()

        similarities.append(score)

    df["similarity"] = similarities

    top_results = df.sort_values(
        by="similarity",
        ascending=False
    ).head(top_k)

    context = ""

    retrieved_questions = []

    for _, row in top_results.iterrows():

        retrieved_questions.append(row["Question"])

        context += f"""
Question:
{row['Question']}

Answer:
{row['Answer']}

Category:
{row['Category']}

-----------------------------------
"""

    return context, retrieved_questions


# ==========================================================
# chemistry_laboratory_safety System Prompt
# ==========================================================

SYSTEM_PROMPT = """
You are an AI Chemistry Laboratory Safety & Compound Assistant.

Your expertise includes:

- Chemical Elements
- Periodic Table
- Chemical Compounds
- Acids
- Bases
- Salts
- Laboratory Equipment
- Laboratory Safety
- Chemical Reactions
- Organic Chemistry
- Inorganic Chemistry
- Analytical Chemistry
- Physical Chemistry
- Chemical Symbols
- Molecular Structures
- Hazard Symbols
- Laboratory Procedures
- Chemical Properties

Rules:

Answer only using the retrieved chemistry knowledge.

Provide educational and scientific explanations.

Do not provide instructions for creating hazardous substances, unsafe laboratory procedures, or other dangerous activities.

If the question is outside chemistry, politely explain that your knowledge is limited to chemistry education.

Keep answers accurate, professional, and concise.

Do not hallucinate.
"""


# ==========================================================
# Chat History
# ==========================================================

MAX_HISTORY = 6


def build_chat_history():

    if "chat_history" not in session:
        session["chat_history"] = []

    return session["chat_history"]


def add_chat(user, bot):

    history = build_chat_history()

    history.append({

        "user": user,
        "bot": bot

    })

    session["chat_history"] = history[-MAX_HISTORY:]


# ==========================================================
# Random chemistry Facts
# ==========================================================

chemistry_facts = [

    "Hydrogen is the lightest element in the periodic table.",

    "Water is composed of two hydrogen atoms and one oxygen atom.",

    "The periodic table currently contains 118 confirmed elements.",

    "The pH scale measures how acidic or basic a solution is.",

    "Helium is the second most abundant element in the universe.",

    "Carbon forms the basis of all known organic life.",

    "Safety goggles are essential in chemistry laboratories.",

    "Chemical reactions involve the rearrangement of atoms.",

    "Noble gases are generally very unreactive.",

    "Avogadro's number is approximately 6.022 × 10²³."

]

def random_fact():
    return random.choice(chemistry_facts)






# ==========================================================
# Generate Response using Ollama
# ==========================================================

def generate_response(user_question):

    context, retrieved_questions = retrieve_relevant_context(
        user_question,
        top_k=3
    )

    history = build_chat_history()

    conversation = ""

    for item in history:

        conversation += f"""
User:
{item['user']}

Assistant:
{item['bot']}

"""

    prompt = f"""
{SYSTEM_PROMPT}

==========================
Conversation History
==========================

{conversation}

==========================
Retrieved chemistry Knowledge
==========================

{context}

==========================
Current User Question
==========================

{user_question}

Answer professionally.
"""

    try:

        response = ollama.chat(

            model="gpt-oss:120b-cloud",

            messages=[

                {
                    "role":"user",
                    "content":prompt
                }

            ]

        )

        answer = response["message"]["content"]

    except Exception as e:

        answer = f"Error communicating with Ollama : {e}"

    add_chat(user_question, answer)

    return answer, retrieved_questions


# ==========================================================
# Login Route
# ==========================================================

@app.route("/login", methods=["GET","POST"])

def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        if verify_user(username, password):

            session["username"] = username

            session["chat_history"] = []

            return redirect("/")

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")


# ==========================================================
# Signup Route
# ==========================================================

@app.route("/signup", methods=["GET","POST"])

def signup():

    if request.method == "POST":

        username = request.form["username"]

        email = request.form["email"]

        password = request.form["password"]

        success = register_user(
            username,
            email,
            password
        )

        if success:

            return redirect("/login")

        return render_template(
            "signup.html",
            error="Username already exists"
        )

    return render_template("signup.html")


# ==========================================================
# Logout
# ==========================================================

@app.route("/logout")

def logout():

    session.clear()

    return redirect("/login")


# ==========================================================
# Home
# ==========================================================

@app.route("/")

@login_required

def home():

    return render_template(

        "index.html",

        username=session["username"],

        aquatic_species_fact=random_fact()

    )


# ==========================================================
# Chat Page
# ==========================================================

@app.route("/chat")

@login_required

def chat():

    history = build_chat_history()

    return render_template(

        "chat.html",

        history=history

    )


# ==========================================================
# Send Message API
# ==========================================================

@app.route("/send_message", methods=["POST"])

@login_required

def send_message():

    try:

        data = request.get_json()

        user_message = data["message"].strip()

        if len(user_message) == 0:

            return jsonify({

                "success":False,

                "message":"Question cannot be empty."

            })

        answer, retrieved_questions = generate_response(
            user_message
        )

        return jsonify({

            "success":True,

            "question":user_message,

            "answer":answer,

            "retrieved_questions":retrieved_questions,

            "history":session["chat_history"]

        })

    except Exception as e:

        return jsonify({

            "success":False,

            "message":str(e)

        })


# ==========================================================
# Clear Chat
# ==========================================================

@app.route("/clear_chat")

@login_required

def clear_chat():

    session["chat_history"] = []

    return redirect("/chat")


# ==========================================================
# About Page
# ==========================================================

@app.route("/about")

@login_required

def about():

    return render_template("about.html")


# ==========================================================
# Knowledge Categories
# ==========================================================

@app.route("/categories")

@login_required

def categories():

    categories = sorted(

        df["Category"].unique().tolist()

    )

    return render_template(

        "categories.html",

        categories=categories

    )


# ==========================================================
# Search Knowledge Base
# ==========================================================

@app.route("/search")

@login_required

def search():

    keyword = request.args.get("q","")

    results = []

    if keyword != "":

        filtered = df[

            df["Question"].str.contains(
                keyword,
                case=False,
                na=False
            )

        ]

        results = filtered.to_dict(
            orient="records"
        )

    return render_template(

        "search.html",

        keyword=keyword,

        results=results

    )


# ==========================================================
# Profile
# ==========================================================

@app.route("/profile")

@login_required

def profile():

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email FROM users WHERE username=?",
        (session["username"],)
    )
    row = cursor.fetchone()
    conn.close()

    email = row[0] if row else "—"
    chat_count = len(build_chat_history())

    return render_template(

        "profile.html",

        username=session["username"],

        email=email,

        total_questions=len(df),

        total_categories=df["Category"].nunique(),

        chat_count=chat_count,

        kb_percent=min(100, int(len(df) / 10)),

        chat_percent=min(100, int(chat_count / 6 * 100))

    )


# ==========================================================
# Health Check
# ==========================================================

@app.route("/health")

def health():

    return jsonify({

        "status":"running",

        "knowledge_base_rows":len(df),

        "embedding_model":"paraphrase-MiniLM-L6-v2",

        "llm":"gpt-oss:120b-cloud"

    })


# ==========================================================
# 404
# ==========================================================

@app.errorhandler(404)

def page_not_found(e):

    return render_template("404.html"),404


# ==========================================================
# 500
# ==========================================================

@app.errorhandler(500)

def internal_error(e):

    return render_template("500.html"),500


# ==========================================================
# Run Application
# ==========================================================

if __name__ == "__main__":

    app.run(

        debug=False,

        host="0.0.0.0",

        port=5000

    )