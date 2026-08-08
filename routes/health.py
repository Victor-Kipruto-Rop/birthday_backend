"""
routes/health.py
=================
GET /api/health - simple health check endpoint used by Render and any
uptime monitors to verify the service is running.
"""

from flask import Blueprint, Response

from services.availability import submission_cutoff, submissions_open
from utils.responses import success

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Return a basic healthy status payload."""
    return success(message="Service is healthy.", data={"status": "healthy"})


@health_bp.route("/api/availability", methods=["GET"])
def availability_check():
    """Return the configured submission window for frontend synchronization."""
    return success(
        message="Availability retrieved.",
        data={
            "open": submissions_open(),
            "cutoff_iso": submission_cutoff().isoformat(),
        },
    )


@health_bp.route("/health", methods=["GET"])
def health_page():
    """Render a lightweight HTML page for server health monitoring."""
    html = """
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>Health Check</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 2rem; line-height: 1.6; }
        code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; }
        .card { max-width: 700px; margin: 0 auto; padding: 1.5rem; border: 1px solid #ddd; border-radius: 12px; }
        a { color: #2563eb; }
      </style>
    </head>
    <body>
      <div class=\"card\">
        <h1>Health Check</h1>
        <p>The birthday backend is running normally.</p>
        <p>JSON endpoint: <code>/api/health</code></p>
        <p>Availability endpoint: <code>/api/availability</code></p>
        <p><a href=\"/api\">View API endpoints</a></p>
      </div>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@health_bp.route("/api", methods=["GET"])
def api_page():
    """Render a lightweight HTML page listing the primary API routes."""
    html = """
    <!doctype html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>API Endpoints</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 2rem; line-height: 1.6; }
        code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; }
        .card { max-width: 800px; margin: 0 auto; padding: 1.5rem; border: 1px solid #ddd; border-radius: 12px; }
        a { color: #2563eb; }
      </style>
    </head>
    <body>
      <div class=\"card\">
        <h1>API Endpoints</h1>
        <ul>
          <li><code>/api/health</code> — health status JSON</li>
          <li><code>/api/availability</code> — submission window status</li>
          <li><code>/api/wish</code> — submit a birthday wish</li>
          <li><code>/api/payment</code> — initiate an M-Pesa gift payment</li>
          <li><code>/api/payment-status/&lt;transaction_id&gt;</code> — check payment status</li>
        </ul>
        <p><a href=\"/health\">Return to health page</a></p>
      </div>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")
