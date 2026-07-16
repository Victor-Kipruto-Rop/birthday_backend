# 🎉 Birthday Backend API

A secure, production-ready Flask backend powering my birthday website. The backend handles birthday wishes, Pay Hero M-Pesa STK Push payments, SMTP email notifications, and communication with the frontend.

---

# Features

- 🎂 Receive birthday wishes
- 💝 Initiate Pay Hero M-Pesa STK Push payments
- 📧 Send birthday wishes to my email using SMTP
- 🔔 Receive payment callback notifications
- 🌍 RESTful JSON API
- 🔒 Environment variable configuration
- 🛡️ Input validation
- ⚡ Production-ready for Render
- 🌐 Supports Vercel frontend

---

# Tech Stack

- Python 3
- Flask
- Flask-CORS
- Requests
- Gunicorn
- python-dotenv
- SMTP
- Pay Hero API
- Render

---

# Project Structure

```
birthday-backend/
│
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── .gitignore
│
├── routes/
│   ├── health.py
│   ├── wishes.py
│   ├── payments.py
│   └── callback.py
│
├── services/
│   ├── smtp_service.py
│   ├── payhero_service.py
│   └── validation.py
│
├── models/
│   └── storage.py
│
├── utils/
│   ├── helpers.py
│   ├── logger.py
│   └── responses.py
│
└── static/
```

---

# API Endpoints

## Health Check

```
GET /api/health
```

Returns server status.

---

## Send Birthday Wish

```
POST /api/wish
```

Example Request

```json
{
  "name": "John Doe",
  "phone": "254712345678",
  "message": "Happy Birthday! Wishing you many more amazing years."
}
```

---

## Initiate Payment

```
POST /api/payment
```

Example Request

```json
{
  "phone": "254712345678",
  "amount": 500
}
```

Starts a Pay Hero M-Pesa STK Push transaction.

---

## Payment Status

```
GET /api/payment-status/<transaction_id>
```

Returns the latest payment status.

---

## Pay Hero Callback

```
POST /api/payhero/callback
```

Receives payment confirmations from Pay Hero.

---

# Environment Variables

Create a `.env` file with the following variables.

```env
SECRET_KEY=

FRONTEND_URL=

SMTP_SERVER=
SMTP_PORT=
SMTP_EMAIL=
SMTP_PASSWORD=
RECIPIENT_EMAIL=

PAYHERO_BASE_URL=
PAYHERO_USERNAME=
PAYHERO_PASSWORD=
PAYHERO_CHANNEL_ID=
PAYHERO_CALLBACK_URL=

LOG_LEVEL=INFO
```

---

# Installation

Clone the repository.

```bash
git clone <repository-url>
```

Move into the project.

```bash
cd birthday-backend
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate it.

Linux/macOS

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create a `.env` file.

Run the application.

```bash
python app.py
```

---

# Running with Gunicorn

```bash
gunicorn app:app
```

---

# Deploying to Render

1. Push the project to GitHub.
2. Create a new Web Service on Render.
3. Connect the GitHub repository.
4. Build Command

```bash
pip install -r requirements.txt
```

5. Start Command

```bash
gunicorn app:app
```

6. Add all environment variables in the Render dashboard.
7. Deploy.

---

# Frontend

The frontend is deployed separately on Vercel.

The backend only accepts requests from the configured frontend URL.

Example

```
https://your-project.vercel.app
```

---

# SMTP

Birthday wishes are sent securely using SMTP.

Supported providers include:

- Gmail
- Outlook
- Zoho
- Custom SMTP servers

---

# Payments

Payments are processed securely using the Pay Hero API.

Flow:

```
Visitor
      │
      ▼
Frontend (Vercel)
      │
      ▼
Flask Backend (Render)
      │
      ▼
Pay Hero STK Push
      │
      ▼
M-Pesa Prompt
      │
      ▼
Payment Callback
      │
      ▼
Email Notification
```

---

# Security

- Environment variables protect sensitive credentials.
- API keys are never exposed to the frontend.
- Input validation on all endpoints.
- Secure CORS configuration.
- Structured error handling.
- Logging for monitoring and debugging.

---

# Future Improvements

- PostgreSQL database support
- Admin dashboard
- Email templates
- Transaction history
- Analytics dashboard
- Payment receipts
- Rate limiting
- Authentication for admin routes

---

# License

This project is licensed under the MIT License.

---

## Author

**Victor Kipruto Rop**

Data Engineer • Data Science Student • FinTech Infrastructure Builder

Built with ❤️ to celebrate a special birthday while showcasing secure payment integration and modern backend engineering.
