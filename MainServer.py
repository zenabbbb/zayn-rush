import socket
import threading
import time
import sqlite3
import os
import json
import datetime
#database initialization
DB_PATH = "history.db"

def init_db():
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    #create matches history table
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1 TEXT,
        player2 TEXT,
        result TEXT
    )''')
    #create users table with additional fields for car choice and stats
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        last_login TEXT,
        car TEXT,
        wins INTEGER DEFAULT 0,
        games INTEGER DEFAULT 0
    )''')
    #add new columns if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN car TEXT")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN wins INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN games INTEGER DEFAULT 0")
    except Exception:
        pass
    db.commit()
    db.close()

init_db()

def log_match(player1, player2):
    """Insert a new match record with result 'Pending'. Return the match ID."""
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    cursor.execute("INSERT INTO history (player1, player2, result) VALUES (?, ?, ?)",
                   (player1, player2, "Pending"))
    match_id = cursor.lastrowid  # get auto-incremented match ID
    db.commit()
    db.close()
    return match_id

def register_user(username, password, car):
    """Register a new user with preferred car. Returns True if success, False if username exists."""
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, last_login, car, wins, games) VALUES (?, ?, ?, ?, ?, ?)",
                       (username, password, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        car, 0, 0))
        db.commit()
        db.close()
        return True
    except sqlite3.IntegrityError:
        db.close()
        return False

def login_user(username, password):
    """Validate user credentials and update last login timestamp. Returns True if valid."""
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    if user:
        cursor.execute("UPDATE users SET last_login = ? WHERE username = ?",
                       (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
        db.commit()
        db.close()
        return True
    else:
        db.close()
        return False

def get_user_stats(username):
    """Retrieve a user's car choice, wins, games, and last login from the database."""
    db = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = db.cursor()
    cursor.execute("SELECT car, wins, games, last_login FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    db.close()
    if row:
        car, wins, games, last_login = row
        return {
            "car": car or "N/A", 
            "wins": wins if wins is not None else 0, 
            "games": games if games is not None else 0, 
            "last_login": last_login or ""
        }
    return None


#global variables for online clients

clients = {}           # Map username -> {"conn": connection_socket, "ip": client_ip}
clients_lock = threading.Lock()
pending_challenges = {}  # Map challenged_username -> challenger_username
pending_lock = threading.Lock()


#client handler function

def handle_client(conn, addr):
    """
    Handle a new client connection.
    Supports:
      - G: get list of online players
      - LOGIN:<user>:<pass>
      - REGISTER:<user>:<pass>:<car>
      Then listens for challenge commands or results.
    """
    username = None
    try:
        #short timeout for initial data to see if it's a quick query
        conn.settimeout(0.5)
        try:
            initial_data = conn.recv(1024).decode().strip()
        except socket.timeout:
            initial_data = ""
        conn.settimeout(None)
        if initial_data == "":
            #no data sent, close the connection
            conn.close()
            return

        if initial_data.upper() == "G":
            #send list of active players with stats
            players_list = []
            with clients_lock:
                for user, info in clients.items():
                    #include display name (here just username) and stats
                    stats = get_user_stats(user) or {"car": "N/A", "wins": 0, "games": 0, "last_login": ""}
                    players_list.append({
                        "username": user,
                        "display_name": user,
                        **stats
                    })
            if players_list:
                conn.send((json.dumps(players_list) + "\n").encode())
            else:
                conn.send("No active players\n".encode())
            conn.close()
            return

        if initial_data.startswith("LOGIN:"):
            #handle login attempt
            parts = initial_data.split(":")
            if len(parts) >= 3:
                username = parts[1]
                password = parts[2]
                if login_user(username, password):
                    conn.send("LOGIN_SUCCESS\n".encode())
                    #keep this connection open for further communication
                    with clients_lock:
                        clients[username] = {"conn": conn, "ip": addr[0]}
                else:
                    conn.send("LOGIN_FAILED\n".encode())
                    conn.close()
                    return
            else:
                conn.send("INVALID_FORMAT\n".encode())
                conn.close()
                return

        elif initial_data.startswith("REGISTER:"):
            #handle new user registration
            parts = initial_data.split(":")
            if len(parts) >= 4:
                reg_username = parts[1]
                reg_password = parts[2]
                reg_car = parts[3] if parts[3] else "A"
                if register_user(reg_username, reg_password, reg_car):
                    conn.send("REGISTER_SUCCESS\n".encode())
                else:
                    conn.send("REGISTER_FAILED\n".encode())
                conn.close()
                return
            else:
                conn.send("INVALID_FORMAT\n".encode())
                conn.close()
                return

        else:
            #if the request is not recognized, close connection
            conn.send("INVALID_REQUEST\n".encode())
            conn.close()
            return

        #at this point, the client is logged in and kept in `clients` dict.
        #listen for commands (challenge requests, responses, results) from this client.
        while True:
            try:
                data = conn.recv(1024).decode().strip()
            except Exception:
                break  # socket likely closed or error
            if not data:
                break

            #challenge request
            if data.startswith("CHALLENGE:"):
                #expected format: challenge:<challenger>:<challenged>
                parts = data.split(":")
                if len(parts) >= 3:
                    challenger = parts[1]
                    challenged = parts[2]
                    if not challenged or challenged == challenger:
                        #invalid challenge target
                        conn.send("OPPONENT_NOT_AVAILABLE\n".encode())
                        continue
                    with clients_lock:
                        target_info = clients.get(challenged)
                    if target_info:
                        with pending_lock:
                            #ensure target isn't already challenged
                            if challenged in pending_challenges:
                                conn.send("OPPONENT_NOT_AVAILABLE\n".encode())
                                continue
                            challenger_car = parts[3] if len(parts) >= 4 else "A"
                            pending_challenges[challenged] = {"challenger": challenger, "car": challenger_car }
                        try:
                            #forward challenge request to the target
                            target_conn = target_info["conn"]
                            target_conn.send(f"CHALLENGE_REQUEST:{challenger}\n".encode())
                        except Exception:
                            #if target isn't reachable, clean up and notify challenger
                            with clients_lock:
                                clients.pop(challenged, None)
                            with pending_lock:
                                pending_challenges.pop(challenged, None)
                            conn.send("OPPONENT_NOT_AVAILABLE\n".encode())
                            continue
                        conn.send("CHALLENGE_SENT\n".encode())
                    else:
                        conn.send("OPPONENT_NOT_AVAILABLE\n".encode())

            elif data.startswith("CHALLENGE_RESPONSE:"):
                #expected format: challenge_response:<responder>:accept/reject
                parts = data.split(":")
                if len(parts) >= 3:
                    responder = parts[1]
                    response = parts[2].upper()
                    responder_live_car = parts[3] if len(parts) >= 4 else None
                    challenger = None
                    with pending_lock:
                        info = pending_challenges.pop(responder, None)
                        if info:
                             challenger = info["challenger"]
                             challenger_car = info["car"]
                    if response == "ACCEPT" and challenger:
                        #challenge accepted – set up match
                        with clients_lock:
                            challenger_info = clients.get(challenger)
                            responder_info = clients.get(responder)
                        if not challenger_info or not responder_info:
                            #one player went offline; inform whoever is still connected
                            try:
                                conn.send("OPPONENT_NOT_AVAILABLE\n".encode())
                            except Exception:
                                pass
                            continue
                        #log match in history and prepare role assignments
                        match_id = log_match(challenger, responder)
                        challenger_conn = challenger_info["conn"]
                        responder_conn = responder_info["conn"]
                        challenger_ip = challenger_info["ip"]
                        responder_ip = responder_info["ip"]
                        #retrieve preferred cars for each player
                        challenger_stats = get_user_stats(challenger) or {}
                        responder_stats = get_user_stats(responder) or {}
                        responder_car = (
    responder_live_car              #use live choice if client sent it
    if responder_live_car else
    responder_stats.get("car", "A") #otherwise fall back to DB
)

                        try:
                            #the responder will act as p2p server
                            responder_conn.send(f"MATCH_START:{match_id}:server:{challenger_ip}:12345:{challenger_car}:{challenger}\n".encode())
                        except Exception as e:
                            print("Error sending match start to responder:", e)
                            continue  # If we fail to notify responder, abort match setup
                        try:
                            #the challenger will act as p2p client
                            challenger_conn.send(f"MATCH_START:{match_id}:client:{responder_ip}:12345:{responder_car}:{responder}\n".encode())
                        except Exception as e:
                            print("Error sending match start to challenger:", e)
                            #even if challenger notification fails, responder was told to wait for connection
                    elif response == "REJECT" and challenger:
                        #challenge was declined
                        with clients_lock:
                            challenger_info = clients.get(challenger)
                        if challenger_info:
                            try:
                                challenger_info["conn"].send("CHALLENGE_REJECTED\n".encode())
                            except Exception:
                                pass

            elif data.startswith("RESULT:"):
                #expected format: result:player1:player2:winner
                parts = data.split(":")
                if len(parts) >= 4:
                    p1 = parts[1]
                    p2 = parts[2]
                    winner = parts[3]
                    result_text = winner if winner != "DRAW" else "Draw"
                    db = sqlite3.connect(DB_PATH, check_same_thread=False)
                    cur = db.cursor()
                    #update match result if still pending
                    cur.execute("""UPDATE history
                                   SET result = ?
                                   WHERE ((player1 = ? AND player2 = ?) OR (player1 = ? AND player2 = ?))
                                   AND result = 'Pending'""",
                                (result_text, p1, p2, p2, p1))
                    #update win and game counts
                    if winner != "DRAW":
                        cur.execute("UPDATE users SET wins = wins + 1 WHERE username = ?", (winner,))
                    cur.execute("UPDATE users SET games = games + 1 WHERE username = ?", (p1,))
                    cur.execute("UPDATE users SET games = games + 1 WHERE username = ?", (p2,))
                    db.commit()
                    db.close()
                    try:
                        conn.send("RESULT_UPDATED\n".encode())
                    except Exception:
                        pass

            elif data.startswith("STATUS:"):
                #simple acknowledgment for status updates (not heavily used in this project)
                conn.send("STATUS_UPDATED\n".encode())

            else:
                #unrecognized command
                conn.send("INVALID_COMMAND\n".encode())
    except Exception as e:
        print("Error handling client:", e)
    finally:
        #cleanup when client disconnects
        if username:
            with clients_lock:
                clients.pop(username, None)
            #handle any pending challenge involving this user
            with pending_lock:
                #if this user was challenged and hasn't responded yet, notify challenger
                if username in pending_challenges:
                    challenger = pending_challenges.pop(username, None)
                    if challenger:
                        with clients_lock:
                            challenger_info = clients.get(challenger)
                        if challenger_info:
                            try:
                                challenger_info["conn"].send("OPPONENT_NOT_AVAILABLE\n".encode())
                            except Exception:
                                pass
                #if this user had sent a challenge and then disconnected, remove it
                to_remove = [target for target, chall in pending_challenges.items() if chall == username]
                for target in to_remove:
                    pending_challenges.pop(target, None)
                    with clients_lock:
                        target_info = clients.get(target)
                    if target_info:
                        try:
                            target_info["conn"].send("OPPONENT_NOT_AVAILABLE\n".encode())
                        except Exception:
                            pass
        try:
            conn.close()
        except Exception:
            pass


#main server loop

def main():
    HOST = ""  # Listen on all interfaces (0.0.0.0)
    PORT = 8005
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen()
    print("Server is running on port", PORT)
    print("Waiting for connections...")
    while True:
        conn, addr = server.accept()
        print(f"New connection from {addr}")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
