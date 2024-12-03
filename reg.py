import os
import cv2
import numpy as np
import psycopg2
import face_recognition
import sys
from ultralytics import YOLO
import math
from datetime import datetime

class SimpleFacerec:
    def __init__(self):
        self.frame_resizing = 0.25
        self.images_folder = "images"  # Folder to store captured face images

        # Create folder if it doesn't exist
        if not os.path.exists(self.images_folder):
            os.makedirs(self.images_folder)

        # Initialize YOLO model for anti-spoofing
        self.model = YOLO('n_version_1_3.pt')  # Replace with your model's path
        self.classNames = ["fake", "real"]

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

    def check_existing_face(self, name):
        # Check if the name already exists in the images folder (based on name)
        img_path = os.path.join(self.images_folder, f"{name}.jpg")
        if os.path.exists(img_path):
            print(f"Face image for {name} already exists in the images folder. Skipping capture.")
            return True

        # Check if the face encoding already exists in the database
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT encoding FROM face_encodings WHERE name = %s", (name,))
                existing_encoding = cursor.fetchone()
                if existing_encoding:
                    print(f"Face encoding for {name} already exists in the database. Skipping registration.")
                    conn.close()
                    return True
            except Exception as e:
                print(f"Error checking face encoding in the database: {e}")
                conn.close()
                return False
        return False

    def insert_face_encoding(self, name, encoding, age, department, position, address, employee_id):
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                # Insert encoding and additional data if it doesn't already exist
                query = """
                    INSERT INTO face_encodings (name, encoding, age, department, position, address, employee_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (name, encoding.tobytes(), age, department, position, address, employee_id, datetime.now()))
                conn.commit()
                print(f"Face encoding for {name} added to the database.")
            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()

    def capture_and_register_face(self, name, age, department, position, address, employee_id):
        # Check if the face image or encoding already exists
        if self.check_existing_face(name):
            return

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Set a lower resolution for better performance
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        captured = False
        frame_count = 0
        real_face_count = 0  # To track consistency of real face detection

        while not captured:
            ret, frame = cap.read()
            if not ret:
                break

            # Resize the frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect face in the resized frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            # Perform anti-spoofing detection with YOLO
            results = self.model(frame, stream=True, verbose=False)
            is_real_face = False
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    conf = box.conf[0].item()

                    # If confidence is above a threshold, classify the face as real
                    if conf > 0.5:
                        is_real_face = True
                        break

            if is_real_face:
                real_face_count += 1

            if face_encodings and real_face_count > 3:  # We captured enough real faces
                encoding = face_encodings[0]
                img_path = os.path.join(self.images_folder, f"{name}.jpg")
                cv2.imwrite(img_path, frame)  # Save captured image to file
                self.insert_face_encoding(name, encoding, age, department, position, address, employee_id)
                captured = True
            frame_count += 1
            cv2.imshow('Register Face', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Read command-line arguments
    name = sys.argv[1]
    age = sys.argv[2]
    department = sys.argv[3]
    position = sys.argv[4]
    address = sys.argv[5]
    employee_id = sys.argv[6]

    facerec = SimpleFacerec()
    facerec.capture_and_register_face(name, age, department, position, address, employee_id)
