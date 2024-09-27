import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js";
import { getFirestore, doc, setDoc, onSnapshot, deleteDoc } from "https://www.gstatic.com/firebasejs/9.22.0/firebase-firestore.js";

const firebaseConfig = { 
    apiKey: "AIzaSyAL7bggiQ82831f5p0QK1ijgNVT-0t5xI0", 
    authDomain: "screenshot-d87e4.firebaseapp.com", 
    projectId: "screenshot-d87e4", 
    storageBucket: "screenshot-d87e4", 
    messagingSenderId: "358248125741", 
    appId: "1:358248125741:web:9e5e49e1154aa62aef6fa4", 
    measurementId: "G-Y1C6JKVD9R"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

let peer;
let sessionId;
let userId;
const socket = io();

function generateId() {
    return Math.random().toString(36).substring(2, 15);
}

function log(message) {
    console.log(message);
    document.getElementById('log').innerText += message + '\n';
}

function showNotification(message) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.classList.add('show');
    setTimeout(() => {
        notification.classList.remove('show');
    }, 2000);
}

async function createPeer(isInitiator) {
    if (peer) {
        peer.destroy();
    }

    peer = new SimplePeer({ initiator: isInitiator, trickle: false });

    peer.on('signal', async data => {
        log('Signal data generated');
        const signalingDoc = doc(db, 'signaling', sessionId);
        await setDoc(signalingDoc, { [isInitiator ? 'offer' : 'answer']: JSON.stringify(data) });
    });

    peer.on('connect', () => {
        log('Peer connected');
        document.getElementById('sendMessage').disabled = false;
    });

    peer.on('data', data => {
        const receivedData = JSON.parse(data);
        if (receivedData.type === 'screenshot') {
            log('Received screenshot');
            document.getElementById('latestScreenshot').src = receivedData.content;
        } else if (receivedData.type === 'message') {
            log('Received message: ' + receivedData.content);
            showNotification('New message received!');
        }
    });

    peer.on('error', err => {
        log('Peer error: ' + err);
    });

    onSnapshot(doc(db, 'signaling', sessionId), snapshot => {
        const data = snapshot.data();
        if (data) {
            if (isInitiator && data.answer) {
                log('Received answer');
                peer.signal(JSON.parse(data.answer));
            } else if (!isInitiator && data.offer) {
                log('Received offer');
                peer.signal(JSON.parse(data.offer));
            }
        }
    });
}

document.getElementById('createOffer').addEventListener('click', () => {
    sessionId = generateId();
    userId = generateId();
    document.getElementById('sessionId').value = sessionId;
    createPeer(true);
    log('Offer created. Share the Session ID with your friend.');
    socket.emit('start_gesture_recognition', { userId: userId });
});

document.getElementById('joinSession').addEventListener('click', () => {
    sessionId = document.getElementById('sessionId').value.trim();
    userId = generateId();
    if (sessionId) {
        createPeer(false);
        log('Joining session...');
        socket.emit('start_gesture_recognition', { userId: userId });
    } else {
        log('Please enter a valid Session ID');
    }
});

// Add event listener for sending messages
document.getElementById('sendMessage').addEventListener('click', () => {
    const messageInput = document.getElementById('message');
    const message = messageInput.value.trim();
    if (message && peer && peer.connected) {
        peer.send(JSON.stringify({ type: 'message', content: message }));
        log('Sent message: ' + message);
        messageInput.value = '';
    }
});

// Handle screenshot reception
socket.on('receive_screenshot', data => {
    if (data.toUserId === userId) {
        log('Received screenshot from peer');
        document.getElementById('latestScreenshot').src = data.image;
        showNotification('Screenshot received!');
    }
});

// Handle 'O' gesture and send screenshot to peer
socket.on('screenshot_taken', data => {
    log('Screenshot taken: ' + data.url);
    if (peer && peer.connected) {
        log('Sending screenshot to peer...');
        peer.send(JSON.stringify({ type: 'screenshot', content: data.url }));
        showNotification('Screenshot taken and sent!');
    }
});

// Update the 'V' gesture handler
socket.on('v_gesture_detected', data => {
    if (data.userId !== userId) {
        log('V gesture detected from other peer, requesting screenshot...');
        socket.emit('request_latest_screenshot', { requesterId: userId, targetId: data.userId });
        showNotification('Requesting latest screenshot...');
    }
});

window.addEventListener('beforeunload', () => {
    if (sessionId) {
        deleteDoc(doc(db, 'signaling', sessionId));
    }
});