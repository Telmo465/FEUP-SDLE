import logging
import asyncio
import sys
import time
import threading
import json
import os
from os.path import exists

import random

import utils

from kademlia.network import Server
from PeerInfo import PeerInfo
from Listener import Listener
from Message import Message



mutex = threading.Lock()

class Peer():
    
    def __init__(self, ip, port, username):
        self.ip = ip
        self.port = port
        self.username = username
        self.info = PeerInfo(self.ip, self.port, [],[], 0)
        self.myMessages = {}
        self.timelineMessages = []
        
        self.info.ip = self.ip # User may log using another IP:Port
        self.info.port = self.port
        self.readPeerInfoFromFile()
        self.loop = asyncio.get_event_loop()
        self.bootstrapPorts = []

        self.notifications = []
        
        self.thread = ""

    async def setup(self):
        self.server = Server()
        await self.server.listen(int(self.port))
        bootstrap_node = ('127.0.0.1', 8468)
        await self.server.bootstrap([bootstrap_node])
        await self.server.set(self.username, self.info.serialize())

        print(await self.server.get(self.username))



    def writePeerInfoToFile(self):

        filename = "users/" + str(self.username) + ".txt"
        file = open(filename, "w")
        dictSave = {}
        dictSave["peerinfo"] = self.info.serialize()
        dictSave["myMessages"] = self.message_to_Dictionary(self.myMessages)
        dictSave["timelineMessages"] = []
        
        i = 0
        for message in self.timelineMessages:
            dictSave["timelineMessages"].append({"author": message.author, "content": message.content, "number" : message.number})
            i+=1

        file.write(json.dumps(dictSave))
        file.close()   
        

    def readPeerInfoFromFile(self):
        filename = "users/" + str(self.username) + ".txt"
        
        file_exists = exists(filename)
        if not file_exists : 
            return False
        file = open(filename, "r")
        contentRead = file.read()
        if(len(contentRead) < 1):
            file.close() 
            return False
        
        dictSave = json.loads(contentRead)
        
        self.info = PeerInfo.deserialize(dictSave["peerinfo"])
        
        for key in dictSave["myMessages"]:
            self.myMessages[key] =  Message(dictSave["myMessages"][key]["number"], dictSave["myMessages"][key]["author"], dictSave["myMessages"][key]["content"])
            
        for message in dictSave["timelineMessages"]:
            self.timelineMessages.append(Message(message["number"], message["author"], message["content"]))

        file.close() 
        return True
    
    def addNotification(self, notif):
        self.notifications.append(notif)

    def addMessage(self, message):
        self.info.last_post_id += 1
        messageToAdd = Message(self.info.last_post_id, self.username, message)
        self.myMessages[self.info.last_post_id] = messageToAdd
        

    def addMessageTimeline(self, message):
        self.timelineMessages.append(message)


    def send_message(self, destiny_ip, destiny_port, message):
        asyncio.run_coroutine_threadsafe(PeerInfo.send_message_safe(destiny_ip, destiny_port, message), loop=self.loop) # loop - .run_until_complete() ...
        

    async def set_peer_info(self, username, peer_info):
        await self.server.set(username, peer_info)

    async def get_peer_info(self, username):
        info = await self.server.get(username)


        if info is None:
            return None
        return PeerInfo.deserialize(info)
    

    def message_to_Dictionary(self, messages):
        messageDict = {}
        for key in messages:
            messageDict[key] = {"author": messages[key].author, "content": messages[key].content, "number" : messages[key].number}
        
        return messageDict
    

    def peerInfo_to_Dictionary(self, peerInfo):
        return  {"ip": peerInfo.ip, "port": peerInfo.port, "following": peerInfo.following, "followers": peerInfo.followers, "last_post_id": peerInfo.last_post_id}
    
    
    def handle_get(self, message_id, ip, port):
        
        if(message_id == -1):
            contentM = self.message_to_Dictionary(self.myMessages)
            message_to_send = {"operation" : "getResponse", "content": contentM, "ip" : self.ip, "port": self.port} 
            message_to_send = json.dumps(message_to_send)  
            self.send_message(ip, port, message_to_send)
            return
        
        if(self.myMessages[message_id] != None):
            contentM = self.message_to_Dictionary(self.myMessages)
            dicton = {}
            for key, value in contentM.items():
                if key > message_id:
                    dicton[key] = value
            message_to_send = {"operation" : "getResponse", "content": dicton, "ip" : self.ip, "port": self.port}
            message_to_send = json.dumps(message_to_send)  
            self.send_message(ip, port, message_to_send)
        else :
            contentM = self.message_to_Dictionary(self.myMessages)
            message_to_send = {"operation" : "getResponse", "content": contentM, "ip" : self.ip, "port": self.port}
            message_to_send = json.dumps(message_to_send)  
            self.send_message(ip, port, message_to_send)


    async def handle_followed(self, username: str): 
        return self.info.addFollower(username)


    async def handle_unfollowed(self, username: str) -> None:
        self.info.followers.remove(username)
        await self.set_kademlia_info(self.username, self.info)


    async def follow_user(self):
        
        users = utils.getAvailableUsernames()

        print("\n|=Available Users=|")
        
        i=1
        possible_followers = []
        for user in users:
            if user != self.username:
                possible_followers.append(user)
                print(str(i) + ": " + user)
                i+=1

        if len(possible_followers) <= 0:
            print(">There are no available users to follow!")
            return

        print("0 to Exit")
        option = int(input("Choose an option: "))
        utils.cleanScreen()
        if option == 0 : return
        if option < 0 and option >= len(users)-1:
            print('>Fail: User is not online!')
            return
    
        user = possible_followers[option - 1]
        self.info.addFollowing(user)
        
        content = self.peerInfo_to_Dictionary(self.info)

        message_to_send = {"operation" : "follow", "content": content, "ip" : self.ip, "port": self.port, "username": self.username}
        message_to_send = json.dumps(message_to_send)
        user_followed = await self.get_peer_info(user)
        self.send_message(user_followed.ip, user_followed.port, message_to_send)


    async def unfollow_user(self):

        print("|=Following Users=|")

        i=1
        for user in self.info.following:
            print(str(i) + ": " + user)
            i+=1
        
        print("0 to Exit")
        option = int(input('Choose a user to unfollow: '))
        utils.cleanScreen()
        
        if option == 0 : return
        if option < 0 and option >= len(self.info.following)-1:
            print('>Fail: User is not online!')
            return
    

        user = self.info.following[option - 1]
        self.info.removeFollowing(user)

        message_to_send = {"operation" : "unfollow", "content": self.username, "ip" : self.ip, "port": self.port}
        message_to_send = json.dumps(message_to_send)
        user_followed = await self.get_peer_info(user)
        print(user_followed.ip)
        print(user_followed.port)
        self.send_message(user_followed.ip, user_followed.port, message_to_send)


    async def refresh_timeline(self):
        
        for followed in self.info.following:
            
            messageID = -1
            for message in self.timelineMessages:
                if (message.author == followed and message.number > messageID):
                    messageID = message.number
            
            # Form message
            message_to_send = {"operation" : "get", "content": messageID, "ip" : self.ip, "port": self.port}
            message_to_send = json.dumps(message_to_send)
            
            # Get IP and PORT of followed
            info = await self.get_peer_info(followed)
            ip = info.ip
            port = info.port
            
            self.send_message(ip, port, message_to_send)
            
    def showPeerInfo(self):
        
        while True:
            print("\n|=Peer Info=|")
            print("1 - IP , PORT, Last Post ID")
            print("2 - Followers")
            print("3 - Following")
            print("0 - Exit")
            print("\n")
            
            option = input("Choose an option: ")
            utils.cleanScreen()
                    
            if(option == "1"):
                print("IP: " + self.info.ip)
                print("Port: " + str(self.info.port))
                print("Last Post ID: " + str(self.info.last_post_id))
            elif(option == "2"):
                print("\n|=Followers=|")
                for follower in self.info.followers:
                    print(follower)
            elif(option == "3"):
                print("\n|=Following=|")
                for following in self.info.following:
                    print(following)
            elif(option == "0"):
                break
            else :
                print("Invalid option")
            
            print("\npress any key to continue...")
            input()
            

    def createPost(self):
            
            print("\n|=Create Post=|")
            content = input("Content: ")
            self.info.last_post_id += 1
            post = Message(self.info.last_post_id, self.username, content)
            self.myMessages[post.number] = post
            self.timelineMessages.append(post)
            
            print("Post created!")
            print("\npress any key to continue...")
            input()
            utils.cleanScreen()
    

    def showUserTimeline(self):
        if(self.myMessages.__len__() == 0):
            print("No posts to show!")
            return
        
        for key in self.myMessages:
            print("\n|=Post=|" + "id : " + str(self.myMessages[key].number))
            print("Author: " + self.myMessages[key].author)
            print("Content: " + self.myMessages[key].content)
            print("\n")
        
        print("\npress any key to continue...")
        input()
        utils.cleanScreen()
            

    def showTimeline(self):
        if(self.timelineMessages.__len__() == 0):
            print("No posts to show!")
            return
        
        for post in self.timelineMessages:
            print("\n|=Post=|" + "id : " + str(post.number))
            print("Author: " + post.author)
            print("Content: " + post.content)
            print("\n")
        
        print("\npress any key to continue...")
        input()
        utils.cleanScreen()

    def showNotifications(self):
        if(len(self.notifications) == 0):
            print("No notifications to show!")
            return
        
        for notification in self.notifications:
            print(">>", notification, '\n')
        
        self.notifications = []

        print("\npress any key to continue...")
        input()
        utils.cleanScreen()


    async def menu(self):
        
        print("\n1 - Create post")
        print("2 - Follow user")
        print("3 - Unfollow user")
        print("4 - Get timeline")
        print("5 - Get user timeline")
        print("6 - Refresh Timeline")
        print('7 - Notifications')
        print('8 - Peer Info ')
        print("0 - Quit")
        
        option = input("Choose an option: ")
        utils.cleanScreen()
            
        if(option == "1"):
            self.createPost()
        elif(option == "2"):
            await self.follow_user()
        elif(option == "3"):
            await self.unfollow_user()
            pass
        elif(option == "4"):
            self.showTimeline()
        elif(option == "5"):
            self.showUserTimeline()
        elif(option == "6"):
            await self.refresh_timeline()
        elif(option == "7"):
            self.showNotifications()
        elif(option == "8"):
            self.showPeerInfo()
        elif(option == "0"):
            utils.removeUsernameFromFile(self.username)
            self.listener.join()
            self.thread.join()
            sys.exit()
        else:
            print("Invalid option")
        



    async def run(self):
        
        await self.setup()
        self.listener = Listener(self.ip, self.port, self)
        self.listener.start()
        info = await self.get_peer_info(self.username)
        print(info)
        
        mutex.acquire()
        utils.writeUsernameToFile(self.username)
        mutex.release()  

        while True:
            await self.menu()
            self.writePeerInfoToFile()

            
def main():
    if(len(sys.argv) != 4):
        print("Usage: python Peer.py <ip> <port> <username>")
        return

    peer = Peer(str(sys.argv[1]), int(sys.argv[2]), str(sys.argv[3]))
    peer.thread = threading.Thread(target=peer.loop.run_forever, daemon=True).start()
    asyncio.run(peer.run())
    
    
if __name__ == "__main__":
    main()