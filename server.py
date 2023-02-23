from socket import *
from threading import Thread
import sys, select
from datetime import datetime
import json
import os

if len(sys.argv) != 3:
    print("\n===== Error usage, python3 server3.py <server-port> <number-of-consecutive-failed-attempts> ======\n")
    exit(0)

serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
numberFailedAttempts = int(sys.argv[2])
if not (1 <= numberFailedAttempts <= 5):
    print("Invalid number of allowed failed consecutive attempts: " + str(numberFailedAttempts) + ". The valid value of argument number is an integer between 1 and 5")
    exit(0)
serverAddress = (serverHost, serverPort)

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)

failedAttempts = {}
blockedIds = {}
userLoggedIn = []

def removeFromFailedAttempts(username):
    # Removing user from failed attempts
    if username in failedAttempts.keys():
        del failedAttempts[username]

def removeClientFromBlocked(username):
    # Removing user from blocked users
    if username in blockedIds.keys():
        del blockedIds[username]

def getCredentials():
    # getting credentials and storing in dictionary
    temp = {}
    with open('credentials.txt') as f1:
        data = f1.readlines()
    for i in data:
        temp[i.split()[0]] = i.split()[1]
    return temp

def checkCorrectCredentials(username, password, credentials):
    # checking if credentials are correct
    return username in credentials.keys() and password == credentials[username]

def increaseFailedAttempts(username):
    # increasing failed attempts of user on invalid login
    if username in failedAttempts.keys():
        failedAttempts[username] += 1
    else:
        failedAttempts[username] = 1

def checkBlocked(username):
    # Checking if user should be blocked or not
    return failedAttempts[username] < numberFailedAttempts

def addInBlocked(username):
    # blocking the user
    blockedIds[username] = datetime.now()

def getFilesInCurrentDir():
    # get Names of files in current directory
    return [f for f in os.listdir('.') if os.path.isfile(f)]

def addActiveDeviceInLogFile(username, clientUDPPort):
    # Adding user in edge device log file
    now = datetime.now()
    hostname = gethostname()    
    IPAddr = gethostbyname(hostname)
    files = getFilesInCurrentDir()
    if "edge-device-log.txt" in files:
        # updating if file already exists
        with open("edge-device-log.txt", 'r+') as f:
            allDevices = f.readlines()
            line = ""
            line += str(len(allDevices) + 1) + "; " + now.strftime("%d %B %Y %H:%M:%S") + "; " + username + "; " + IPAddr + "; " + clientUDPPort + "\n"
            f.write(line)
    else:
        # creating a file and writing to it if not exists already
        with open("edge-device-log.txt", 'w') as f:
            line = ""
            line += str(1) + "; " + now.strftime("%d %B %Y %H:%M:%S") + "; " + username + "; " + IPAddr + "; " + clientUDPPort + "\n"
            f.write(line)

def upload_file(fileName, dataInFile):
    # uploading edge data file the user requested
    if os.path.isdir('./uploaded_data'):
        # if path already exists
        path = './uploaded_data/' + fileName
        with open(path, 'w') as f1:
            f1.write(dataInFile)
    else:
        # else make the directory and upload
        os.mkdir('./uploaded_data')
        path = './uploaded_data/' + fileName
        with open(path, 'w') as f1:
            f1.write(dataInFile)

def writeInUploadLog(temp_log):
    # writing in upload log that a file was uploaded
    with open('upload-log.txt', 'r') as f1:
        uploaded_log = f1.readlines()
    uploaded_log.append(temp_log)
    with open('upload-log.txt', 'w') as f2:
        final_upload = ""
        for i in uploaded_log:
            final_upload += i
        f2.write(final_upload)

def getFilesInUploadedData():
    # get Names of files in uploaded data
    return [f for f in os.listdir('./uploaded_data') if os.path.isfile(f)]

class ClientThread(Thread):
    global failedAttempts
    global blockedIds
    global userLoggedIn
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        
        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True

    def run(self):
        while self.clientAlive:
            data = self.clientSocket.recv(1024)
            message = data.decode()

            if message == '':

                self.clientAlive = False
                print("===== the user disconnected - ", clientAddress)
                break

            if 'credentials' in message:
                # if message is sending the credentials
                # extracting username password and udpport from the message
                username = message.split(',')[1]
                password = message.split(',')[2]
                clientUDPPort = message.split(',')[3]
                print("[recv] Credentials received")
                print("Verifying...")
                # logging in
                self.process_login(username, password, clientUDPPort)
            
            elif 'UED' in message:
                # if the message has upload edge data
                fileName = message.split(',')[1]
                dataInFile = message.split(',')[2]
                username = message.split(',')[3]
                fileID = message.split(',')[4]
                dataAmount = message.split(',')[5]
                print("> Edge device" + username + " issued UED command")
                print("> A data file is received from edge device " + username)
                self.process_upload_edge_data(fileName, dataInFile, username, fileID, dataAmount)

            elif 'SCS' in message:
                # if the message is SCS
                fileName = message.split(',')[1]
                computationOperation = message.split(',')[2]
                username = message.split(',')[3]
                fileID = message.split(',')[4]
                print("> Edge device " + username + " requested a computation on the file with ID of " + fileID)
                files = getFilesInUploadedData()
                if not fileName in files:
                    message_to_send = 'SCS File Error'
                    self.clientSocket.send(message_to_send.encode())
                else:
                    pathComputationFile = './uploaded_data/' + fileName
                    with open(pathComputationFile , 'r') as f1:
                        dataForComputation = f1.readlines()
                    if computationOperation == 'MAX':
                        self.process_scs_max(dataForComputation, computationOperation, fileID, username)
                    elif computationOperation == 'MIN':
                        self.process_scs_min(dataForComputation, computationOperation, fileID, username)
                    elif computationOperation == 'SUM':
                        self.process_scs_sum(dataForComputation, computationOperation, fileID, username)
                    elif computationOperation == 'AVERAGE':
                        self.process_scs_average(dataForComputation, computationOperation, fileID, username)

            elif 'DTE' in message:
                # if the message has DTE
                fileID = message.split(',')[1]
                fileName = message.split(',')[2]
                username = message.split(',')[3]
                print("> Edge device " + username + " issued DTE command, the file ID is " + fileID)
                files = getFilesInUploadedData()
                if not fileName in files:
                    message_to_send = 'DTE File Error'
                    print("> Error the file to be deleted: " + fileName + " was not found in the server")
                    self.clientSocket.send(message_to_send.encode())
                else:
                    self.delete_dataFile(fileName)
                    filesInSame = getFilesInUploadedData()
                    now = datetime.now()
                    temp_deletion_log = username + "; " + now.strftime("%d %B %Y %H:%M:%S") + "; " + fileID + "; " + str(dataAmount) + "\n"
                    if 'deletion-log.txt' in filesInSame:
                        self.writeInDeletionLog(temp_deletion_log)
                    else:
                        with open('deletion-log.txt', 'w') as f1:
                            f1.write(temp_deletion_log)
                    message_to_display = "> Return message " + "The file with ID of " + fileID + " from edge device " + username + " has been deleted, deletion log file has been updated"
                    print(message_to_display)
                    self.clientSocket.send('DTE Success'.encode())

            elif 'AED' in message:
                # if the message has AED
                username = message.split(',')[1]
                print("> Edge device " + username + " issued AED command")
                with open('edge-device-log.txt', 'r') as f1:
                    loggedDevices = f1.readlines()
                all_logged_users = self.getAllLoggedUsers(loggedDevices, username)
                self.clientSocket.send(all_logged_users.encode())
                split_logged_users = all_logged_users.split(';;')
                self.printActiveusers(split_logged_users)

            elif 'OUT' in message:
                # if the message has OUT
                username = message.split(',')[1]
                with open('edge-device-log.txt', 'r') as f1:
                    active_edge_devices = f1.readlines()
                new_active_devices = self.getNewActiveDevices(username, active_edge_devices)
                final_active_devices = self.getFinalActiveDevices(new_active_devices)
                with open('edge-device-log.txt', 'w') as f2:
                    for i in final_active_devices:
                        f2.write(i)
                print("> " + username + " exited the edge network")
                self.clientSocket.send('OUT Success'.encode())

            elif message == 'getActiveDevices':
                # if the message wasnts all active devices
                self.sendAllActiveDevices()


    def process_login(self, username, password, clientUDPPort):
        credentials = getCredentials() # getting credentials
        if username in blockedIds: # checking username in blocked IDs
            if (datetime.now() - blockedIds[username]).total_seconds() <= 10:
                # if still blocked tell client
                self.clientSocket.send('blocked'.encode())
            else:
                # else remove from blocked and failed Attempts
                removeClientFromBlocked(username)
                removeFromFailedAttempts(username)
                if checkCorrectCredentials(username, password, credentials):
                    # credentials provided now are correct
                    addActiveDeviceInLogFile(username, clientUDPPort)
                    self.clientSocket.send('Correct Credentials'.encode())
                else:
                    # else if not correct credentials
                    increaseFailedAttempts(username)
                    if not checkBlocked(username):
                        addInBlocked(username)
                        self.clientSocket.send('blocked'.encode())
                    else:
                        self.clientSocket.send('Try again'.encode())

        else:
            # if not blocked
            if checkCorrectCredentials(username, password, credentials):
                # if credentials are correct
                removeClientFromBlocked(username)
                removeFromFailedAttempts(username)
                addActiveDeviceInLogFile(username, clientUDPPort)
                self.clientSocket.send('Correct Credentials'.encode())
            else:
                # if credentials are not correct
                increaseFailedAttempts(username)
                if not checkBlocked(username):
                    addInBlocked(username)
                    self.clientSocket.send('blocked'.encode())
                else:
                    self.clientSocket.send('Try again'.encode())

    def process_upload_edge_data(self, fileName, dataInFile, username, fileID, dataAmount):
        upload_file(fileName, dataInFile)
        files = getFilesInCurrentDir()
        now = datetime.now()
        temp_log = ""
        temp_log += username + '; ' + now.strftime("%d %B %Y %H:%M:%S") + '; ' + fileID + '; ' + dataAmount + "\n"
        if 'upload-log.txt' in files:
            writeInUploadLog(temp_log)
        else:
            with open('upload-log.txt', 'w') as f2:
                f2.write(temp_log)
        print("> Return message: The file with ID of " + fileID + " has been received, upload-log.txt file has been updated")
        message_to_send = 'uploaded' + ',' + fileID
        self.clientSocket.send(message_to_send.encode())

    def process_scs_max(self, dataForComputation, computationOperation, fileID, username):
        max_number = 0 
        for i in dataForComputation:
            if int(i) > max_number:
                max_number = int(i)
        message_to_send = "> Return message " + computationOperation + " has been made on edge device " + username + " data file (ID:" + fileID + "), the result is " + str(max_number)
        print(message_to_send)
        temp_string = 'SCS Success,'+str(max_number)
        self.clientSocket.send(temp_string.encode())

    def process_scs_min(self, dataForComputation, computationOperation, fileID, username):
        min_number = int(dataForComputation[0])
        for i in dataForComputation:
            if int(i) < min_number:
                min_number = int(i)
        message_to_send = "> Return message " + computationOperation + " has been made on edge device " + username + " data file (ID:" + fileID + "), the result is " + str(min_number)
        print(message_to_send)
        temp_string = 'SCS Success,'+str(min_number)
        self.clientSocket.send(temp_string.encode())

    def process_scs_sum(self, dataForComputation, computationOperation, fileID, username):
        sum_SCS = 0
        for i in dataForComputation:
            sum_SCS += int(i)
        message_to_send = "> Return message " + computationOperation + " has been made on edge device " + username + " data file (ID:" + fileID + "), the result is " + str(sum_SCS)
        print(message_to_send)
        temp_string = 'SCS Success,'+str(sum_SCS)
        self.clientSocket.send(temp_string.encode())

    def process_scs_average(self, dataForComputation, computationOperation, fileID, username):
        average_SCS = 0
        length = len(dataForComputation)
        sum_SCS = 0
        for i in dataForComputation:
            sum_SCS += int(i)
        average_SCS = sum_SCS/length
        message_to_send = "> Return message " + computationOperation + " has been made on edge device " + username + " data file (ID:" + fileID + "), the result is " + str(average_SCS)
        print(message_to_send)
        temp_string = 'SCS Success,'+str(average_SCS)
        self.clientSocket.send(temp_string.encode())

    def delete_dataFile(self, fileName):
        path_deletion_file = './uploaded_data/'+fileName
        with open(path_deletion_file, 'r') as f2:
            dataAmount = len(f2.readlines())
        os.remove(path_deletion_file)

    def writeInDeletionLog(self, temp_deletion_log):
        with open('deletion-log.txt', 'r') as f1:
            deletion_data = f1.readlines()
        deletion_data.append(temp_deletion_log)
        with open('deletion-log.txt', 'w') as f1:
            for i in deletion_data:
                f1.write(i)

    def getAllLoggedUsers(self, loggedDevices, username):
        logged_users = "AED;; "
        for i in loggedDevices:
            splitLog = i.split(';')
            username_logged = splitLog[2]
            time_logged = splitLog[1]
            IPAddress = splitLog[3]
            UDPPort = splitLog[4]
            if username_logged.strip() != username.strip():
                logged_users += username_logged + "," + time_logged + "," + IPAddress + "," + UDPPort + ";;"
        return logged_users

    def printActiveusers(self, split_logged_users):
        print("> Return messages: ")
        if len(split_logged_users) == 2 and split_logged_users[1].strip() == "":
            print("No other active devices")
        else:
            for i in range(len(split_logged_users)):
                if i > 0 and split_logged_users[i].strip() != "":
                    print(split_logged_users[i].split(',')[0] + ";" + split_logged_users[i].split(',')[2] + ";" + split_logged_users[i].split(',')[3][:-1] + "; " + "active since " + split_logged_users[i].split(',')[1])

    def getNewActiveDevices(self, username, active_edge_devices):
        new_active_devices = []
        for i in active_edge_devices:
            if i.split(';')[2].strip() != username.strip():
                new_active_devices.append(i)
        return new_active_devices

    def getFinalActiveDevices(self, new_active_devices):
        final_active_devices = []
        if new_active_devices != []:
            for i in range(len(new_active_devices)):
                temp_deletion_log_new = ""
                temp_deletion_log_new += str(i+1) + new_active_devices[i][1:]
                final_active_devices.append(temp_deletion_log_new)
        return final_active_devices

    def sendAllActiveDevices(self):
        with open('edge-device-log.txt', 'r') as f1:
            active_edge_devices = f1.readlines()
        final_string = "allActiveDevices;;"
        for i in active_edge_devices:
            final_string += i + ";;"
        self.clientSocket.send(final_string.encode())

print("\n===== Server is running =====")
print("===== Waiting for connection request from clients...=====")


while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()

