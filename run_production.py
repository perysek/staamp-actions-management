"""
Production entry point — run via NSSM Windows Service.
Waitress serves Flask on 0.0.0.0:PORT so all LAN clients can reach it.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from waitress import serve
from app import create_app

PORT = int(os.environ.get("SERVER_PORT", 8093))

if __name__ == "__main__":
    app = create_app()
    print(f"Starting DMC Validator production server on port {PORT}")
    serve(
        app,
        host="0.0.0.0",
        port=PORT,
        threads=4,
        connection_limit=100,
        channel_timeout=60,
        url_scheme="http",
    )
