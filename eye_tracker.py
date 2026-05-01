import cv2
import mediapipe as mp
import numpy as np
import time
import csv

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

MOUTH_POINTS = [13, 14, 78, 308]
EYEBROW_POINTS = [70, 63, 105, 66, 107]

def eye_aspect_ratio(landmarks, eye_points):
    p1 = np.array([landmarks[eye_points[0]].x, landmarks[eye_points[0]].y])
    p2 = np.array([landmarks[eye_points[1]].x, landmarks[eye_points[1]].y])
    p3 = np.array([landmarks[eye_points[2]].x, landmarks[eye_points[2]].y])
    p4 = np.array([landmarks[eye_points[3]].x, landmarks[eye_points[3]].y])
    p5 = np.array([landmarks[eye_points[4]].x, landmarks[eye_points[4]].y])
    p6 = np.array([landmarks[eye_points[5]].x, landmarks[eye_points[5]].y])

    vertical = np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p1 - p4)

    return vertical / (2.0 * horizontal)

def start_system():
    cap = cv2.VideoCapture(0)

    blink_count = 0
    blink_threshold = 0.25
    blink_frames = 0

    start_time = time.time()
    ear_values = []
    movement_scores = []
    prev_landmarks = None

    csv_file = open("data/session_data.csv", mode="w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Time", "Blink_Rate", "Eye_Engagement", "Facial_Activity", "Risk_Level"])

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        avg_ear = 0
        avg_movement = 0

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:

                left_ear = eye_aspect_ratio(face_landmarks.landmark, LEFT_EYE)
                right_ear = eye_aspect_ratio(face_landmarks.landmark, RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0

                if ear < blink_threshold:
                    blink_frames += 1
                else:
                    if blink_frames > 1:
                        blink_count += 1
                    blink_frames = 0

                ear_values.append(ear)
                if len(ear_values) > 100:
                    ear_values.pop(0)
                avg_ear = sum(ear_values) / len(ear_values)

                current_points = []
                for idx in MOUTH_POINTS + EYEBROW_POINTS:
                    point = face_landmarks.landmark[idx]
                    current_points.append([point.x, point.y])

                current_points = np.array(current_points)

                if prev_landmarks is not None:
                    movement = np.linalg.norm(current_points - prev_landmarks)
                    movement_scores.append(movement)
                    if len(movement_scores) > 100:
                        movement_scores.pop(0)

                prev_landmarks = current_points

                if movement_scores:
                    avg_movement = sum(movement_scores) / len(movement_scores)

        elapsed_time = time.time() - start_time
        blink_rate = (blink_count / elapsed_time) * 60 if elapsed_time > 0 else 0

        # ---------------- RISK ENGINE ----------------
        risk_score = 0

        if blink_rate > 25:
            risk_score += 1
        if avg_ear < 0.22:
            risk_score += 1
        if avg_movement < 0.002:
            risk_score += 1

        if risk_score == 0:
            risk_level = "Low"
            color = (0, 255, 0)
        elif risk_score == 1:
            risk_level = "Mild"
            color = (0, 255, 255)
        elif risk_score == 2:
            risk_level = "Moderate"
            color = (0, 165, 255)
        else:
            risk_level = "Elevated"
            color = (0, 0, 255)

        # ---------------- DISPLAY ----------------
        cv2.putText(frame, f"Blinks: {blink_count}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.putText(frame, f"Blink Rate: {int(blink_rate)}", (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        cv2.putText(frame, f"Eye Engagement: {round(avg_ear, 2)}", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        cv2.putText(frame, f"Facial Activity: {round(avg_movement, 4)}", (30, 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 100, 255), 2)

        cv2.putText(frame, f"Risk Level: {risk_level}", (30, 210),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

        current_time = round(time.time() - start_time, 2)

        csv_writer.writerow([
            current_time,
            round(blink_rate, 2),
            round(avg_ear, 4),
            round(avg_movement, 6),
            risk_level
        ])

        cv2.imshow("Mental Health Monitoring System", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    csv_file.close()
    cv2.destroyAllWindows()
