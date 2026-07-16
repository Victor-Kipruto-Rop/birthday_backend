Birthday Website — Wishes + M-Pesa Gift (STK Push)
A birthday page where visitors can:
Push a birthday wish (name, message, phone) → you get it on WhatsApp
Deploy a gift via M-Pesa STK Push → you get a WhatsApp receipt when it succeeds
frontend/   plain HTML/CSS/JS — the page itself
backend/    Flask API — Daraja STK push + Twilio WhatsApp notifications
1. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
Fill in .env:
Daraja (M-Pesa)
Create an app at https://developer.safaricom.co.ke to get MPESA_CONSUMER_KEY / MPESA_CONSUMER_SECRET.
For sandbox testing, MPESA_SHORTCODE=174379 and the passkey from the "Lipa Na M-Pesa Online" sandbox page both work out of the box.
MPESA_CALLBACK_URL must be publicly reachable over HTTPS — Safaricom's servers call it directly. Locally, run ngrok http 5000 and use the https://...ngrok-free.app/api/stk-callback URL it gives you. In production, use your deployed backend URL.
Twilio WhatsApp
Create a free account at https://www.twilio.com.
Go to Messaging → Try it out → Send a WhatsApp message, and join the sandbox by sending the given code to the Twilio sandbox number from your own WhatsApp.
Copy Account SID and Auth Token into .env.
Set NOTIFY_WHATSAPP_TO to your own number in the format whatsapp:+2547XXXXXXXX.
Note: Twilio's sandbox requires you to re-join every 72 hours by resending the join code. For a permanent setup, apply for a WhatsApp Business sender in Twilio (takes a few days for approval).
Run it:
python app.py
The API runs on http://localhost:5000 by default.
2. Frontend setup
Open frontend/script.js and set:
const API_BASE = "http://localhost:5000"; // or your deployed backend URL
const BIRTHDAY_AGE = 23; // the age you're turning
Then just open frontend/index.html in a browser, or serve it:
cd frontend
python3 -m http.server 8000
3. Testing the STK push (sandbox)
Safaricom's sandbox only accepts specific test phone numbers. Use 254708374149 as the phone number when testing — it will simulate a successful payment without a real prompt on your device. Real prompts only work once you're on production Daraja credentials with a live shortcode.
4. Deploying
Given your existing PesaGuard setup, this fits well on Render:
Deploy backend/ as a Render web service (gunicorn app:app).
Add all .env values as Render environment variables.
Update MPESA_CALLBACK_URL to your Render URL once deployed.
Host frontend/ as a Render static site, or GitHub Pages — just update API_BASE to point at the deployed backend.
Notes on hardening (optional, but you'll want these before sharing widely)
Add rate limiting on /api/wish and /api/stk-push (e.g. Flask-Limiter) to stop spam/abuse.
Move transactions and wishes from in-memory dicts to Redis or Postgres so nothing is lost on restart.
Verify the callback request actually comes from Safaricom's IP range before trusting it.
Restrict CORS to your actual frontend domain instead of * once deployed.
