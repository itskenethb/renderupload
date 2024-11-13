import psycopg2
import os
import glob
import face_recognition
import cv2
import numpy as np
from datetime import datetime

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.frame_resizing = 0.25

    def connect_db(self):
        """
        Connect to PostgreSQL Database.
        """
        try:
            conn = psycopg2.connect(
                dbname="new_database_name", 
                user="Kenneth_Baynas", 
                password="", 
                host="localhost"
            )
            return conn
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            return None

    def insert_face_encoding(self, name, encoding):
        """
        Insert or update face encoding in the database.
        """
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                # Check if the name already exists in the table
                cursor.execute("SELECT name FROM face_encodings WHERE name = %s", (name,))
                existing_name = cursor.fetchone()

                if existing_name:
                    # Skip insertion if the name already exists
                    pass
                else:
                    query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s)"
                    print(f"Logging face: {name}")  # Debugging: Ensure face name is not empty
                    cursor.execute(query, (name, encoding.tobytes()))  # Store encoding as bytes
                    conn.commit()

            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()

    def load_encoding_images(self, images_path):
        """
        Load and encode images from the provided folder path.
        """
        images_path = glob.glob(os.path.join(images_path, "*.*"))
        print(f"{len(images_path)} encoding images found.")

        for img_path in images_path:
            img = cv2.imread(img_path)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            basename = os.path.basename(img_path)
            (filename, ext) = os.path.splitext(basename)

            # Get face encoding
            img_encoding = face_recognition.face_encodings(rgb_img)[0]

            # Add encoding and name to lists
            self.known_face_encodings.append(img_encoding)
            self.known_face_names.append(filename)

            # Insert encoding into the database
            self.insert_face_encoding(filename, img_encoding)

        print("Encoding images loaded")

    def detect_known_faces(self, frame):
        """
        Detect known faces in a given frame.
        """
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            face_names.append(name)

        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names


# Function to log recognized faces in the database once per day
def log_recognized_face(name, logged_faces_today):
    # Skip logging if the face has already been logged today or if it is "Unknown"
    if name in logged_faces_today or name == "Unknown":
        return  # Face has already been logged today or is unrecognized

    # Connect to the database
    conn = psycopg2.connect(
        dbname="new_database_name", 
        user="Kenneth_Baynas", 
        password="", 
        host="localhost"
    )
    cursor = conn.cursor()

    # Get today's date in the format YYYY-MM-DD
    today_date = datetime.now().date()

    # Check if the face has already been logged today
    cursor.execute("""
        SELECT name FROM recognized_faces
        WHERE name = %s AND DATE(recognized_at) = %s
    """, (name, today_date))
    
    if cursor.fetchone():
        pass  # Face already logged today, no need to log again
    else:
        # Log the face if not already logged today
        query = "INSERT INTO recognized_faces (name, recognized_at) VALUES (%s, %s)"
        cursor.execute(query, (name, datetime.now()))
        conn.commit()

        # Add name to the set of logged faces for today
        logged_faces_today.add(name)

    cursor.close()
    conn.close()

# Initialize a set to keep track of the faces logged today
logged_faces_today = set()

# Initialize the SimpleFacerec instance
sfr = SimpleFacerec()
sfr.load_encoding_images("images/")  # Load images from 'images/' folder

# Open video capture
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    # Detect Faces
    face_locations, face_names = sfr.detect_known_faces(frame)

    # Loop through detected faces
    for face_loc, name in zip(face_locations, face_names):
        y1, x2, y2, x1 = face_loc
        width = x2 - x1
        height = y2 - y1

        # Only consider the face if it is not too narrow (likely side view)
        if 0.75 <= width / height <= 1.3 and name != "Unknown":  # Aspect ratio for full front faces
            log_recognized_face(name, logged_faces_today)
            # Display the face with name
            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)

    # Show the video feed
    cv2.imshow("Frame", frame)

    # Break on ESC key press
    key = cv2.waitKey(1)
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()