import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# ==========================================
# 1. API KEYS SETUP
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TUMHARI_GEMINI_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "TUMHARI_GOOGLE_MAPS_KEY_YAHAN_DAALO")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ==========================================
# 2. WHATSAPP / CALL SCRIPT GENERATOR
# ==========================================
def generate_whatsapp_script(client_name):
    prompt = f"""
    Write a very short, polite WhatsApp outreach message (Hinglish/English mix) for a client named '{client_name}'.
    I am Md Rushan, a graphic designer and owner of a Custom Mirror Fitting & Barrisol Premium Ceiling business.
    
    Key points to include:
    - We provide 3D stretch ceilings and custom glass/mirror fitting.
    - We operate on a 'Direct-to-Site' model (no showroom, we bring samples directly to their office/site).
    - Ask for a quick 2-minute call to discuss potential collaboration.
    
    Keep it under 60 words. Make it sound human and professional.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Namaste! Hum Barrisol Premium Ceiling aur Custom Mirrors ka direct-to-site kaam karte hain. Kya hum ek choti call par connect kar sakte hain?"

# ==========================================
# 3. REAL PHONE NUMBERS ROUTE (Google Places API)
# ==========================================
@app.route('/api/get-real-contacts', methods=['POST'])
def get_real_contacts():
    data = request.json
    niche = data.get('niche', 'Interior Designers')
    location = data.get('location', 'Okhla, New Delhi')
    
    query = f"{niche} in {location}"
    
    # Google Places Text Search API (Official method to get real phone numbers)
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        response = requests.get(url).json()
        results = response.get('results', [])
        
        leads = []
        # Top 5 leads nikalna
        for place in results[:5]:
            place_id = place.get('place_id')
            name = place.get('name')
            address = place.get('formatted_address')
            
            # Phone number nikalne ke liye Place Details API call
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number&key={GOOGLE_MAPS_API_KEY}"
            details_response = requests.get(details_url).json()
            
            phone_number = details_response.get('result', {}).get('formatted_phone_number', 'Number not public')
            
            # Agar phone number available hai, tabhi lead save karo
            if phone_number != 'Number not public':
                whatsapp_script = generate_whatsapp_script(name)
                
                leads.append({
                    "business_name": name,
                    "phone_number": phone_number,
                    "address": address,
                    "whatsapp_pitch": whatsapp_script
                })
                
        return jsonify({"status": "success", "total_contacts_found": len(leads), "data": leads})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
