from flask import Flask, Response
import threading
import socket
import cv2
import numpy as np

app = Flask(__name__)

# Buffer for the latest frame received from the socket server
latest_frame = None
frame_lock = threading.Lock()

# Configuration for the socket server
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8446

def socket_server():
    global latest_frame
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        print(f"Socket server listening on {SERVER_HOST}:{SERVER_PORT}...")

        while True:
            client_socket, _ = server_socket.accept()
            with client_socket:
                print("Client connected for video streaming.")
                try:
                    while True:
                        # Example: Assuming the frame size is 640x480
                        data = client_socket.recv(640 * 480 * 3)
                        if not data:
                            break
                        # Convert the bytes to a numpy array and reshape to an image
                        nparr = np.frombuffer(data, np.uint8)
                        frame = nparr.reshape((480, 640, 3))
                        with frame_lock:
                            latest_frame = frame
                except Exception as e:
                    print(f"Error receiving data: {e}")

@app.route('/video_feed')
def video_feed():
    """Route to stream the video feed."""
    def generate():
        global latest_frame
        while True:
            with frame_lock:
                if latest_frame is not None:
                    # Encode the frame in JPEG format
                    ret, jpeg = cv2.imencode('.jpg', latest_frame)
                    if ret:
                        # Convert the frame to byte format
                        frame_data = jpeg.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Start the socket server in a background thread
    threading.Thread(target=socket_server, daemon=True).start()
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)