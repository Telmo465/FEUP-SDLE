from kademlia.network import Server
import asyncio
from threading import Thread
from Message import Message
import json
import PeerInfo


class Listener(Thread):

    def __init__(self, ip, port, peer):
        super().__init__()
        self.ip = ip
        self.port = port
        self.peer = peer

    # Messages are json dictionaries keys -> operation ; content
    async def recieve_messages(self, reader, writer):
        
        message = await reader.read(-1)
        
        info_json = json.loads(message)
        #print("\nReceived message from " + str(info_json["ip"]) + ":" + str(info_json["port"]))
        operation = info_json["operation"]
        content = info_json["content"]
 
        ip = info_json["ip"]
        port = info_json["port"]

        
        if operation == "post":
            self.peer.timelineMessages.append(content)
        elif operation == "follow":
            # Follow content is PeerInfo as Dictionary
            # followerPInfo = PeerInfo.dicionary_to_peerInfo(content)
            
            if(await self.peer.handle_followed(info_json["username"])):
                self.peer.addNotification("New Follower - " + str(content))
            else :
                self.peer.addNotification("follow failed")                
        elif operation == "unfollow":
            if(self.peer.info.removeFollower(content)):
                self.peer.addNotification("Lost a follower - " + str(content))
            else :
                self.peer.addNotification("Unfollow failed")
        elif operation == "get":
            # content is the last message ID
            self.peer.handle_get(content, ip, port)
            self.peer.addNotification("get request from - " + str(ip) + ":" + str(port))
        elif operation == "getResponse":
            for key in content:
                self.peer.timelineMessages.append(Message(content[key]["number"], content[key]["author"], content[key]["content"]))

        return

    
    async def create_server(self):
        self.server = await asyncio.start_server(self.recieve_messages, self.ip, self.port)
        await self.server.serve_forever()
        

    def run(self):
        listener_running = asyncio.new_event_loop()
        listener_running.run_until_complete(self.create_server())
        
        