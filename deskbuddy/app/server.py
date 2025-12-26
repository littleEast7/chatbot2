from flask import Flask, request, jsonify
import base64
import os

app = Flask(__name__)
assistant_ref = None
chat_window_ref = None


@app.route("/remind", methods=["POST"])
def remind():
    data = request.json or {}
    text = data.get("text", "提醒你一下～")
    sender_port = data.get("port")
    sender_ip = request.remote_addr

    if assistant_ref:
        assistant_ref.remind(text)

    if chat_window_ref:
        chat_window_ref.on_message_received(text, sender_ip, sender_port)

    return jsonify({"status": "ok"})


@app.route("/handshake", methods=["POST"])
def handshake():
    data = request.json or {}
    sender_port = data.get("port")
    avatar_data = data.get("avatar")
    sender_user_id = data.get("user_id")
    sender_ip = request.remote_addr

    if chat_window_ref:
        # Reuse the logic to update target IP
        chat_window_ref.on_handshake_received(sender_ip, sender_port, avatar_data, sender_user_id)

    # Prepare response with my avatar and user_id
    my_avatar_data = None
    my_user_id = None

    if chat_window_ref:
        my_user_id = chat_window_ref.config.get("user_id")
        current_avatar_path = chat_window_ref.current_avatar_path
        if current_avatar_path and os.path.exists(current_avatar_path):
            try:
                with open(current_avatar_path, "rb") as f:
                    my_avatar_data = base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                pass

    return jsonify({
        "status": "ok",
        "message": "Handshake accepted",
        "user_id": my_user_id,
        "avatar": my_avatar_data
    })


def start_server(config, assistant, chat_window=None):
    global assistant_ref, chat_window_ref
    assistant_ref = assistant
    chat_window_ref = chat_window

    app.run(
        host=config["server"]["host"],
        port=config["server"]["port"],
    )
