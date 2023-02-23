from socket import *
import sys, json, os
from threading import *

if len(sys.argv) != 4:
    print("\n===== Error usage, python3 client.py server_IP server_port client_udp_server_port ======\n")
    exit(0)
serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
clientUDPPort = int(sys.argv[3])
serverAddress = (serverHost, serverPort)

clientSocket = socket(AF_INET, SOCK_STREAM)

clientSocket.connect(serverAddress)

def login(username, password, clientSocket):
    credentials = "credentials," + username + "," + password + ", " + str(clientUDPPort)
    clientSocket.sendall(credentials.encode())

def checkInput(message):
    if message[0:3] in ["EDG", "UED", "SCS", "DTE", "AED", "OUT", "UVF"]:
        return True
    return False

def is_int(num):
    try:
        int(num)
    except ValueError:
        return False
    return True

def receiveUDP(serverSocket):
    while 1:
        message, clientAddress = serverSocket.recvfrom(1024)
        message1 = message.decode()
        print(message1, clientAddress)

def sendFileUDP(new_user_IP, user_UDP, fileName):
    temp_UDP = "UDP,"+fileName
    sock = socket(AF_INET, SOCK_STREAM)
    sock.sendto(temp_UDP.encode(),(new_user_IP, int(user_UDP)))

def start_udp(clientUDPPort):
    hostname = gethostname()
    udpclientip = gethostbyname(hostname)
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    serverSocket.bind((udpclientip, clientUDPPort))
    new_thread = Thread(target=receiveUDP,args=(serverSocket,))
    new_thread.start()

loggedIn = False
username = input('> username: ')
password = input('> password: ')
login(username, password, clientSocket)
while not loggedIn:
    data = clientSocket.recv(1024)
    receivedMessage = data.decode()

    if receivedMessage == "blocked":
        print("> Your account is blocked due to multiple authentication failures. Please try again later")
        exit(0)
    if receivedMessage == "Correct Credentials":
        print("> Welcome!")
        loggedIn = True
    if receivedMessage == "Try again":
        print("> Invalid Password. Please try again")
        new_password = input('> password: ')
        login(username, new_password, clientSocket)

start_udp(clientUDPPort)

if loggedIn:
    while True:
        message = input("> Enter one of the following commands (EDG, UED, SCS, DTE, AED, OUT, UVF): ")
        if checkInput(message):
            if message[0:3] == 'EDG':
                split_message = message.split()
                if len(split_message) != 3:
                    print("> EDG command requires fileID and dataAmount as arguments.")
                else:
                    fileID = split_message[1]
                    dataAmount = split_message[2]
                    if not ((is_int(fileID)) and (is_int(dataAmount))):
                        print("> the fileID or dataAmount are not integers, you need to specify the parameter as integers")
                    else:
                        EDGdata = ""
                        for i in range(int(dataAmount)):
                            EDGdata += str(i+1)+"\n"
                        fileName = username+"-"+str(fileID)+".txt"
                        with open(fileName, 'w') as f1:
                            f1.write(EDGdata)
                        print("> Data generation done, " + dataAmount + " data samples have been generated and stored in the file " + fileName)

            elif message[0:3] == 'UED':
                split_message = message.split()
                if len(split_message) != 2:
                    print("> UED command requires fileID as an argument.")
                else:
                    if not is_int(fileID):
                        print("> the fileID is not an integer, you need to specify the parameter as an integer")
                    else:
                        files = [f for f in os.listdir('.') if os.path.isfile(f)]
                        fileName = username+"-"+str(fileID)+".txt"
                        if fileName not in files:
                            print("> the file to be uploaded does not exist")
                        else:
                            with open(fileName, 'r') as f1:
                                uploadingData = f1.read()
                            with open(fileName, 'r') as f2:
                                dataAmount = len(f2.readlines())
                            completeDataUpload = "UED" + "," + fileName + "," + uploadingData + "," + username + "," + fileID + "," + str(dataAmount)
                            clientSocket.sendall(completeDataUpload.encode())
                            data = clientSocket.recv(1024)
                            receivedMessage = data.decode()
                            if 'uploaded,' in receivedMessage:
                                print(receivedMessage, "message was received here")
                                uploadedFileID = receivedMessage.split(',')[1]
                                print("> Data file with ID of " + uploadedFileID + " has been uploaded to the server")
            elif message[0:3] == 'SCS':
                split_message = message.split()
                if len(split_message) != 3:
                    print("> SCS command requires fileID and computationOperation as arguements")
                else:
                    fileID = split_message[1]
                    computationOperation = split_message[2]
                    if not (is_int(fileID) and computationOperation in ['MAX', 'MIN', 'SUM', 'AVERAGE']):
                        print("> The file ID is supposed to be an integer or the computation operation is supposed to be ['MAX', 'MIN', 'SUM', 'AVERAGE']")
                    else:
                        fileName = username + "-"+fileID+".txt"
                        temp_computation = 'SCS,'+fileName + ',' + computationOperation + ',' + username + ',' + fileID
                        clientSocket.sendall(temp_computation.encode())
                        data = clientSocket.recv(1024)
                        receivedMessage = data.decode()
                        if receivedMessage == 'SCS File Error':
                            print("> The file " + fileName + ' does not exist at the server side.')
                        elif 'SCS Success' in receivedMessage:
                            result = receivedMessage.split(',')[1]
                            message_to_display = "> (" + computationOperation + ") result on the file (ID:" + fileID + ") returned from the server is: " + str(result)
                            print(message_to_display)
            elif message[0:3] == 'DTE':
                split_message = message.split()
                if len(split_message) != 2:
                    print("> DTE command requires fileID as an arguement")
                else:
                    fileID = split_message[1]
                    if not is_int(fileID):
                        print("> The file ID is supposed to be an integer")
                    else:
                        fileName = username+"-"+fileID+".txt"
                        temp_deletion = 'DTE,'+fileID+","+fileName+","+username
                        clientSocket.sendall(temp_deletion.encode())
                        data = clientSocket.recv(1024)
                        receivedMessage = data.decode()
                        if receivedMessage == 'DTE File Error':
                            print("> The file provided does not exist in the server, hence, it could not be deleted")
                        elif receivedMessage == 'DTE Success':
                            message_to_display = "> The file with ID of " + fileID + " from edge device " + username + " has been deleted, deletion log file has been updated"
                            print(message_to_display)
            elif message == 'AED':
                temp_AED = 'AED,'+username
                clientSocket.sendall(temp_AED.encode())
                data = clientSocket.recv(1024)
                receivedMessage = data.decode()
                if receivedMessage[0:3] == 'AED':
                    split_logged_users = receivedMessage.split(';;')
                    if split_logged_users[1].strip() == '' and len(split_logged_users) == 2:
                        print("> No other active edge devices")
                    else:
                        for i in range(len(split_logged_users)):
                            if i > 0 and split_logged_users[i].strip() != '':
                                print("> " + split_logged_users[i].split(',')[0] + ";" + split_logged_users[i].split(',')[2] + ";" + split_logged_users[i].split(',')[3][:-1] + "; " + "active since " + split_logged_users[i].split(',')[1])

            elif message == 'OUT':
                temp_OUT = "OUT," + username
                clientSocket.sendall(temp_OUT.encode())
                data = clientSocket.recv(1024)
                receivedMessage = data.decode()
                if receivedMessage == "OUT Success":
                    print("> Bye, " + username)
                clientSocket.close()
                exit()

            elif message[0:3] == 'UVF':
                split_message = message.split()
                if len(split_message) != 3:
                    print("> The UVF command requires the username and fileName as arguements")
                else:
                    username1 = split_message[1]
                    fileName = split_message[2]
                    temp_AED = 'AED,'+username
                    clientSocket.sendall(temp_AED.encode())
                    data = clientSocket.recv(1024)
                    receivedMessage = data.decode()
                    new_user_IP = ""
                    user_UDP = ""
                    if receivedMessage[0:3] == 'AED':
                        split_logged_users = receivedMessage.split(';;')
                        if split_logged_users[1].strip() == '' and len(split_logged_users) == 2:
                            print("> " + username1 + " is not active")
                        else:
                            userFound = False
                            for i in range(len(split_logged_users)):
                                if i > 0 and split_logged_users[i].strip() != '':
                                    if split_logged_users[i].split(',')[0].strip() == username1:
                                        userFound = True
                                        new_user_IP = split_logged_users[i].split(',')[2].strip()
                                        user_UDP = split_logged_users[i].split(',')[3][:-1].strip()
                                        break
                            if userFound:
                                sendFileUDP(new_user_IP,user_UDP, fileName)
                            else:
                                print("> " + username1 + " is not active.")
        else:
            print("> Error. Invalid command!")

clientSocket.close()