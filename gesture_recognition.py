import cv2
import mediapipe as mp
import pyautogui
import time
import os
from datetime import datetime
import base64
from flask_socketio import SocketIO

class GestureRecognition:
    def __init__(self, screenshot_folder, socketio, bucket):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.screenshot_folder = screenshot_folder
        self.socketio = socketio
        self.bucket = bucket
        self.cap = cv2.VideoCapture(0)
        self.hands = self.mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.last_gesture_time = 0
        self.gesture_cooldown = 2  # 2 seconds cooldown between gestures

    def is_o_gesture(self, hand_landmarks):
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        index_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        distance = ((thumb_tip.x - index_finger_tip.x) ** 2 + (thumb_tip.y - index_finger_tip.y) ** 2) ** 0.5
        return distance < 0.05

    def is_v_gesture(self, hand_landmarks):
        index_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        ring_finger_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        return (index_finger_tip.y < ring_finger_tip.y and
                middle_finger_tip.y < ring_finger_tip.y and
                abs(index_finger_tip.y - middle_finger_tip.y) < 0.02)

    def take_screenshot(self, user_id):
        screenshot = pyautogui.screenshot()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{user_id}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_folder, filename)
        screenshot.save(filepath)

        # Upload to Firebase Storage
        blob = self.bucket.blob(filename)
        blob.upload_from_filename(filepath)

        # Get the public URL
        blob.make_public()
        public_url = blob.public_url

    # Return the URL (do not emit anything here)
        return public_url




    def get_latest_screenshot(self, user_id):
        blobs = self.bucket.list_blobs(prefix=f"screenshot_{user_id}")
        latest_blob = max(blobs, key=lambda x: x.time_created, default=None)
        if latest_blob:
            return latest_blob.public_url
        return None

    def process_frame(self, frame, user_id):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb_frame)

        gesture = None
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                current_time = time.time()
                if current_time - self.last_gesture_time > self.gesture_cooldown:
                    if self.is_o_gesture(hand_landmarks):
                        gesture = 'O'
                        print(f"O gesture detected by user {user_id}")
                        screenshot_url = self.take_screenshot(user_id)
                        print(f"Screenshot taken: {screenshot_url}")
                        self.socketio.emit('screenshot_taken', {'userId': user_id, 'url': screenshot_url})
                        self.last_gesture_time = current_time
                    elif self.is_v_gesture(hand_landmarks):
                        print(f"V gesture detected by user {user_id}")
                        # Emit an event to request the latest screenshot from the other peer
                        self.socketio.emit('v_gesture_detected', {'userId': user_id})
                        self.last_gesture_time = current_time


        return frame, gesture



    def run(self, user_id):
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame, gesture = self.process_frame(frame, user_id)

            cv2.imshow("Hand Gesture Recognition", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()