from email import message
from optparse import Values
import string    
from random import randint, choice
import zmq
import asyncio
import json
import time
import os
import sys
import numpy

import threading

from json import JSONEncoder

import itertools

MAX_LIMIT = 255



# Class Subscriber
# SUbscribes and unsubscribes topics
# Get messages from topics that it subscribes to

class Subscriber :

    def __init__(self, id, topic_name) -> None:

        self.id = id
        self.last_messages_received = []
        self.files_name = []
        self.topic_name = topic_name

        # Create subscriber socket
        context = zmq.Context()
        self.proxy_socket = context.socket(zmq.REQ)
        self.proxy_socket.connect("tcp://localhost:5559")

    
    # Sends GET() command to proxy, meaning it asks for a message on a certain topic
    # Get command is - "GET SubscriberID TopicName"
    def get(self):

        get_message = "GET" + " " + str(self.id) + " " + self.topic_name
        print(f"Sent request to get message from topic {self.topic_name}")
        self.proxy_socket.send(get_message.encode('utf-8'))
        
        response = self.proxy_socket.recv()
        print("Get response : " + response.decode('utf-8'))
        

    # Sends SUB() command to proxy, meaning it subscribes a certain topic
    # Get command is - "SUB SubscriberID TopicName"
    def subscribe(self):

        sub_message = "SUB" + " " + str(self.id) + " " + self.topic_name
        print(f"Sent request to join to topic {self.topic_name}")
        self.proxy_socket.send(sub_message.encode('utf-8'))
        
        response = self.proxy_socket.recv()
        print("Subscribe Response : " + response.decode('utf-8'))
        
    # Sends UNSUB() command to proxy, meaning it unsubscribes a certain topic
    # Get command is - "SUB SubscriberID TopicName"
    def unsubscribe(self):

        unsub_message = "UNSUB" + " " + str(self.id) + " " + self.topic_name
        print(f"Sent request to leave the topic {self.topic_name}")
        self.proxy_socket.send(unsub_message.encode('utf-8'))

        response = self.proxy_socket.recv()
        print("Unsubscribe Response : " + response.decode('utf-8'))


    # code executed by the subscriber so we can see its behaviour
    def run(self):

        self.subscribe()
        for i in range(10):
            self.get()
            time.sleep(2)
        self.unsubscribe()    
        
        
    # Save to file ?? (Not prioritary?)

# Class Publisher
# Creates and publishes random messages on topics

class Publisher :

    def __init__(self, id, topic_name) -> None:

        self.id = id
        self.topic_name = topic_name
        self.count_message = 0
        
        # Create Publisher socket
        context = zmq.Context()
        self.proxy_socket = context.socket(zmq.REQ)
        self.proxy_socket.connect("tcp://localhost:5560")


    #Talvez por num ficheiro de funções auxiliares
    def generate_random_string(self):

        random_string = ""

        for _ in range(20):
            random_integer = choice([randint(48, 58), randint(65, 91), randint(97, 123)])
            random_string += (chr(random_integer))

        return random_string


    def put(self):

        put_message = "PUT " + self.topic_name + " " + self.generate_random_string()
        self.proxy_socket.send(put_message.encode('utf-8'))
        
        response = self.proxy_socket.recv()
        print("PUT response : " + response.decode('utf-8'))

    def run(self):
        
        while True:
            for _ in range(5):
                self.put()
            time.sleep(5)


class Proxy :
    def __init__(self) -> None:

        self.topics = {} ## Key -> Topic name , Value -> Topic Object 

        # Create Proxy Router Pooling
        context = zmq.Context()
        self.frontend = context.socket(zmq.ROUTER)
        self.backend = context.socket(zmq.ROUTER)
        self.frontend.bind("tcp://*:5559")
        self.backend.bind("tcp://*:5560")

        # Initialize poll set
        self.poller = zmq.Poller()
        self.poller.register(self.frontend, zmq.POLLIN)
        self.poller.register(self.backend, zmq.POLLIN)

    
    #loop
    def run(self):

        # Read Json file that contains previous state from proxy
        self.readJson()

        while True:
            
            # Update Json file with current state of proxy
            self.updateJson()

            try:
                socks = dict(self.poller.poll())
            except KeyboardInterrupt:
                break

            # Messages from subscribers
            if socks.get(self.frontend) == zmq.POLLIN:
                message_bytes = self.frontend.recv_multipart()
                message = message_bytes[2].decode('utf-8')
                thread = threading.Thread(target=self.frontend_messages_handler, args=(message, message_bytes,))
                thread.daemon = True
                thread.start()

            # Messages from publishers
            if socks.get(self.backend) == zmq.POLLIN:
                message_bytes = self.backend.recv_multipart()
                message = message_bytes[2].decode('utf-8')
                thread = threading.Thread(target=self.backend_messages_handler, args=(message, message_bytes,))
                thread.daemon = True
                thread.start()
            
            
            
    # Function for reading from Json file (Topics dictionary)
    def readJson(self):
                
        with open('topics.json', 'r') as openfile:
            json_object = json.load(openfile)
            for key in json_object.keys():
                key = str(key)
                new_topic = Topic(key)
                self.topics[key] = new_topic
                self.topics[key].active_subs = json_object[key]["active_subs"]
                self.topics[key].total_num_messages = json_object[key]["total_num_messages"]
                self.topics[key].most_delayed_message = json_object[key]["most_delayed_message"]
                for num in json_object[key]["messages"].keys():
                    self.topics[key].messages[int(num)] = json_object[key]["messages"][num]
                self.topics[key].sub_last_message = json_object[key]["sub_last_message"]
                
               
    # Function for updating Json file (Topics dictionary) 
    def updateJson(self):
        topicsDic = {}
        
        for key in self.topics.keys():
            topicDic = {}
            topicDic["name"] = self.topics[key].name
            topicDic["active_subs"] = self.topics[key].active_subs
            topicDic["total_num_messages"] = self.topics[key].total_num_messages
            topicDic["most_delayed_message"] = self.topics[key].most_delayed_message
            topicDic["messages"] = self.topics[key].messages
            topicDic["sub_last_message"] = self.topics[key].sub_last_message
            topicsDic[self.topics[key].name] = topicDic
            
        with open("topics.json", "w") as outfile:
                    json.dump(topicsDic, outfile)

    def parse_message(self, message):

        message_list = message.split(' ')
        return message_list
    
    
    # Checks if topic has no active subs and updates most delayed message from said topic, plus deletes all messages in memory
    def check_no_subs_and_clear(self, topic_name):
        if (len(self.topics[topic_name].active_subs) == 0):
            self.topics[topic_name].most_delayed_message = self.topics[topic_name].total_num_messages + 1
            self.topics[topic_name].messages = {}
        

    # Adds subcriber to topic
    def handle_sub(self, message_list, message_bytes):

        topic_name = message_list[2]
        subscriber_id = message_list[1]

        if topic_name in self.topics.keys():
            if subscriber_id not in self.topics[topic_name].active_subs :
                self.topics[topic_name].active_subs.append(subscriber_id)
                
                # Set sub_last_received message to current one
                self.topics[topic_name].sub_last_message[subscriber_id] = self.topics[topic_name].most_delayed_message
                
                # Response
                print(f"Added sub {subscriber_id} to topic {topic_name}")
                subResponse = 'sucess'
                self.frontend.send_multipart([message_bytes[0], b'', subResponse.encode('utf-8')])
            else :
                print(f"Sub {subscriber_id} already subscribed to topic {topic_name}")
                
                # Response
                subResponse = 'error'
                self.frontend.send_multipart([message_bytes[0], b'', subResponse.encode('utf-8')])
        else:
            new_topic = Topic(topic_name)
            self.topics[topic_name] = new_topic
            self.topics[topic_name].active_subs.append(subscriber_id)

            print(f"Created topic {topic_name} and adedd sub {subscriber_id}")
            self.topics[topic_name].sub_last_message[subscriber_id] = self.topics[topic_name].most_delayed_message
            # Response
            subResponse = 'sucess'
            self.frontend.send_multipart([message_bytes[0], b'', subResponse.encode('utf-8')])

        print(self.topics[topic_name].active_subs)
             
    # Remove subscriber from topic
    def handle_unsub(self, message_list, message_bytes): 
        
        topic_name = message_list[2]
        subscriber_id = message_list[1]
        
        if topic_name not in self.topics.keys():
            print(f'No Topic by the name of {topic_name}')
            
            # Response
            unsubResponse = 'error'
            self.frontend.send_multipart([message_bytes[0], b'', unsubResponse.encode('utf-8')])   
        else :
            if subscriber_id not in self.topics[topic_name].active_subs:
                print(f'Sub {subscriber_id} is not a subscriber of {topic_name}')
                
                # Response
                unsubResponse = 'error'
                self.frontend.send_multipart([message_bytes[0], b'', unsubResponse.encode('utf-8')])
            else:
                if(subscriber_id in self.topics[topic_name].active_subs and len(self.topics[topic_name].active_subs) == 1):
                    self.topics[topic_name].active_subs = []
                else :    
                    self.topics[topic_name].active_subs.remove(subscriber_id)
                
                print(f"Removed sub {subscriber_id} from topic {topic_name} ")
                
                # Remove subscriber from active on topic
                del self.topics[topic_name].sub_last_message[subscriber_id]
                
                # If no more active subscribers for the topic clear messages
                self.check_no_subs_and_clear(topic_name)
                
                # Response
                unsubResponse = 'sucess'
                self.frontend.send_multipart([message_bytes[0], b'', unsubResponse.encode('utf-8')])

        print(self.topics[topic_name].active_subs)
        
    # Handle response to get message by subscriber
    def handle_get(self, message_list, message_bytes):
        
        topic_name = message_list[2]
        subscriber_id = message_list[1]
        
        if topic_name not in self.topics.keys():
            print(f'No Topic by the name of {topic_name}')
            
            # Response
            getResponse = 'error'
            self.frontend.send_multipart([message_bytes[0], b'', getResponse.encode('utf-8')])   
            pass
        else :
            message_to_send = 'error'
            if subscriber_id not in self.topics[topic_name].active_subs:
                print(f'Sub {subscriber_id} is not a subscriber of {topic_name}')
                getResponse = 'error'
                self.frontend.send_multipart([message_bytes[0], b'', getResponse.encode('utf-8')])
                pass
            else:
                # GET MESSAGE FROM TOPIC AND SEND IT
                last_msg_number = self.topics[topic_name].sub_last_message[subscriber_id]
                # print ("LAST MSG VAL : " + str(last_msg_number))
                
                # Check if message number exists
                if((last_msg_number + 1) not in self.topics[topic_name].messages.keys()):
                    getResponse = 'error message number doesnt exist (GET)'
                    self.frontend.send_multipart([message_bytes[0], b'', getResponse.encode('utf-8')])
                    pass
                else:
                    message_to_send = self.topics[topic_name].messages[last_msg_number + 1]
                                
                
                    # Check if he is most "delayed" subscriber on that topic, if so delete the message that was sent (All others are ahead)
                    update_delayed_msg = 0
                    
                    for num_message in self.topics[topic_name].sub_last_message.values():
                        if(num_message <= last_msg_number):
                            update_delayed_msg += 1
                    
                    # If theres is only 1 match for the last message received than that subscriber is the most delayed one and we can delete the message that just got sent
                    if(update_delayed_msg < 2):
                        self.topics[topic_name].most_delayed_message = last_msg_number + 1
                        if(num_message > 0):
                            del self.topics[topic_name].messages[last_msg_number]
                        
                    # Update last message sent to subscriber
                    self.topics[topic_name].sub_last_message[subscriber_id] +=1
                    
                        
                    # getResponse = 'ACTUAL MESSAGE'
                    self.frontend.send_multipart([message_bytes[0], b'', message_to_send.encode('utf-8')])
                    pass
            
            print(f"(GET)MESSAGES from Topic {topic_name}: ")
            print(self.topics[topic_name].messages)
        
    # Handles put from publisher
    def handle_put(self, message_list, message_bytes):
        
        topic_name = message_list[1]
        message = message_list[2]
        
        if topic_name not in self.topics.keys():
            print(f'No Topic by the name of {topic_name}')
            
            # Response
            putResponse = 'error'
            self.backend.send_multipart([message_bytes[0], b'', putResponse.encode('utf-8')])   
        else :
            # Add Message to Topic
            most_recent_message = self.topics[topic_name].total_num_messages + 1
            self.topics[topic_name].total_num_messages = most_recent_message
            self.topics[topic_name].messages[most_recent_message] = message
            
            # Response
            putResponse = message
            self.backend.send_multipart([message_bytes[0], b'', putResponse.encode('utf-8')]) 
           
            
        
    #handler das mensagens que recebe do subscriber
    def frontend_messages_handler(self, message, message_bytes):

        message_list = self.parse_message(message)

        if message_list[0] == "SUB":
            self.handle_sub(message_list, message_bytes)
        if message_list[0] == "UNSUB":
            self.handle_unsub(message_list, message_bytes)
        if message_list[0] == "GET":
            self.handle_get(message_list, message_bytes) 
        else:
            #Handlers dos outros tipo de mensagens
            pass
        
    #Handles Publisher messages
    def backend_messages_handler(self, message, message_bytes):

        message_list = self.parse_message(message)

        if message_list[0] == "PUT": 
            self.handle_put(message_list, message_bytes)   
        else:
            #Handlers dos outros tipo de mensagens
            pass

    # Parse Backend MEssage
    # Parse FrontEnd message
        
# Class Topic
# Represents a topic, and keeps updated information about the number of messages, last message added...

class Topic :
    def __init__(self, name) -> None:
        
        self.name = name
        self.active_subs = [] #Array containing all current subscribers of the topic
        self.total_num_messages = 0 # Total number of messages created on this topic
        self.most_delayed_message = 1 # Number of the message that the most delayed subscriber is on
        self.messages = {} # Key -> Message ID (counter), Value -> MEssage content
        self.sub_last_message = {} # Key -> Subscriber ID ; Value -> Number of last message received   
        
        print('Created Topic Successfully (' + name + ')')

    
        
        
        
