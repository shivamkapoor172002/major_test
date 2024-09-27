from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import os
from gesture_recognition import GestureRecognition
import threading
import firebase_admin
from firebase_admin import credentials, storage

# Initialize Flask and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Firebase
cred = credentials.Certificate("firebase.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'screenshot-d87e4.appspot.com'
})
bucket = storage.bucket()

# Define folder to save screenshots
screenshot_folder = "screenshot"
os.makedirs(screenshot_folder, exist_ok=True)

# Initialize GestureRecognition with the screenshot folder
gesture_recognition = GestureRecognition(screenshot_folder, socketio, bucket)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@socketio.on('start_gesture_recognition')
def handle_start_gesture_recognition(data):
    user_id = data['userId']
    
    def gesture_recognition_thread():
        gesture_recognition.run(user_id)

    thread = threading.Thread(target=gesture_recognition_thread)
    thread.daemon = True
    thread.start()
@socketio.on('screenshot_taken')
def handle_screenshot_taken(data):
    user_id = data['userId']
    screenshot_url = gesture_recognition.take_screenshot(user_id)
    # Store the screenshot URL in a global/user-specific cache or Firebase
    # Do NOT send it to User B yet

@socketio.on('request_latest_screenshot')
def handle_request_latest_screenshot(data):
    requester_id = data['requesterId']
    target_id = data['targetId']
    
    # Retrieve the stored screenshot URL from Firebase (or your cache)
    latest_screenshot = gesture_recognition.get_latest_screenshot(target_id)
    
    if latest_screenshot:
        # Now send the screenshot to the requesting user
        socketio.emit('receive_screenshot', {
            'image': latest_screenshot,
            'fromUserId': target_id,
            'toUserId': requester_id
        }, room=requester_id)  # Send to User B only when requested


if __name__ == '__main__':
    socketio.run(app, debug=True)
