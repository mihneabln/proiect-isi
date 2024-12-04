import pika

credentials = pika.PlainCredentials("guest", "guest")
connection_params = pika.ConnectionParameters(host='localhost', port=5672, credentials=credentials)
connection = pika.BlockingConnection(connection_params)
channel = connection.channel()

# Array of usernames
usernames = ["stefan", "alex", "maria"]

# Exchange name
exchange_name = "chat_online_user_exchange"

def clear_rabbitmq():
  global channel
  try:
    channel.exchange_delete(exchange=exchange_name)
    print(f"Exchange '{exchange_name}' deleted.")
  except pika.exceptions.ChannelClosed:
    print("Exchange deletion failed (likely because it didn't exist). Reopening channel.")
    channel = connection.channel()

  for username in usernames:
    queue_name = f"chatUser.{username}"
    try:
      channel.queue_delete(queue=queue_name)
      print(f"Queue '{queue_name}' deleted.")
    except pika.exceptions.ChannelClosed:
      print(f"Queue '{queue_name}' does not exist or deletion failed.")
      channel = connection.channel()
    queue_name = f"chatUser.{username}"

def setup_chat_queues():
  global channel
  channel.exchange_declare(exchange=exchange_name, exchange_type="fanout")

  for username in usernames:
    queue_name = f"chatUser.{username}"
  
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(exchange=exchange_name, queue=queue_name)
    print(f"Queue created and bound to exchange: {queue_name}")

clear_rabbitmq()
setup_chat_queues()

connection.close()
