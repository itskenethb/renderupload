import os
import cv2
import numpy as np
import psycopg2
from datetime import datetime
import face_recognition
import sys

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.frame_resizing = 0.25
        self.images_folder = "images"  # Folder to store captured face images

        # Create folder if it doesn't exist
        if not os.path.exists(self.images_folder):
            os.makedirs(self.images_folder)

    def connect_db(self):
        try:
            conn = psycopg2.connect(
                dbname="new_database_name",
                user="Kenneth_Baynas",
                password="",  # Add your password
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
                # Check if the name already exists in the database
                cursor.execute("SELECT name FROM face_encodings WHERE name = %s", (name,))
                existing_name = cursor.fetchone()
                
                if existing_name:
                    print(f"Face for {name} already exists. Skipping insertion.")
                else:
                    query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s)"
                    cursor.execute(query, (name, encoding.tobytes()))
                    conn.commit()
                    print(f"Face encoding for {name} added to the database.")

            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()

    def capture_and_register_face(self, name):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Set a lower resolution for better performance
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        captured = False

        # Check if the name already exists in the images folder (based on name)
        img_path = os.path.join(self.images_folder, f"{name}.jpg")
        if os.path.exists(img_path):
            print(f"Face for {name} already exists. Skipping capture.")
            return

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

            if face_encodings:
                # Assume first detected face is the intended face
                encoding = face_encodings[0]
                # Scale back face locations to full size
                y1, x2, y2, x1 = [int(coord / self.frame_resizing) for coord in face_locations[0]]

                # Save image to /images folder only if it doesn't exist
                img_path = os.path.join(self.images_folder, f"{name}.jpg")
                if not os.path.exists(img_path):
                    cv2.imwrite(img_path, frame[y1:y2, x1:x2])
                    print(f"Face image saved at {img_path}")

                # Store encoding in the database
                self.insert_face_encoding(name, encoding)
                print(f"Face registered for {name}.")
                captured = True

                # Display confirmation on screen
                cv2.putText(frame, "Face Registered", (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Frame", frame)
                cv2.waitKey(1000)  # Pause for confirmation display

            # Display the live feed
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) == 27:  # Press ESC to exit capture
                break

        cap.release()
        cv2.destroyAllWindows()

# Main registration process
if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]  # Get the name from command-line argument
        sfr = SimpleFacerec()
        sfr.capture_and_register_face(name)
    else:
        print("Please provide a name as a command-line argument.")
