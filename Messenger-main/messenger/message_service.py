import pika
import threading
import time
import json
from message import Message

class MessageService:
  def __init__(self, socketio, userConnectedCallback, messageReceivedCallback):
    self.socketio = socketio
    self.existingListeners = {}
    self.userConnectedCallback = userConnectedCallback
    self.messageReceivedCallback = messageReceivedCallback
    
    # TODO e) Pentru primele puncte poti folosi o instanta locala. Pentru ultimul punct schimba credentialele
    # si incepe sa conversezi cu ceilalti colegi. Have fun!
    credentials = pika.PlainCredentials("guest", "guest")
    self.connection_params = pika.ConnectionParameters(host='localhost', port=5672, credentials=credentials)
    self.open_connection()

  def open_connection(self):
    self.connection = pika.BlockingConnection(self.connection_params)    
    self.channel = self.connection.channel()    

  def start_listening_for_user(self, username):
    queue_name = f'chatUser.{username}'
    if queue_name in self.existingListeners:
      return
    
    self.existingListeners[queue_name] = True
    
    listenForMessages = threading.Thread(target=self.listen_for_messages, args=(queue_name,))
    listenForMessages.start()
    
    userAliveKeep = threading.Thread(target=self.kepp_user_alive, args=(username, queue_name,))
    userAliveKeep.start()
    
  def check_user_queue_exists(self, username):
    try:
      queue_name = f'chatUser.{username}'
      self.channel.queue_declare(queue=queue_name, passive=True)
    except Exception as e:
      self.open_connection()
      return False
    
    return True

  def stop_listening_for_user(self, username):
    queue_name = f'chatUser.{username}'
    if queue_name not in self.existingListeners:
      return
    
    self.channel.stop_consuming(consumer_tag=queue_name)
    del self.existingListeners[queue_name]

  def kepp_user_alive(self, username, queue_name):
    while queue_name in self.existingListeners:
      print(f'[INFO] User alive {username}')
      body = json.dumps({
        "type": "user-alive",
        "username": username
      })      
      
      try:
        # TODO a): trimite un mesaj prin care sa anunti ceilalti utilizatori ca esti online.
        # Ai grija ca acest mesaj sa expire dupa ce a stat pe queue 2 minute. Exchange: chat_online_user_exchange
            self.channel.basic_publish(
                exchange='chat_online_user_exchange', 
                routing_key='',  # Fără routing_key pentru exchange de tip fanout
                body=body,
                properties=pika.BasicProperties(
                    expiration='120000'  # Mesajul expiră după 2 minute
                )
            )
            print(f'[INFO] {username} este online. Mesaj trimis.')
      except Exception as e:
        self.open_connection()
      time.sleep(30)

  def send_message(self, message: Message):
    print(f"[Info] send message from {message.sender} to {message.recipient}")
    queue_name = f'chatUser.{message.recipient}'
    
    try:
      # TODO c) trimite un mesaj direct catre queue-ul utilizatorului cu care conversezi.
      # Body-ul trebuie sa fie un string, iar clasa Message are o metoda sa te ajute sa faci conversia
      # Hint: cauta in breviar cum trebuie sa fie exchange-ul si routing_key-ul pentru a trimite direct catre queue
      body = message.serialize()  # Convertim mesajul într-un format serializat
      self.channel.basic_publish(
          exchange='',
          routing_key=queue_name,  # Folosește queue-ul utilizatorului drept routing_key
          body=body
      )
      print(f'[INFO] Mesaj trimis către {message.recipient}: {body}')
    except Exception as e:
      self.open_connection()

  def listen_for_messages(self, queue_name):
    def callback(ch, method, properties, body):
      message = json.loads(body.decode())
      print("[INFO] Message consumed:")
      print(message)
      if message['type'] == 'user-alive':
        self.userConnectedCallback(message['username'])
        return
      if message['type'] == 'message':
        self.messageReceivedCallback(Message.deserialize(body.decode()))
        return

    # TODO b) Fiecare utilizator are un queue pentru el. Poti sa folosesti interfata sa vezi cum arata queue-urile.
    # Consuma mesajele pentru queue-ul atribuit tie si asigura-te ca le procesezi, iar apoi scoti de pe queue
    try:
        self.channel.basic_consume(
            queue=queue_name, 
            on_message_callback=callback, 
            auto_ack=True,
            consumer_tag=queue_name
        )
        print(f"[INFO] Începerea ascultării pentru {queue_name}")
        self.channel.start_consuming()
    except Exception as e:
        print(f'[ERROR] Nu am putut începe ascultarea pentru {queue_name}: {str(e)}')
        self.open_connection()