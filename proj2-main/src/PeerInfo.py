import json
from dataclasses import asdict, dataclass
from dataclasses_json import dataclass_json
import asyncio
import attr

@dataclass_json
@dataclass
class PeerInfo:


    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.followers = []
        self.following = []
        self.last_post_id = 0

    def __init__(self, ip, port, followers, following, last_post_id):
        self.ip = ip
        self.port = port
        self.followers = followers
        self.following = following
        self.last_post_id = last_post_id


    def addFollower(self, follower):
        if(self.followers.__contains__(follower)):
            print("Already following")
            return False

        self.followers.append(follower)
        
        return True


    def removeFollower(self, follower):
        if(not self.followers.__contains__(follower)):
            print("Not a follower")
            return False
        else :
            self.followers.remove(follower)

        return True
        
    
    def addFollowing(self, possibleFollow):
        if(self.following.__contains__(possibleFollow)):
            print("Already following")
            return False

        self.following.append(possibleFollow)
        return True


    def removeFollowing(self, possibleUnfollow):
        if(not self.following.__contains__(possibleUnfollow)):
            print("Not following")
            return False

        self.following.remove(possibleUnfollow)    
    
    def listFollowers(self):
        pass
    
    def listFollowing(self):
        pass
    
    
    async def send_message_safe(ip, port, message):
        try:
            _, writer = await asyncio.open_connection(ip, port) 
            writer.write(message.encode())
            writer.write_eof()
            await writer.drain()
            return True
        except Exception as e:
            return False    
    
    def serialize(self):

        return json.dumps({
            "ip": self.ip,
            "port": self.port,
            "followers": self.followers,
            "following": self.following,
            "last_post_id": self.last_post_id
        })   

    def deserialize(json_str: str):
        peer_info_json = json.loads(json_str)
        return PeerInfo(
            peer_info_json["ip"],
            peer_info_json["port"],
            peer_info_json["followers"],
            peer_info_json["following"],
            peer_info_json["last_post_id"])



def dicionary_to_peerInfo(dictionary):
    return PeerInfo(dictionary["ip"], dictionary["port"], dictionary["followers"], dictionary["following"], dictionary["last_post_id"])
