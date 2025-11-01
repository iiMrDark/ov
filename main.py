#!/usr/bin/env python3
"""
Main entry point for Replit
Starts the Overload API Server
"""

from api_server import app
import os

if __name__ == '__main__':
    # Get host and port from environment variables (Replit compatibility)
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 Starting Overload API Server for Replit...")
    print("📡 Available endpoints:")
    print("  POST /api/attack/<site_url> - Start attack on target")
    print("  POST /api/attack/stop - Stop all running attacks")
    print("  GET  /api/attack/status - Get status of running attacks")
    print("  GET  /api/health - Health check")
    print(f"🌐 Server running on http://{host}:{port}")
    print("✅ Ready for Replit webview!")
    
    # Start the Flask app with Replit-optimized settings
    app.run(
        host=host, 
        port=port, 
        debug=False, 
        threaded=True,
        use_reloader=False  # Disable reloader for Replit
    )