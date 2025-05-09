#!/usr/bin/env python3
"""
Railway Auto Fix Webhook Server

Deze server ontvangt notificaties van Railway deployments
en start het auto-fix proces wanneer een deployment faalt.
"""

import os
import json
import time
import logging
import threading
import traceback
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
from datetime import datetime

# Importeer de Cursor Bridge functionaliteit
from cursor_bridge_enhanced import fetch_deployment_logs, extract_errors_from_logs, create_prompt_file, launch_cursor_with_prompt

# Laad environment variabelen
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialiseer Flask app
app = Flask(__name__)

# Configuratie
RAILWAY_TOKEN = os.environ.get('RAILWAY_TOKEN')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'jomarcello/Sigmapips-V2.4')
LOCAL_REPO_PATH = os.environ.get('LOCAL_REPO_PATH', '/tmp/railway-auto-fix-repo')
AUTH_TOKEN = os.environ.get('WEBHOOK_AUTH_TOKEN')  # Token voor webhook beveiliging

def start_cursor_fix(deployment_id=None, deployment_logs=None):
    """
    Start Cursor met het auto fix proces
    """
    try:
        logger.info(f"Starting Cursor fix process for deployment: {deployment_id}")
        
        # 1. Haal deployment logs op als we ze nog niet hebben
        if not deployment_logs and deployment_id:
            deployment_logs = fetch_deployment_logs(deployment_id)
        
        if not deployment_logs:
            logger.error("No deployment logs available, cannot proceed")
            return False
        
        # 2. Extraheer errors uit de logs
        errors = extract_errors_from_logs(deployment_logs)
        
        # 3. Maak een prompt file
        prompt_file = create_prompt_file(deployment_id, deployment_logs, errors)
        
        # 4. Start Cursor met de prompt
        repo_path = os.environ.get('LOCAL_REPO_PATH')
        success = launch_cursor_with_prompt(prompt_file, repo_path)
        
        logger.info(f"Cursor launch for auto-fix {'succeeded' if success else 'failed'}")
        return success
        
    except Exception as e:
        logger.error(f"Error in Cursor fix process: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint voor Railway"""
    try:
        # Controleer of we toegang hebben tot de Railway API
        if RAILWAY_TOKEN:
            # Maak een simpele API call om te controleren of de token werkt
            headers = {
                "Authorization": f"Bearer {RAILWAY_TOKEN}",
                "Content-Type": "application/json"
            }
            
            # GraphQL query voor een simpele check
            query = """
            query {
              me {
                id
              }
            }
            """
            
            response = requests.post(
                "https://backboard.railway.app/graphql/v2",
                headers=headers,
                json={"query": query},
                timeout=5
            )
            
            # Als de API call succesvol is, is de service gezond
            if response.status_code == 200:
                app.logger.info("Health check passed - API connection successful")
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Webhook service is running correctly and can connect to Railway API"
                })
        
        # Basic health check - als geen token of API check niet succesvol
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": "Webhook service is running"
        })
    except Exception as e:
        app.logger.warning(f"Health check warning: {str(e)}")
        # Nog steeds healthy terugsturen maar met waarschuwing
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "message": f"Webhook service is running with warning: {str(e)}"
        })

@app.route('/webhook', methods=['POST'])
def railway_webhook():
    """
    Webhook endpoint for Railway deployment notifications
    
    Verwacht JSON in het formaat:
    {
        "event": "deployment.failed", // of andere events
        "deployment": {
            "id": "deployment-id",
            "status": "FAILED"
        },
        "service": {
            "id": "service-id",
            "name": "service-name"
        }
    }
    """
    # Valideer auth token als deze is geconfigureerd
    if AUTH_TOKEN:
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {AUTH_TOKEN}":
            logger.warning("Unauthorized webhook request received")
            return jsonify({"error": "Unauthorized"}), 401
    
    # Valideer request data
    if not request.json:
        logger.warning("Invalid webhook payload - not JSON")
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    logger.info(f"Received webhook: {json.dumps(request.json)[:200]}...")
    
    try:
        data = request.json
        event_type = data.get('event')
        
        # Controleer of dit een deployment failure event is
        if event_type == 'deployment.failed':
            deployment_id = data.get('deployment', {}).get('id')
            service_name = data.get('service', {}).get('name')
            
            logger.info(f"Detected failed deployment: {deployment_id} for service: {service_name}")
            
            # Start het Cursor fix proces in een nieuwe thread
            threading.Thread(
                target=start_cursor_fix,
                args=(deployment_id, None),
                daemon=True
            ).start()
            
            return jsonify({
                "status": "processing",
                "message": f"Cursor auto-fix started for deployment {deployment_id}"
            })
        else:
            logger.info(f"Ignoring non-failure event: {event_type}")
            return jsonify({
                "status": "ignored", 
                "message": "Event is not a deployment failure"
            })
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/manual-fix', methods=['POST'])
def manual_fix():
    """
    Handmatig starten van het Cursor fix proces voor een specifieke deployment
    
    Verwacht JSON in het formaat:
    {
        "deployment_id": "deployment-id"
    }
    
    Of met logs:
    {
        "logs": "deployment logs content"
    }
    """
    # Valideer auth token
    if AUTH_TOKEN:
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f"Bearer {AUTH_TOKEN}":
            return jsonify({"error": "Unauthorized"}), 401
    
    # Valideer request data
    if not request.json:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    deployment_id = request.json.get('deployment_id')
    logs = request.json.get('logs')
    
    if not deployment_id and not logs:
        return jsonify({"error": "Either deployment_id or logs must be provided"}), 400
    
    # Start het Cursor fix proces in een nieuwe thread
    threading.Thread(
        target=start_cursor_fix,
        args=(deployment_id, logs),
        daemon=True
    ).start()
    
    return jsonify({
        "status": "processing",
        "message": f"Cursor auto-fix started for {'deployment ' + deployment_id if deployment_id else 'provided logs'}"
    })

if __name__ == "__main__":
    # Controleer of de vereiste environment variabelen aanwezig zijn
    if not RAILWAY_TOKEN:
        logger.error("Missing required RAILWAY_TOKEN environment variable")
        exit(1)
    
    # Start de webhook server
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Railway-Cursor webhook server on port {port}")
    app.run(host='0.0.0.0', port=port) 