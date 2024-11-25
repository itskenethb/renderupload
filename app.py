from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import signal

app = Flask(__name__)
CORS(app)

# Store the process objects for later termination
current_processes = []

@app.route('/run-script', methods=['POST'])
def run_script():
    try:
        # Run the Python script using subprocess
        process = subprocess.Popen(
            ['python3', 'main.py'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        current_processes.append(process)  # Store the process
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return jsonify({'status': 'success', 'output': stdout.decode()})
        else:
            return jsonify({'status': 'error', 'output': stderr.decode()}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop-script', methods=['POST'])
def stop_script():
    try:
        if current_processes:
            # Iterate through the list of processes and terminate them
            for process in current_processes:
                try:
                    os.kill(process.pid, signal.SIGTERM)  # Terminate the process
                    print(f"Terminated process PID: {process.pid}")
                except ProcessLookupError:
                    print(f"Process {process.pid} already terminated.")
            current_processes.clear()  # Clear the list of processes after termination
            return jsonify({'status': 'success', 'message': 'All scripts terminated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'No scripts are running'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/register-face', methods=['POST'])
def register_face():
    try:
        data = request.json
        name = data.get('name', '')

        if not name:
            return jsonify({'status': 'error', 'message': 'Name is required'}), 400

        # Run the first registration Python script with the name as an argument
        first_process = subprocess.Popen(
            ['python3', 'simple_facereg.py', name], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        current_processes.append(first_process)  # Store the process
        
        stdout1, stderr1 = first_process.communicate()
        
        # Check if the first process was successful before running the second script
        if first_process.returncode == 0:
            # Run the second Python script
            second_process = subprocess.Popen(
                ['python3', 'simple_facereg.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            current_processes.append(second_process)  # Store the second process

            stdout2, stderr2 = second_process.communicate()

            if second_process.returncode == 0:
                return jsonify({
                    'status': 'success', 
                    'output': f"First script output: {stdout1.decode()}\nSecond script output: {stdout2.decode()}"
                })
            else:
                return jsonify({
                    'status': 'error', 
                    'message': f"First script succeeded but second script failed", 
                    'output': stderr2.decode()
                }), 400
        else:
            return jsonify({
                'status': 'error', 
                'message': 'First script failed', 
                'output': stderr1.decode()
            }), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/register-face-simple', methods=['POST'])
def register_face_simple():
    try:
        # Run the second script independently
        process = subprocess.Popen(
            ['python3', '/simple_facereg.py'],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        current_processes.append(process)  # Store the process
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return jsonify({'status': 'success', 'output': stdout.decode()})
        else:
            return jsonify({'status': 'error', 'output': stderr.decode()}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)