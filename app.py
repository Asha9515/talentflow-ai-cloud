import os
import boto3
import pymysql
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

DB_CONFIG = {
    "host": "talentflow-db.cixec2e4kne6.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "user": "admin",
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": "talentflow",
    "ssl": {"ca": "/home/ubuntu/global-bundle.pem"},
    "cursorclass": pymysql.cursors.DictCursor
}

S3_BUCKET = "talentflow-ai-storage-2026"
s3_client = boto3.client("s3", region_name="us-east-1")

def get_db():
    return pymysql.connect(**DB_CONFIG)

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(120) NOT NULL,
                role VARCHAR(100) NOT NULL,
                resume_key VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TalentFlow AI - Candidate Portal</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 20px; background: #f4f6f9; }
        .card { background: #fff; padding: 24px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; }
        input, button { width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; }
        button { background: #2563eb; color: #fff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border-bottom: 1px solid #e5e7eb; text-align: left; }
        .badge { background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>TalentFlow AI — Resume Upload & Candidate Intake</h2>
        <p><span class="badge">AWS Architecture Active: EC2 + RDS MySQL + S3</span></p>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="name" placeholder="Candidate Full Name" required>
            <input type="email" name="email" placeholder="Candidate Email" required>
            <input type="text" name="role" placeholder="Target Role (e.g., Cloud Engineer)" required>
            <input type="file" name="resume" accept=".pdf,.doc,.docx,.txt" required>
            <button type="submit">Submit Application to S3 & RDS</button>
        </form>
    </div>
    <div class="card">
        <h3>Submitted Candidates (Stored in RDS MySQL)</h3>
        <table>
            <tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>S3 Resume File</th></tr>
            {% for c in candidates %}
            <tr>
                <td>{{ c.id }}</td>
                <td>{{ c.name }}</td>
                <td>{{ c.email }}</td>
                <td>{{ c.role }}</td>
                <td>{{ c.resume_key }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    init_db()
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        role = request.form["role"]
        file = request.files["resume"]
        s3_key = f"resumes/{file.filename}"
        s3_client.upload_fileobj(file, S3_BUCKET, s3_key)
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO candidates (name, email, role, resume_key) VALUES (%s, %s, %s, %s)",
                (name, email, role, s3_key)
            )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM candidates ORDER BY id DESC")
        candidates = cur.fetchall()
    conn.close()
    return render_template_string(HTML, candidates=candidates)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
