import cv2
import math
import os
import glob
import psycopg2
import numpy as np
import face_recognition
from datetime import datetime
from ultralytics import YOLO
import cvzone

# Configuration and model loading
confidence = 0.8
model = YOLO('n_version_1_3.pt')
classNames = ["fake", "real"]
frame_resizing = 0.25

# Initialize SimpleFacerec class for face recognition
class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

    def connect_db(self):
        try:
            conn = psycopg2.connect(
                dbname="facetwahdb",
                user="facetwahdb_user",
                password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi",
                host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
            )
            return conn
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            return None

    def insert_face_encoding(self, name, encoding):
        conn = self.connect_db()
        person_id = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM face_encodings WHERE name = %s", (name,))
                existing_name = cursor.fetchone()
                if not existing_name:
                    query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s) RETURNING id"
                    cursor.execute(query, (name, encoding.tobytes()))
                    person_id = cursor.fetchone()[0]  # Get the inserted person's id
                    conn.commit()
                else:
                    person_id = existing_name[0]  # Use existing person's id if the name already exists
            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()
        return person_id

    def load_encoding_images(self, images_path):
        images_path = glob.glob(os.path.join(images_path, "*.*"))
        print(f"{len(images_path)} encoding images found.")
        for img_path in images_path:
            img = cv2.imread(img_path)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            basename = os.path.basename(img_path)
            filename, ext = os.path.splitext(basename)
            img_encoding = face_recognition.face_encodings(rgb_img)[0]
            self.known_face_encodings.append(img_encoding)
            self.known_face_names.append(filename)
            self.insert_face_encoding(filename, img_encoding)  # Insert encoding into the database
        print("Encoding images loaded")

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=frame_resizing, fy=frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_names = []

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)

            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index] and face_distances[best_match_index] < 0.5:
                    name = self.known_face_names[best_match_index]
            face_names.append(name)

        face_locations = np.array(face_locations) / frame_resizing
        return face_locations.astype(int), face_names

# Function to log attendance
def log_attendance(name):
    if name == "Unknown":
        return
    try:
        conn = psycopg2.connect(
            dbname="facetwahdb",
            user="facetwahdb_user",
            password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi",
            host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
        )
        cursor = conn.cursor()

        today_date = datetime.now().date()
        cursor.execute("""
            SELECT id, in_time, out_time FROM attendance
            WHERE name = %s AND DATE(in_time) = %s
        """, (name, today_date))

        existing_record = cursor.fetchone()
        if existing_record:
            cursor.execute("""
                UPDATE attendance
                SET out_time = %s
                WHERE name = %s AND DATE(in_time) = %s
            """, (datetime.now(), name, today_date))
            conn.commit()
        else:
            cursor.execute("SELECT id FROM face_encodings WHERE name = %s", (name,))
            person_id = cursor.fetchone()
            if person_id:
                person_id = person_id[0]
                cursor.execute("""
                    INSERT INTO attendance (name, in_time, id)
                    VALUES (%s, %s, %s)
                """, (name, datetime.now(), person_id))
                conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error logging attendance: {e}")

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 500)
cap.set(4, 480)

# Initialize SimpleFacerec and load face encodings
sfr = SimpleFacerec()
sfr.load_encoding_images("images/")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, stream=True, verbose=False)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1
            conf = math.ceil((box.conf[0] * 100)) / 100
            cls = box.cls[0]
            name = classNames[int(cls)].upper()

            if conf > confidence:
                color = (0, 255, 0) if name == "REAL" else (0, 0, 255)
                cvzone.cornerRect(frame, (x1, y1, w, h), colorC=color, colorR=color)
                label_y_position = max(35, y1 - 50)
                cvzone.putTextRect(frame, f'{name} {int(conf*100)}%', (max(0, x1), label_y_position), scale=2, thickness=2, colorR=color)

                if name == "REAL":
                    face_locations, face_names = sfr.detect_known_faces(frame)
                    for face_loc, face_name in zip(face_locations, face_names):
                        top, right, bottom, left = face_loc
                        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 0), 2)
                        cvzone.putTextRect(frame, face_name, (left, top - 10), scale=2, thickness=2, colorR=(255, 0, 0))
                        log_attendance(face_name)

    cv2.imshow("Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
