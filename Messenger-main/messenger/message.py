import json
import time

class Message:
  def __init__(self, sender, recipient, message, creation_time = None):
    self.type = "message"
    self.sender = sender
    self.recipient = recipient
    self.creation_time = time.time() if creation_time == None else creation_time
    self.message = message

  def serialize(self):
    return json.dumps({
      "type": self.type,
      "sender": self.sender,
      "recipient": self.recipient,
      "creation_time": self.creation_time,
      "message": self.message
    })
    
  def to_dict(self):
    return {
      "type": self.type,
      "sender": self.sender,
      "recipient": self.recipient,
      "creation_time": self.creation_time,
      "message": self.message
    }

  @classmethod
  def deserialize(cls, json_str):
    data = json.loads(json_str)
    result = cls(
      sender=data["sender"],
      recipient=data["recipient"],
      creation_time=data["creation_time"],
      message=data["message"]
    )
    result.type = data["type"]
    
    return result

  def __repr__(self):
    return f"Message(type={self.type}, sender={self.sender}, recipient={self.recipient}, creation_time={self.creation_time}, message={self.message})"
