from flask import Flask, render_template, request, redirect
from flask_socketio import SocketIO, emit, join_room
from message_service import MessageService
import threading
import time
from message import Message

app = Flask(__name__)
app.secret_key = 'supersecretkey'
socketio = SocketIO(app)

connected_users = {}
session = {}
userMessages = {}

def user_connected(username):
  if username not in connected_users:
    socketio.emit('user_connected', {'username': username})
  connected_users[username] = time.time()

def message_received(message: Message):
  socketio.emit('receive_message', message.to_dict())
  
  if message.sender not in userMessages:
    userMessages[message.sender] = []
  userMessages[message.sender].append(message)
  userMessages[message.sender].sort(key=lambda x: x.creation_time)

message_service = MessageService(socketio, user_connected, message_received)

# Background thread to monitor user activity
def monitor_user_activity():
  while True:
    current_time = time.time()
    for user, last_seen in list(connected_users.items()):
      if current_time - last_seen > 2 * 60:  # 2 minutes timeout
        del connected_users[user]
        socketio.emit('user_disconnected', {'username': user})
    time.sleep(10)

# Start the background thread for user activity monitoring
threading.Thread(target=monitor_user_activity, daemon=True).start()

@app.route("/", methods=["GET", "POST"])
def index():
  if "username" not in session:
    if request.method == "POST":
      username = request.form["username"]
      if message_service.check_user_queue_exists(username):
        session["username"] = username
        message_service.start_listening_for_user(username)
        connected_users[username] = time.time()
      else:
        print("[ERROR] Invalid username, please try another one")
      return redirect("/")
    return render_template("login.html")
  return render_template("chat.html", username=session["username"])

@socketio.on('logout')
def logout():
  if 'username' in session:
    message_service.stop_listening_for_user(session['username'])
    del session['username']
    userMessages.clear()
    emit('redirect', {'url': '/'})

@socketio.on('connect')
def on_connect():
  if 'username' in session:
    username = session['username']
    join_room(username)
    connected_users[username] = time.time()    
    for user in connected_users:
      if user != username:
        socketio.emit('user_connected', {'username': user})
  else:
    emit('redirect', {'url': '/'})

@socketio.on('send_message')
def handle_send_message(data):
  sender = session["username"]
  recipient = data["recipient"]
  message = Message(sender, recipient, data["message"])
  message_service.send_message(message)
  socketio.emit('receive_message', message.to_dict(), room=recipient)
  
  # Add the message to the in memory collection
  if message.recipient not in userMessages:
    userMessages[message.recipient] = []
  userMessages[message.recipient].append(message)
  userMessages[message.recipient].sort(key=lambda x: x.creation_time)

@socketio.on('chat_open')
def handle_send_message(data):
  recipient = data["recipient"]
  messages = [] if userMessages.get(recipient) == None else userMessages.get(recipient)
  messages = [message.to_dict() for message in messages]
  socketio.emit('chat_open_received', {'recipient': recipient, 'messages': messages })
  
@socketio.on('heartbeat')
def handle_heartbeat():
  if 'username' in session:
    username = session['username']
    connected_users[username] = time.time()

if __name__ == "__main__":
  socketio.run(app, debug=True)
