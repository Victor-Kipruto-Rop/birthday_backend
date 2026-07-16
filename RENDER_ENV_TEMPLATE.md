# Birthday Backend - Render Environment Variables Template
# 
# Instructions for Render Deployment:
# 1. Go to Render Dashboard → your service → Settings → Environment
# 2. Add each variable below with YOUR actual values
# 3. Copy the values from the sources listed below
# 4. NEVER commit real secrets to Git - only use Render's environment dashboard
#
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# FLASK CORE
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_KEY=generate-a-secure-random-string-e.g.-$(openssl-rand-32-hex)
# Generate via: openssl rand -hex 32
# This must be a long, random string. Never use the default value in production.

# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND (CORS)
# ═══════════════════════════════════════════════════════════════════════════════

FRONTEND_URL=https://your-project.vercel.app
# Your Vercel frontend URL. CORS will only allow requests from this origin.
# Example: https://birthday-site.vercel.app

# ═══════════════════════════════════════════════════════════════════════════════
# SMTP / EMAIL NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

SMTP_SERVER=smtp.gmail.com
# For Gmail: smtp.gmail.com
# For SendGrid: smtp.sendgrid.net
# For other providers, check their documentation

SMTP_PORT=587
# Standard for TLS: 587
# Standard for SSL: 465

SMTP_EMAIL=your-email@gmail.com
# The email address that sends wishes/payment notifications
# For Gmail: your full Gmail address (e.g. your-name@gmail.com)
# For Gmail App Password: https://support.google.com/accounts/answer/185833
#   Generate an app-specific password, use that instead of your Gmail password

SMTP_PASSWORD=your-app-specific-password
# For Gmail: Generate an app password (not your main Gmail password!)
#   - Go to: https://myaccount.google.com/apppasswords
#   - Select Mail and Windows Computer
#   - Copy the 16-character password
# For SendGrid: Use your SendGrid API key with username "apikey"

RECIPIENT_EMAIL=owner@example.com
# Your email address where wish notifications are sent
# This is who receives the birthday wishes and payment confirmations

# ═══════════════════════════════════════════════════════════════════════════════
# PAY HERO / M-PESA
# ═══════════════════════════════════════════════════════════════════════════════

PAYHERO_BASE_URL=https://backend.payhero.co.ke/api/v2
# Pay Hero's API base URL. This is the production endpoint.
# Do not change unless Pay Hero updates it.

PAYHERO_USERNAME=your-payhero-username
# Your Pay Hero account username
# Get from: https://payhero.co.ke/ → Dashboard → API Settings

PAYHERO_PASSWORD=your-payhero-password
# Your Pay Hero account password or API key
# Get from: https://payhero.co.ke/ → Dashboard → API Settings

PAYHERO_CHANNEL_ID=your-channel-id
# Your Pay Hero channel/merchant ID
# Get from: https://payhero.co.ke/ → Dashboard → Channels
# Example: might look like a number or UUID

PAYHERO_CALLBACK_URL=https://your-backend.onrender.com/api/payhero/callback
# The URL Pay Hero will call when payments are completed
# IMPORTANT: After your first Render deployment, update this to your actual Render URL
# Format: https://[your-service-name].onrender.com/api/payhero/callback
# Get your URL from: Render Dashboard → your service → copy the URL from the top
# Then add /api/payhero/callback to it

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE (OPTIONAL - for persistent storage)
# ═══════════════════════════════════════════════════════════════════════════════

DATABASE_URL=
# Leave empty to use JSON file storage (ephemeral on Render free tier)
#
# For persistent storage, use PostgreSQL:
# 
# Option A: Supabase (Free Tier)
#   1. Go to https://supabase.com → Create new project
#   2. Wait for setup, then go to Settings → Database → Connection string
#   3. Copy the PostgreSQL connection string
#   4. Paste here: postgresql://postgres:[PASSWORD]@db.[REGION].supabase.co/postgres
#
# Option B: Render PostgreSQL Add-On
#   1. Go to Render Dashboard → your service → Settings → Add-ons
#   2. Add PostgreSQL ($7+/month)
#   3. The DATABASE_URL is automatically set by Render
#
# Option C: Railway, Heroku, or other provider
#   1. Create a PostgreSQL database
#   2. Copy the connection string
#   3. Paste here
#
# Example (Supabase): postgresql://postgres:password123@db.yourregion.supabase.co/postgres

# ═══════════════════════════════════════════════════════════════════════════════
# REDIS (OPTIONAL - for scaling rate limiting to multiple workers)
# ═══════════════════════════════════════════════════════════════════════════════

REDIS_URL=
# Leave empty to use in-memory rate limiting (works for single worker only)
#
# For multiple Gunicorn workers or horizontal scaling, use Redis:
#
# Option A: Render Redis Add-On
#   1. Go to Render Dashboard → your service → Settings → Add-ons
#   2. Add Redis ($7+/month)
#   3. The REDIS_URL is automatically set by Render
#
# Option B: Railway, Upstash, or other provider
#   1. Create a Redis database
#   2. Copy the connection string
#   3. Paste here
#
# Example: redis://user:password@redis.host:6379/0

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

LOG_LEVEL=INFO
# Options: DEBUG (verbose), INFO (standard), WARNING, ERROR, CRITICAL
# Use INFO for production, DEBUG for troubleshooting

# ═══════════════════════════════════════════════════════════════════════════════
# QUICK SETUP CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
#
# ✅ MUST CONFIGURE (requests will fail without these):
#   - SECRET_KEY (generate random)
#   - FRONTEND_URL (your Vercel URL)
#   - PAYHERO_USERNAME / PAYHERO_PASSWORD / PAYHERO_CHANNEL_ID
#   - PAYHERO_CALLBACK_URL (set after first deploy)
#
# ✅ SHOULD CONFIGURE (email won't work without these):
#   - SMTP_EMAIL / SMTP_PASSWORD
#   - RECIPIENT_EMAIL
#
# ✅ SHOULD CONFIGURE (data will be lost on redeploy without this):
#   - DATABASE_URL (use Supabase free tier if unsure)
#
# ✅ OPTIONAL (nice-to-have for scaling):
#   - REDIS_URL (only if you run multiple workers)
#
# ═══════════════════════════════════════════════════════════════════════════════
# HOW TO ADD THESE TO RENDER
# ═══════════════════════════════════════════════════════════════════════════════
#
# 1. Go to Render Dashboard → click your service
# 2. Click "Settings" in the left sidebar
# 3. Scroll to "Environment" section
# 4. Click "Add Environment Variable"
# 5. Paste each key-value pair from above
# 6. After adding DATABASE_URL (PostgreSQL), Render may auto-set it
# 7. Click "Save Changes"
# 8. Service will automatically redeploy with new env vars
#
# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY NOTES
# ═══════════════════════════════════════════════════════════════════════════════
#
# - NEVER commit .env files with real secrets to Git
# - NEVER paste secrets into code comments
# - Always use Render's Environment dashboard for secrets
# - Rotate PAYHERO_PASSWORD and SECRET_KEY periodically
# - Use app-specific passwords for email (not your actual email password)
# - Keep RENDER_API_KEY (for CI/CD) in GitHub Secrets, not in Render Environment
#
# ═══════════════════════════════════════════════════════════════════════════════
