from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import signal
import psycopg2
from datetime import datetime

app = Flask(__name__)
CORS(app)


DB_HOST = 'dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com'
DB_PORT = '5432'
DB_NAME = 'facetwahdb'
DB_USER = 'facetwahdb_user'
DB_PASS = 'FDmm3mM50lE91i0WFlXr4VFtyKRexoFi'
current_processes = []

def get_db_connection():
 connection = psycopg2.connect(
     host=DB_HOST,
     port=DB_PORT,
     dbname=DB_NAME,
     user=DB_USER,
     password=DB_PASS
 )
 return connection

# Define the valid API key directly in the code
VALID_API_KEY = "U6sZ7EsPyJAcaOAgSVpT4mAZeNKOJOc7"

def is_valid_api_key(api_key):
    return api_key == VALID_API_KEY

@app.before_request
def require_api_key():
    protected_endpoints = ['/run-script', '/stop-script', '/register', '/employees', '/employee/<int:id>', '/attendance/remarks', '/attendance', '/mark_absent']
    
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

@app.route('/employees', methods=['GET'])
def get_employees():
    """Endpoint to fetch all employees."""
    cursor = None  # Initialize cursor to None
    connection = None  # Initialize connection to None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute('SELECT id, name, age, department, position, address, employee_id FROM face_encodings')
        rows = cursor.fetchall()

        # Convert rows into a list of dictionaries
        employees = [
            {
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'department': row[3],
                'position': row[4],
                'address': row[5],
                'employee_id': row[6]
            }
            for row in rows
        ]

        return jsonify({'status': 'success', 'employees': employees}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()  # Close cursor only if it was created
        if connection is not None:
            connection.close()  # Close connection if it was created

@app.route('/employee/<int:id>', methods=['GET'])
def get_employee_by_id(id):
    """Endpoint to fetch a specific employee by ID."""
    cursor = None  # Initialize cursor to None
    connection = None  # Initialize connection to None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute('SELECT id, name, age, department, position, address, employee_id FROM employee WHERE id = %s', (id,))
        row = cursor.fetchone()

        if row:
            employee = {
                'id': row[0],
                'name': row[1],
                'age': row[2],
                'department': row[3],
                'position': row[4],
                'address': row[5],
                'employee_id': row[6]
            }
            return jsonify({'status': 'success', 'employee': employee}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Employee not found'}), 404

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()  # Close cursor only if it was created
        if connection is not None:
            connection.close()  # Close connection if it was created

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

@app.route('/attendance', methods=['GET'])
def get_attendance_logs():
    id = request.args.get('id')  # Get the id parameter from the query string
    if not id:
        return jsonify({"error": "ID parameter is required"}), 400

    try:
        conn = psycopg2.connect(
            dbname="facetwahdb",
            user="facetwahdb_user",
            password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi",
            host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
        )
        cursor = conn.cursor()

        # Query all attendance logs for the specified ID
        cursor.execute("""
            SELECT id, name, in_time, out_time 
            FROM attendance 
            WHERE id = %s
            ORDER BY in_time ASC
        """, (id,))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        if rows:
            # Format the results as a list of dictionaries
            logs = [
                {
                    "id": row[0],
                    "name": row[1],
                    "in_time": row[2],
                    "out_time": row[3]
                }
                for row in rows
            ]
            return jsonify(logs)
        else:
            # Return a not found response if no records exist
            return jsonify({"message": "No attendance logs found for the specified ID"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/mark_absent', methods=['POST'])
def mark_absent():
    try:
        # Parse the incoming JSON request
        data = request.get_json()
        person_id = data.get('id')
        absent_date = data.get('date')  # Format: 'YYYY-MM-DD'

        # Validate input
        if not person_id or not absent_date:
            return jsonify({"error": "id and date are required"}), 400

        # Connect to the database
        conn = psycopg2.connect(
            dbname="facetwahdb",
            user="facetwahdb_user",
            password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi",
            host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
        )
        cursor = conn.cursor()

        # Check if the person exists
        cursor.execute("SELECT name FROM face_encodings WHERE id = %s", (person_id,))
        person = cursor.fetchone()
        if not person:
            return jsonify({"error": "Person with the specified ID does not exist"}), 404

        name = person[0]  # Fetch the name of the person

        # Insert absent log into the attendance table
        cursor.execute("""
            INSERT INTO attendance (id, name, in_time, out_time, onleave, status)
            VALUES (%s, %s, %s, NULL, NULL, 'absent')
        """, (person_id, name, absent_date))

        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()

        # Return a success message
        return jsonify({"message": f"{name} marked as absent on {absent_date}."}), 200

    except Exception as e:
        # Handle errors
        return jsonify({"error": str(e)}), 500
    
@app.route('/attendance/remarks', methods=['GET'])
def attendance_remarks():
    """
    Fetch attendance remarks for a specific date or all records.
    Query Parameters:
        - date (optional): Filter results for a specific date (format: YYYY-MM-DD).
    """
    date = request.args.get('date')  # Get the optional 'date' parameter

    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="facetwahdb",
            user="facetwahdb_user",
            password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi",
            host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
        )
        cursor = conn.cursor()

        # Define the query based on whether a date is provided
        if date:
            try:
                # Validate date format
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

            query = """
                SELECT name, remarks, in_time
                FROM attendance
                WHERE DATE(in_time) = %s
            """
            cursor.execute(query, (date,))
        else:
            query = "SELECT name, remarks, in_time FROM attendance"
            cursor.execute(query)

        # Fetch and format the results
        records = cursor.fetchall()
        result = [
            {"name": record[0], "remarks": record[1], "in_time": record[2].strftime("%Y-%m-%d %H:%M:%S")}
            for record in records
        ]

        # Close the connection
        cursor.close()
        conn.close()

        # Return the formatted result
        return jsonify(result), 200

    except Exception as e:
        print(f"Error fetching attendance remarks: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
