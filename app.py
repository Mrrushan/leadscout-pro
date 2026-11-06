import os
import requests
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Yahan quotes ke andar apni AIzaSy... wali asli Gemini API key daalein (os.getenv nahi lagana hai)
client = genai.Client(api_key=os.getenv("AQ.Ab8RN6I8xnowIAFq0sWRJGGeQ8UpUf_Z4VxmjahVXsXZB640HQ"))

def fetch_reddit_leads(keyword):
    leads = []
    url = f"https://www.reddit.com/r/DesignJobs+forhire+freelance_forhire/search.json?q={keyword}&restrict_sr=1&sort=new&t=week&limit=10"
    headers = {"User-Agent": "LeadScoutAI/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            posts = res.json().get("data", {}).get("children", [])
            for post in posts:
                data = post["data"]
                title = data.get("title", "")
                selftext = data.get("selftext", "")
                if "[hiring]" in title.lower() or "looking for" in title.lower() or "need a" in title.lower():
                    if "[for hire]" not in title.lower():
                        leads.append({
                            "source": "Reddit",
                            "title": title,
                            "description": selftext[:350] + "..." if len(selftext) > 350 else selftext,
                            "url": f"https://www.reddit.com{data.get('permalink')}"
                        })
    except Exception as e:
        print("Reddit Error:", e)
    return leads

def fetch_remotive_leads(keyword):
    leads = []
    url = f"https://remotive.com/api/remote-jobs?search={keyword}&limit=5"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            jobs = res.json().get("jobs", [])
            for job in jobs[:5]:
                leads.append({
                    "source": "Remotive Job",
                    "title": f"{job.get('title')} - {job.get('company_name')}",
                    "description": f"Location: {job.get('candidate_required_location', 'Remote')} | Category: {job.get('category')}",
                    "url": job.get("url")
                })
    except Exception as e:
        print("Remotive Error:", e)
    return leads

def generate_human_pitch(lead_title, lead_desc, user_skill, user_portfolio):
    prompt = f"""
    You are an expert freelancer/business owner applying for a client lead.
    Client Post Title: {lead_title}
    Client Details: {lead_desc}
    My Skill/Service: {user_skill}
    My Portfolio/Proof: {user_portfolio}

    Write a short, punchy, human-sounding outreach message (max 70 words).
    RULES:
    - NEVER start with "I hope this message finds you well" or "Dear Sir/Madam".
    - Start directly by addressing their exact problem/need.
    - Mention my relevant experience and include my portfolio/contact naturally.
    - End with a simple, low-friction question to start a chat.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Hi! Saw your post about '{lead_title}'. I specialize in {user_skill} and would love to help. Check my work here: {user_portfolio}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/hunt", methods=["POST"])
def hunt_leads():
    data = request.json
    keyword = data.get("keyword", "Graphic Design")
    portfolio = data.get("portfolio", "Available on request")

    all_leads = fetch_reddit_leads(keyword) + fetch_remotive_leads(keyword)
    
    enriched_leads = []
    for lead in all_leads[:8]:
        pitch = generate_human_pitch(lead["title"], lead["description"], keyword, portfolio)
        lead["pitch"] = pitch
        enriched_leads.append(lead)

    return jsonify({"leads": enriched_leads})

if __name__ == "__main__":
    app.run(debug=True, port=5000)