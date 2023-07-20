import logging
import asyncio
import os
import shutil

from kademlia.network import Server

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


class InitiatorPeer():

    def __init__(self, port):
        self.server = Server()
        self.port = port
        
        # Reset usernames.txt
        file1 = open("usernames.txt", "w")
        file1.write("")
        file1.close()
        
        # Delete folder and contents in it
        if os.path.exists('./users'):
            shutil.rmtree('users')
        
        # Create folder again
        os.mkdir('users')
        
        self.loop = asyncio.new_event_loop()
        self.loop.set_debug(True)
        self.loop.run_until_complete(self.server.listen(int(self.port)))
        

    
initiatorPeer = InitiatorPeer(8468)

try:
    initiatorPeer.loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    initiatorPeer.server.stop()
    initiatorPeer.loop.close()