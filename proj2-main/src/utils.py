import os
import sys

def cleanScreen():
    os.system('cls' if os.name == 'nt' else 'clear')


def getAllAvailableAddressInfo():

    file1 = open("BootstrapFile.txt", "r")
    
    lines = file1.readlines()

    peer_address_info = []

    for line in lines:
        values = line.split(' ')
        ip = values[0]
        port = int(values[1])
        values = (ip, port)
        peer_address_info.append(values)

    file1.close()

    return peer_address_info
    
    
def writeMyInfoToFile(ip, port):

    file1 = open("BootstrapFile.txt", "a")

    file1.write(ip + " " + str(port) + '\n')

    file1.close()


def removePeerFromFile(ip, port):

    peers = []

    file1 = open("BootstrapFile.txt", "r")
    lines = file1.readlines()

    for line in lines:
        address_info = line.strip('\n').split(' ')
        tuple_address_info = (address_info[0], address_info[1])
        if tuple_address_info != (ip, str(port)):
            peers.append(tuple_address_info)

    file1.close()
    file1 = open("BootstrapFile.txt", "w")

    for line in peers:
        address_tuple = line[0] + " " + line[1]
        file1.write(address_tuple + '\n')
    
    file1.close()


def writeUsernameToFile(username):

    # Check username
    users = getAvailableUsernames()
    if username in users:
        return

    file1 = open("usernames.txt", "a")

    file1.write(username + "\n")
    file1.close()


def removeUsernameFromFile(username):

    file1 = open("usernames.txt", "r")
    lines = file1.readlines()
    usernames = []

    for line in lines:
        line = line.strip('\n')
        if line != username:
            usernames.append(line)

    file1.close()
    file1 = open("usernames.txt", "w")
    
    for username in usernames:
        file1.write(username + '\n')
    
    file1.close()

def getAvailableUsernames():

    file1 = open("usernames.txt", "r")
    lines = file1.readlines()
    lines = map(lambda line: line.strip('\n'), lines)

    file1.close()

    return lines







