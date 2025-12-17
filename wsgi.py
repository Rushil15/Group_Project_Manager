from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # For local testing with eventlet/Socket.IO
    socketio.run(app, host="0.0.0.0", port=5000)
