#!/usr/bin/env python3
"""
MLflow Webhook Handler for Model Promotion.

This script receives webhooks from MLflow when a model is promoted to Production
and triggers a GitHub Actions deployment workflow.

Setup:
    1. Configure MLflow Registry Webhooks (Admin → Model Registry → Webhooks)
    2. Set webhook URL to: https://api.github.com/repos/YOUR_ORG/YOUR_REPO/dispatches
    3. Set request headers:
       - Authorization: token YOUR_GITHUB_TOKEN
       - Content-Type: application/json
    4. Payload template:
       {"event_name": "model_promoted", "model_name": "{{model_name}}", "model_version": "{{model_version}}"}

Usage (for testing):
    python mlflow_webhook_handler.py --port 5001 --github-token YOUR_TOKEN
    
Environment Variables:
    MLFLOW_WEBHOOK_SECRET: Shared secret for webhook validation (optional)
    GITHUB_TOKEN: GitHub personal access token for triggering workflows
    GITHUB_REPO: Repository in format "owner/repo"
"""

import json
import os
import sys
import hashlib
import hmac
import argparse
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature using HMAC-SHA256."""
    if not secret:
        return True  # Skip verification if no secret configured
    
    expected_signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def trigger_github_workflow(
    github_token: str,
    repository: str,
    model_name: str,
    model_version: str
) -> Tuple[bool, str]:
    """Trigger GitHub Actions workflow via repository dispatch."""
    try:
        import requests
    except ImportError:
        logger.error("requests library not installed. Run: pip install requests")
        return False, "requests not installed"
    
    owner, repo = repository.split('/')
    
    url = f"https://api.github.com/repos/{owner}/{repo}/dispatches"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {github_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'event_type': 'model-promoted',
        'client_payload': {
            'model_name': model_name,
            'model_version': str(model_version),
            'triggered_at': datetime.utcnow().isoformat()
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"✓ Workflow triggered successfully for {model_name} v{model_version}")
            return True, "Workflow triggered"
        else:
            logger.error(f"Failed to trigger workflow: {response.status_code} - {response.text}")
            return False, f"GitHub API error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error triggering workflow: {e}")
        return False, str(e)


def handle_model_promotion(
    event_data: Dict[str, Any],
    github_token: str,
    repository: str
) -> Tuple[bool, str]:
    """Handle model promotion event."""
    
    logger.info(f"Received event: {json.dumps(event_data)}")
    
    # Extract model information
    model_name = event_data.get('model_name')
    model_version = event_data.get('model_version')
    
    if not model_name or not model_version:
        logger.error("Missing model_name or model_version in event")
        return False, "Missing required fields"
    
    logger.info(f"Processing model promotion: {model_name} v{model_version}")
    
    # Trigger GitHub workflow
    success, message = trigger_github_workflow(
        github_token=github_token,
        repository=repository,
        model_name=model_name,
        model_version=model_version
    )
    
    if success:
        logger.info(f"✓ Successfully processed promotion for {model_name} v{model_version}")
        return True, message
    else:
        logger.error(f"✗ Failed to process promotion: {message}")
        return False, message


def create_flask_app(github_token: str, repository: str, webhook_secret: str = None):
    """Create Flask application for webhook handling."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        logger.error("Flask not installed. Run: pip install flask")
        return None
    
    app = Flask(__name__)
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({'status': 'healthy'}), 200
    
    @app.route('/webhook/mlflow', methods=['POST'])
    def webhook_handler():
        """Handle MLflow promotion webhooks."""
        
        try:
            # Verify signature if secret is configured
            if webhook_secret:
                signature = request.headers.get('X-Signature', '')
                payload = request.get_data(as_text=True)
                
                if not verify_webhook_signature(payload, signature, webhook_secret):
                    logger.warning("Invalid webhook signature")
                    return jsonify({'error': 'Invalid signature'}), 401
            
            # Parse JSON payload
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No JSON payload'}), 400
            
            # Handle different event types
            event_name = data.get('event_name', data.get('event_type'))
            
            if event_name in ['model_promoted', 'model-promoted']:
                success, message = handle_model_promotion(
                    event_data=data,
                    github_token=github_token,
                    repository=repository
                )
                
                if success:
                    return jsonify({
                        'status': 'success',
                        'message': message,
                        'model_name': data.get('model_name'),
                        'model_version': data.get('model_version')
                    }), 202
                else:
                    return jsonify({
                        'status': 'error',
                        'message': message
                    }), 500
            else:
                logger.info(f"Ignoring event type: {event_name}")
                return jsonify({'status': 'ignored'}), 200
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return jsonify({'error': 'Invalid JSON'}), 400
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500
    
    return app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='MLflow Webhook Handler for GitHub Actions Deployment'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('PORT', 5001)),
        help='Port to listen on (default: 5001)'
    )
    parser.add_argument(
        '--host',
        default=os.getenv('HOST', '0.0.0.0'),
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--github-token',
        default=os.getenv('GITHUB_TOKEN'),
        help='GitHub personal access token'
    )
    parser.add_argument(
        '--github-repo',
        default=os.getenv('GITHUB_REPO'),
        help='GitHub repository (owner/repo)'
    )
    parser.add_argument(
        '--webhook-secret',
        default=os.getenv('MLFLOW_WEBHOOK_SECRET'),
        help='Shared secret for webhook validation'
    )
    parser.add_argument(
        '--trigger-workflow',
        action='store_true',
        help='Test: Trigger a sample workflow'
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    if not args.github_token:
        print("Error: --github-token or GITHUB_TOKEN environment variable required")
        print("  Create token at: https://github.com/settings/tokens")
        print("  Required scopes: repo (for private repos) or public_repo (for public repos)")
        sys.exit(1)
    
    if not args.github_repo:
        print("Error: --github-repo or GITHUB_REPO environment variable required")
        print("  Format: owner/repo")
        sys.exit(1)
    
    # Test mode: trigger a sample workflow
    if args.trigger_workflow:
        print(f"Testing workflow trigger for repo {args.github_repo}...")
        success, message = trigger_github_workflow(
            github_token=args.github_token,
            repository=args.github_repo,
            model_name='test-model',
            model_version='1'
        )
        if success:
            print(f"✓ {message}")
        else:
            print(f"✗ {message}")
        sys.exit(0 if success else 1)
    
    # Create and run Flask app
    logger.info("=" * 60)
    logger.info("MLflow Webhook Handler - Starting")
    logger.info("=" * 60)
    logger.info(f"Listening on {args.host}:{args.port}")
    logger.info(f"Repository: {args.github_repo}")
    logger.info(f"Webhook endpoint: http://localhost:{args.port}/webhook/mlflow")
    logger.info(f"Health check: http://localhost:{args.port}/health")
    logger.info("=" * 60)
    
    app = create_flask_app(
        github_token=args.github_token,
        repository=args.github_repo,
        webhook_secret=args.webhook_secret
    )
    
    if not app:
        sys.exit(1)
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)


if __name__ == '__main__':
    main()
