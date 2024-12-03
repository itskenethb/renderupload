from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import signal

app = Flask(__name__)
CORS(app)

current_processes = []

# Define the valid API key directly in the code
VALID_API_KEY = "U6sZ7EsPyJAcaOAgSVpT4mAZeNKOJOc7"

def is_valid_api_key(api_key):
    return api_key == VALID_API_KEY

@app.before_request
def require_api_key():
    protected_endpoints = ['/run-script', '/stop-script', '/register-face']
    
    if request.path in protected_endpoints:
        api_key = request.headers.get('X-API-Key')
        if not api_key or not is_valid_api_key(api_key):
            return jsonify({'status': 'error', 'message': 'Invalid or missing API key'}), 403

def run_python_script(script_name, args=None):
    """Helper function to run a Python script and return its output."""
    try:
        if args is None:
            args = []
        process = subprocess.Popen(
            ['python3', script_name] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        current_processes.append(process)
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return {'status': 'success', 'output': stdout.decode()}
        else:
            return {'status': 'error', 'output': stderr.decode()}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/run-script', methods=['POST'])
def run_script():
    """Endpoint to run the main Python script."""
    result = run_python_script('main.py')
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/stop-script', methods=['POST'])
def stop_script():
    """Endpoint to stop all running scripts."""
    try:
        if current_processes:
            for process in current_processes:
                try:
                    os.kill(process.pid, signal.SIGTERM)  # Terminate the process
                    print(f"Terminated process PID: {process.pid}")
                except ProcessLookupError:
                    print(f"Process {process.pid} already terminated.")
            current_processes.clear()
            return jsonify({'status': 'success', 'message': 'All scripts terminated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'No scripts are running'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/register', methods=['POST'])
def register_face():
    """Endpoint to register a face, run the registration script."""
    try:
        # Extract the data from the request
        data = request.json
        name = data.get('name', '')
        age = data.get('age', '')
        department = data.get('department', '')
        position = data.get('position', '')
        address = data.get('address', '')
        employee_id = data.get('employee_id', '')

        # Validate inputs
        if not all([name, age, department, position, address, employee_id]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400

        # Run the registration script with the provided name and other details
        result = run_python_script('reg.py', [name, age, department, position, address, employee_id])

        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'output': f"Face registration script output: {result['output']}"
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Registration script failed',
                'output': result['output']
            }), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
