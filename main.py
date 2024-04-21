from flask import Flask, Response, render_template_string
import socket
import cv2
import numpy as np
import threading

app = Flask(__name__)

# Configuration for the socket server
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8446
latest_frame = None
frame_lock = threading.Lock()

def recvall(sock, count):
    """Ensure 'count' bytes are read."""
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf

def handle_client_connection(client_socket):
    """Function to handle client connections and receive video frames."""
    global latest_frame
    try:
        while True:
            size_data = recvall(client_socket, 4)
            if not size_data:
                break
            frame_size = int.from_bytes(size_data, 'big')
            frame_data = recvall(client_socket, frame_size)
            if not frame_data:
                break

            with frame_lock:
                latest_frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((480, 640, -1))
    finally:
        client_socket.close()

def socket_server():
    """Background thread function for the socket server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        print(f"Socket server listening on {SERVER_HOST}:{SERVER_PORT}...")

        while True:
            client_socket, _ = server_socket.accept()
            client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
            client_thread.daemon = True
            client_thread.start()

@app.route('/')
def index():
    """Serve a simple webpage to view the video stream."""
    return render_template_string('''<html><body><img src="{{ url_for('video_feed') }}"></body></html>''')

@app.route('/video_feed')
def video_feed():
    """Route to stream the latest video frame."""
    def generate():
        while True:
            with frame_lock:
                if latest_frame is not None:
                    ret, jpeg = cv2.imencode('.jpg', latest_frame)
                    if ret:
                        frame_data = jpeg.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    socket_server()
    # threading.Thread(target=socket_server, daemon=True).start()
    # app.run(debug=True, host='0.0.0.0', port=5000)