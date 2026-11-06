import os
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from flask import Flask, render_template, request, jsonify
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def fetch_web_hiring_leads(keyword, location=""):
    """Fetches real-time hiring posts across Reddit, LinkedIn & Web via Google RSS (Never blocked on cloud servers)"""
    leads = []
    loc_query = f" {location}" if location else ""
    query = urllib.parse.quote(f'("hiring" OR "looking for" OR "need a") "{keyword}"{loc_query}')
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        res = requests.get(rss_url, timeout=10)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            for item in root.findall(".//item")[:6]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else "Recent"
                source_el = item.find("source")
                source_name = source_el.text if source_el is not None else "Web Lead"
                
                leads.append({
                    "source": source_name,
                    "title": title,
                    "description": f"Published: {pub_date[:16]} | Matched Keyword: {keyword}{loc_query}",
                    "url": link
                })
    except Exception as e:
        print("Web RSS Error:", e)
    return leads

def fetch_remotive_leads(keyword):
    """Fetches strictly matched remote jobs"""
    leads = []
    url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(keyword)}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            jobs = res.json().get("jobs", [])
            kw_lower = keyword.lower()
            for job in jobs:
                title = job.get("title", "")
                tags = " ".join(job.get("tags", [])).lower()
                # Strict filter so unrelated jobs don't repeat
                if kw_lower in title.lower() or kw_lower in tags or any(word in title.lower() for word in kw_lower.split()):
                    leads.append({
                        "source": "Remotive",
                        "title": f"{title} at {job.get('company_name')}",
                        "description": f"Location: {job.get('candidate_required_location', 'Worldwide')} | Type: {job.get('job_type', 'Contract/Full-time')}",
                        "url": job.get("url")
                    })
                if len(leads) >= 4:
                    break
    except Exception as e:
        print("Remotive Error:", e)
    return leads

def fetch_arbeitnow_leads(keyword):
    """Fetches fresh international & European/Global jobs"""
    leads = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            jobs = res.json().get("data", [])
            kw_words = keyword.lower().split()
            for job in jobs:
                title = job.get("title", "")
                if any(w in title.lower() for w in kw_words):
                    leads.append({
                        "source": "Arbeitnow",
                        "title": f"{title} — {job.get('company_name')}",
                        "description": f"Location: {job.get('location', 'Remote')} | Remote: {job.get('remote', True)}",
                        "url": job.get("url")
                    })
                if len(leads) >= 4:
                    break
    except Exception as e:
        print("Arbeitnow Error:", e)
    return leads

def generate_human_pitch(lead_title, lead_desc, user_skill, user_portfolio):
    if not client:
        return "API Key missing in Render Environment Variables. Please add GEMINI_API_KEY."
    
    prompt = f"""
    You are an expert freelancer or agency owner reaching out to a potential client.
    Lead Title: {lead_title}
    Lead Context: {lead_desc}
    My Expertise: {user_skill}
    My Portfolio/Contact: {user_portfolio}

    Write a unique, tailored, natural-sounding outreach pitch in clear, professional English (55 to 75 words).
    STRICT RULES:
    - NEVER use generic openings like "I hope this message finds you well" or "Dear Sir/Madam".
    - Reference specific details from the Lead Title so every pitch feels 100% custom-written for that exact client.
    - Highlight how my {user_skill} expertise solves their need, and smoothly include {user_portfolio}.
    - End with a short, conversational call-to-action question.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"[AI Error: {str(e)[:80]}] — Hi, regarding '{lead_title}', I specialize in {user_skill} and can help deliver this quickly. Work samples: {user_portfolio}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/hunt", methods=["POST"])
def hunt_leads():
    data = request.json
    keyword = data.get("keyword", "").strip()
    location = data.get("location", "").strip()
    portfolio = data.get("portfolio", "Available upon request").strip()

    if not keyword:
        return jsonify({"leads": []})

    all_leads = (
        fetch_web_hiring_leads(keyword, location)
        + fetch_remotive_leads(keyword)
        + fetch_arbeitnow_leads(keyword)
    )

    # Remove duplicate titles
    seen = set()
    unique_leads = []
    for lead in all_leads:
        if lead["title"] not in seen:
            seen.add(lead["title"])
            unique_leads.append(lead)

    enriched_leads = []
    for lead in unique_leads[:8]:
        lead["pitch"] = generate_human_pitch(lead["title"], lead["description"], keyword, portfolio)
        enriched_leads.append(lead)

    return jsonify({"leads": enriched_leads})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
