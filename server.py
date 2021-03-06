#!/usr/bin/env python3

"""
    Server side of Assignment 1 for ECE 4564.
    Handles:
    1. Receiving question from client.
    2. Speaking question.
    3. Sending a receiving from WolframAlpha API.
    4. Sending answer to client.
"""

import os
import sys
import argparse
import socket

from cryptography.fernet import Fernet
import wolframalpha
import hashlib
import pickle
from gtts import gTTS

from serverKeys import wolfram_alpha_appid


def checkpoint(message):
    """Prints [Checkpoint] <message>"""
    print("[Checkpoint] {}".format(message))

def encrypt_data(data, key):
    """Encrypt given data and returns key, ciphertest, and md5"""
    # Has to be the same key because the client only has the key it 
    #     sent the data with
    cipher_suite = Fernet(key)
    # Defaults to utf-8
    bytedata = data.encode()
    # Encrypt WA Answer
    ciphertext = cipher_suite.encrypt(bytedata)

    # Determine the md5 of ciphertext
    temp = hashlib.md5()
    temp.update(ciphertext)
    md5 = temp.digest()

    return ciphertext, md5

def ask_wa(message):
    """Asks Wolfram Alpha messasge"""
    checkpoint("Sending question to Wolframalpha: {}".format(message))

    # Get answer from WA
    client = wolframalpha.Client(wolfram_alpha_appid)
    res = client.query(message)
    
    # Handle bad queries to WA
    try:
        answer = next(res.results).text
    except Exception as ex:
        answer = "Wolfram Alpha was unable to find an answer for {}. \
            Please try something else.".format(message)

    checkpoint("Received answer to Wolframalpha: {}".format(answer))

    return answer

def speak(message):
    """Speaks given message"""
    checkpoint("Speaking: {}".format(message))
   
    tts = gTTS(text=message, lang='en')
    tts.save("./saythis.mp3")
    os.system("mplayer ./saythis.mp3 > /dev/null 2>&1")

def decrypt_data(data):
    """Verify md5 and decrypt data"""
    # Data should be formatted as the tuple: (key, ciphertext, md5)
    
    # Extract key & decrypt data
    key = data[0]
    cipher_suite = Fernet(key)
    plaintext = cipher_suite.decrypt(data[1])

    # Get md5 of data
    temp = hashlib.md5()
    temp.update(data[1])
    md5 = temp.digest()

    return key, plaintext, md5

def accept_connections(socket, size):
    """Repeatedly accepts and handles new client connections"""
    while 1:
        client, address = socket.accept()
        client_addr = client.getpeername()[0]
        client_port = client.getpeername()[1]
        checkpoint("Accepted client connection from {} on port {}".format(
            client_addr, client_port))

        data = client.recv(size)
        if data:
            checkpoint("Received data: {}".format(data))

            # Decrypt data
            decryptedData = pickle.loads(data)
            recv_key, recv_plaintext, recv_md5 = decrypt_data(decryptedData)

            # Check if md5 is valid
            if decryptedData[2] == recv_md5:
                checkpoint("Checksum is VALID")
            else:
                checkpoint("Checksum is INVALID")
            
            checkpoint("Decrypt: Using Key: {} | Plaintext: {}"
                .format(recv_key, recv_plaintext, recv_md5))

            # Speak data
            speak(recv_plaintext.decode())

            # Ask WA
            answer = ask_wa(recv_plaintext.decode())

            # Encrypt response
            send_ciphertext, send_md5 = encrypt_data(answer, recv_key)
            checkpoint("Encrypt: Generated Key: {} | Ciphertext: {}"
                .format(recv_key, send_ciphertext))
            checkpoint("Generated MD5 Checksum: {}".format(send_md5))

            # Send response back to client
            dataTup = (recv_key, send_ciphertext, send_md5)
            send_data = pickle.dumps(dataTup)
            client.send(send_data)
            checkpoint("Sending data: {}".format(send_data))

            client.close()


def main():
    """Main function to manager the server"""
    # Parse command line args
    parser = argparse.ArgumentParser(description='Prossesses arguments')
    parser.add_argument('-p', help='Set the server port.')
    parser.add_argument('-b', help='Set the backlog size.')
    parser.add_argument('-z', help='Set the socket size')

    args = parser.parse_args()
    if args.p == None:
        print('Please set server port with the -p flag.')
        sys.exit(1)
    if args.b == None:
        print('Please set backlog size with the -b flag.')
        sys.exit(1)
    if args.z == None:
        print('Please set socket size with the -z flag.')
        sys.exit(1)

    host = '0.0.0.0'

    # Copy args into vars
    try:
        port =      int(args.p)
        backlog =   int(args.b)
        size =      int(args.z)
    except Exception as ex:
        print(ex)
        sys.exit(1)

    # Setup socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host,port))
    checkpoint("Created socket at {} on port {}".format(host, port))

    # Start listening
    checkpoint("Listening for client connections")
    s.listen(backlog)


    # Start accepting connections
    accept_connections(s, size)

main()
