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
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM face_encodings WHERE name = %s", (name,))
                existing_name = cursor.fetchone()
                if not existing_name:
                    query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s)"
                    cursor.execute(query, (name, encoding.tobytes()))
                    conn.commit()
            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()

    def load_encoding_images(self, images_path):
        images_path = glob.glob(os.path.join(images_path, "*.*"))
        for img_path in images_path:
            img = cv2.imread(img_path)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            basename = os.path.basename(img_path)
            (filename, ext) = os.path.splitext(basename)
            img_encoding = face_recognition.face_encodings(rgb_img)[0]
            self.known_face_encodings.append(img_encoding)
            self.known_face_names.append(filename)
            self.insert_face_encoding(filename, img_encoding)
        print("Encoding images loaded")

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_names = []

        try:
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                name = "Unknown"
                if face_distances.size > 0:  # Check if distances are found
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                face_names.append(name)
        except Exception as e:
            print(f"Error in face detection: {e}")
            face_names.append("Unknown")

        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names


def log_recognized_face(name, logged_faces_today):
    if name in logged_faces_today or name == "Unknown":
        return
    conn = psycopg2.connect(
        dbname="new_database_name", 
        user="Kenneth_Baynas", 
        password="", 
        host="localhost"
    )
    cursor = conn.cursor()
    today_date = datetime.now().date()
    cursor.execute("""
        SELECT name FROM recognized_faces
        WHERE name = %s AND DATE(recognized_at) = %s
    """, (name, today_date))
    if not cursor.fetchone():
        query = "INSERT INTO recognized_faces (name, recognized_at) VALUES (%s, %s)"
        cursor.execute(query, (name, datetime.now()))
        conn.commit()
        logged_faces_today.add(name)
    cursor.close()
    conn.close()

logged_faces_today = set()
sfr = SimpleFacerec()
sfr.load_encoding_images("images/")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error reading from camera.")
        break

    try:
        face_locations, face_names = sfr.detect_known_faces(frame)
        for face_loc, name in zip(face_locations, face_names):
            y1, x2, y2, x1 = face_loc
            width = x2 - x1
            height = y2 - y1
            if 0.75 <= width / height <= 1.3:
                log_recognized_face(name, logged_faces_today)
                cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)
    except Exception as e:
        print(f"Error during face recognition loop: {e}")
        cv2.putText(frame, "Unknown", (10, 30), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Frame", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
