import sys, time, random, threading, socket, pygame, os, json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtCore import Qt
from PyQt5.QtGui  import QIcon
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtCore    import Qt

#login dialog
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        #absolute path to image
        bg = r"resources/gui background/login.png"
        #convert backslashes -> forward slashes so qt can load it
        bg = bg.replace("\\", "/")

        self.setObjectName("LoginDialog")
        self.setStyleSheet(f"""
            QDialog#LoginDialog {{
                border-image: url("{bg}") 0 0 0 0 stretch stretch;
                padding: 20px;
            }}
            /* make all labels bold + white */
            QDialog#LoginDialog QLabel {{
                color: white;
                font-weight: bold;
            }}
            QLineEdit, QComboBox, QPushButton {{
                background: rgba(255,255,255,200);
            }}
        """)




        self.setWindowTitle("Login")
        self.setModal(True)
        self.username = ""
        self.password = ""
        self.is_guest = False
        self.setup_ui()

    def setup_ui(self):
        self.setWindowIcon(QIcon("resources/ui/login_icon.png"))
        self.resize(900, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20,20,20,20)
        main_layout.setSpacing(15)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignCenter)
        form.setHorizontalSpacing(10)

        #username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter your username")
        form.addRow("Username:", self.username_edit)

        #password
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Enter your password")
        form.addRow("Password:", self.password_edit)

        #server ip
        self.server_ip_edit = QLineEdit("127.0.0.1")
        self.server_ip_edit.setPlaceholderText("Server IP (e.g. 192.168.1.5)")
        form.addRow("Server IP:", self.server_ip_edit)

        #note: the car‐choice combo is removed here 
        main_layout.addLayout(form)

        #buttons row (unchanged)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        for text, slot in [
            ("Login",    self.login),
            ("Register", self.register),
            ("Play as Guest", self.play_as_guest)
        ]:
            btn = QPushButton(text)
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(slot)
            btn.setStyleSheet("font-size:14px; padding:6px 12px;")
            btn_row.addWidget(btn)
        main_layout.addLayout(btn_row)

        self.setLayout(main_layout)



    def login(self):
        #attempt to log in with given credentials
        self.username = self.username_edit.text().strip()
        self.password = self.password_edit.text().strip()
        if not self.username or not self.password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
        server_ip = self.server_ip_edit.text().strip() or "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((server_ip, 8005))
            s.send(f"LOGIN:{self.username}:{self.password}".encode())
            response = s.recv(1024).decode().strip()
            s.close()
            if response == "LOGIN_SUCCESS":
                self.is_guest = False
                self.accept()  #Close dialog and proceed
            else:
                QMessageBox.warning(None, "Login Failed", "Invalid username or password")
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", f"Could not connect to server: {e}")#hon4

    def register(self):
        #attempt to register a new account with chosen car
        self.username = self.username_edit.text().strip()
        self.password = self.password_edit.text().strip()
        car_choice = "A" 

        if not self.username or not self.password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        if len(self.password) < 6:
            QMessageBox.warning(None, "Password Too Short", "Password must be at least 6 characters long")
            return
        server_ip = self.server_ip_edit.text().strip() or "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((server_ip, 8005))
            s.send(f"REGISTER:{self.username}:{self.password}:{car_choice}".encode())
            response = s.recv(1024).decode().strip()
            s.close()
            if response == "REGISTER_SUCCESS":
                QMessageBox.information(None, "Registration Successful",
                         "Account created successfully. You can now log in.")
            else:
                QMessageBox.warning(None, "Registration Failed",
                    "Username already exists or invalid format")
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", f"Could not connect to server: {e}")

    def play_as_guest(self):
        #continue without logging in (guest mode)
        self.username = f"Guest_{random.randint(1000, 9999)}"
        self.is_guest = True
        self.accept()


#configuration & constants

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 30

#per-map lane boundaries (each map's lane_left and lane_right).
#adjust these values for each map to change road width boundaries.
MAP_LANE_LIMITS = {
    1: (200, 600),
    2: (200, 600),
    3: (200, 600),
    4: (200, 600),
    5: (200, 600)
}

LANE_LEFT = 200    # default; will be overridden per map in run_game
LANE_RIGHT = 600   # default; will be overridden per map in run_game
LANE_WIDTH = (LANE_RIGHT - LANE_LEFT) // 2

#added scaling & boundary constants ===
CAR_W, CAR_H = 200, 200    # car sprite (and hit-box) size
OBST_W, OBST_H = 70, 70    # obstacle sprite size
HITBOX_W, HITBOX_H = 10, 40  # hitbox size independent of sprite
ROAD_LEFT = LANE_LEFT
ROAD_RIGHT = LANE_RIGHT - CAR_W

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

#end‑of‑game image paths ────────────────────────────────────────
GAME_END_IMAGE_PATH = r"resources/endgame/game over.png"
YOU_WON_IMAGE_PATH  = r"resources/endgame/you won.png"
YOU_LOST_IMAGE_PATH = r"resources/endgame/you lose.png"
#


DIFFICULTY_SETTINGS = {
    "Easy":    {"health": 5, "obstacle_multiplier": 1},
    "Medium":  {"health": 4, "obstacle_multiplier": 2},
    "Hard":    {"health": 3, "obstacle_multiplier": 3},
    "Catastrophic": {"health": 1, "obstacle_multiplier": 4}
}

MAPS = {
    1: {
        "background": r"resources/Maps/image 1.jpg",
        "obstacles": [
            r"resources/Obstacles/candy (1).png",
            r"resources/Obstacles/candy (2).png",
            r"resources/Obstacles/candy (3).png"
        ]
    },
    2: {
        "background": r"resources/Maps/image 2.jpg",
        "obstacles": [
            r"resources/Obstacles/beach (1).png",
            r"resources/Obstacles/beach (2).png",
            r"resources/Obstacles/beach (3).png"
        ]
    },
    3: {
        "background": r"resources/Maps/image 3.jpg",
        "obstacles": [
            r"resources/Obstacles/halloween (1).png",
            r"resources/Obstacles/halloween (2).png",
            r"resources/Obstacles/halloween (3).png"
        ]
    },
    4: {
        "background": r"resources/Maps/image 4.jpg",
        "obstacles": [
            r"resources/Obstacles/urban (1).png",
            r"resources/Obstacles/urban (2).png",
            r"resources/Obstacles/urban (3).png"
        ]
    },
    5: {
        "background": r"resources/Maps/image 5.jpg",
        "obstacles": [
            r"resources/Obstacles/winter (1).png",
            r"resources/Obstacles/winter (2).png",
            r"resources/Obstacles/winter (3).png"
        ]
    }
}

CAR_OPTIONS = {
    "Red": r"resources/CARS/car 1.png",
    "Pink": r"resources/CARS/car 2.png",
    "Blue": r"resources/CARS/car 3.png",
    "Green": r"resources/CARS/car 4.png"
}


#helper class for infinite scrolling background

class ScrollingBG:
    def __init__(self, surface):
        self.images = [surface.copy(), surface.copy()]
        self.y = [0, -SCREEN_HEIGHT]

    def draw(self, target, speed=5):
        for i in (0, 1):
            target.blit(self.images[i], (0, self.y[i]))
            self.y[i] += 2*speed
            #wrap image to create infinite scroll
            if self.y[i] >= SCREEN_HEIGHT:
                self.y[i] = -SCREEN_HEIGHT


#game classes (pygame)

class GameMap:
    """Loads map background and obstacle images for a given map ID."""
    def __init__(self, map_id):
        self.map_id = map_id
        self.background = pygame.transform.scale(
            pygame.image.load(MAPS[map_id]["background"]).convert(),
            (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.obstacle_images = [
            pygame.transform.scale(pygame.image.load(img).convert_alpha(), (OBST_W, OBST_H))
            for img in MAPS[map_id]["obstacles"]
        ]
        #note: lane boundaries are configured per map in run_game using map_lane_limits

class Car:
    """Represents a player's car in the game."""
    def __init__(self, lane, car_image_path):
        self.lane = lane
        image = pygame.image.load(car_image_path).convert_alpha()
        self.image = pygame.transform.scale(image, (CAR_W, CAR_H))
        self.rect = self.image.get_rect()
        #position car at bottom of its lane (0 = left lane, 1 = right lane)
        self.rect.x = LANE_LEFT + lane * LANE_WIDTH + LANE_WIDTH // 2 - self.rect.width // 2
        self.rect.y = SCREEN_HEIGHT - self.rect.height - 10
        self.health = 0
        self.hitbox = pygame.Rect(0, 0, HITBOX_W, HITBOX_H)
        self.hitbox.center = self.rect.center

    def move(self, dx):
        #move horizontally within road boundaries
        self.rect.x = min(max(self.rect.x + dx, ROAD_LEFT), ROAD_RIGHT)
        self.hitbox.center = self.rect.center

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Obstacle:
    """Represents an obstacle on the road."""
    def __init__(self, image, lane=None, x=None, y=None):
        #image is expected to be a pre-scaled surface
        self.image = image.copy()
        self.rect = self.image.get_rect()
        if x is not None and y is not None:
            #initialize obstacle at specified coordinates (for synced events)
            self.rect.x = x
            self.rect.y = y
        elif lane is not None:
            #place obstacle in specified lane at a random horizontal position within lane, and random spawn height above screen
            if lane == 0:
                lane_min = LANE_LEFT
                lane_max = LANE_LEFT + LANE_WIDTH - self.rect.width
            else:
                lane_min = LANE_LEFT + LANE_WIDTH
                lane_max = LANE_RIGHT - self.rect.width
            self.rect.x = random.randint(lane_min, lane_max)
            self.rect.y = random.randint(-SCREEN_HEIGHT, -50)
        else:
            #default position if no parameters given
            self.rect.x = LANE_LEFT
            self.rect.y = -50

    def move(self, dy):
        """Move obstacle vertically down the screen."""
        self.rect.y += 2*dy

    def draw(self, surface):
        surface.blit(self.image, self.rect)


#p2p networking 

running_network = False
#set up global variables for network role and event queue
network_role = None
events_queue = []  # queue of obstacle events to send (for host)

def p2p_send_thread(peer_socket, local_car):
    """Continuously send local car's position, health, and any new obstacle events to the peer."""
    global running_network
    #determine if this side is host (server) for sending obstacle data
    is_host = (network_role == "server")
    while running_network:
        try:
            #base state: send car x, y, health
            data = f"{int(local_car.rect.x)},{int(local_car.rect.y)},{int(local_car.health)}"
            if is_host and events_queue:
                #include one obstacle event in the message (index:x:y:imgindex)
                evt = events_queue.pop(0)
                idx = evt["index"]; ox = evt["x"]; oy = evt["y"]; img_idx = evt["img_index"]
                data += f",{idx}:{ox}:{oy}:{img_idx}"
            else:
                data += ",-1"
            data += "\n"
            peer_socket.send(data.encode())
        except Exception as e:
            #on send error, break out to end thread
            print(f"Send error: {e}")
            break
        time.sleep(0.03)  # ~33 sends per second

def p2p_receive_thread(peer_socket, remote_car, game_map):
    """Continuously receive opponent car's state (and new obstacle events) from the peer."""
    global running_network
    buffer = ""  # buffer for assembling complete messages
    while running_network:
        try:
            chunk = peer_socket.recv(1024).decode()
        except socket.timeout:
            continue  # no data received, just loop again to check running_network
        except Exception as e:
            #connection closed or error
            break
        if not chunk:
            break  # connection closed by peer
        buffer += chunk
        #process all complete lines in the buffer
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line.strip() == "":
                continue
            #parse the incoming line
            parts = line.split(",")
            if len(parts) < 3:
                continue  # not a valid state message
            try:
                opp_x = int(parts[0])
                opp_y = int(parts[1])
                opp_health = int(parts[2])
            except ValueError:
                continue  # skip malformed data
            #update opponent car's position and health
            remote_car.rect.x = opp_x
            remote_car.rect.y = opp_y
            remote_car.health = opp_health
            #check for obstacle sync data
            if len(parts) >= 4 and parts[3] != "-1":
                #an obstacle event is included
                evt_parts = parts[3].split(":")
                if len(evt_parts) >= 4:
                    try:
                        evt_idx = int(evt_parts[0])
                        evt_x = int(evt_parts[1])
                        evt_y = int(evt_parts[2])
                        evt_img_idx = int(evt_parts[3])
                    except ValueError:
                        evt_idx = None
                    if evt_idx is not None:
                        if evt_idx < len(obstacles):
                            #update existing obstacle in place
                            obstacles[evt_idx].rect.x = evt_x
                            obstacles[evt_idx].rect.y = evt_y
                            obstacles[evt_idx].image = game_map.obstacle_images[evt_img_idx].copy()
                        else:
                            #append new obstacle if index equals current length (in case of new spawn)
                            if 0 <= evt_img_idx < len(game_map.obstacle_images):
                                new_obs_img = game_map.obstacle_images[evt_img_idx]
                            else:
                                new_obs_img = game_map.obstacle_images[0]
                            obstacles.append(Obstacle(new_obs_img, x=evt_x, y=evt_y))
        #end while (processing lines)
    #end while (running_network loop)


#handshake helper functions (legacy support)

def connect_to_server(username, server_ip, opponent=None):
    """
    Fallback direct handshake with server for starting a match.
    (Uses legacy handshake mechanism if needed.)
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((server_ip, 8005))
        s.settimeout(None)
        #send username (simulate older protocol handshake)
        s.send(username.encode())
        _ = s.recv(1024).decode()           #"Enter your display name"
        s.send(username.encode())
        _ = s.recv(1024).decode()           # "Enter your peer-to-peer port"
        default_port = "12345"
        s.send(default_port.encode())
        if opponent:
            #if client, send opponent username to server to challenge
            _ = s.recv(1024).decode()       # "Enter opponent username"
            s.send(opponent.encode())
        #receive opponent info from server
        data = s.recv(1024).decode().strip()
        s.close()
        #expected format: "role:opponent_ip:opponent_port"
        details = data.split(":")
        if len(details) >= 3:
            role = details[0]
            opp_ip = details[1]
            opp_port = int(details[2])
            return {"success": True, "role": role, "opponent_ip": opp_ip, "opponent_port": opp_port}
        else:
            return {"success": False}
    except Exception as e:
        print(f"Handshake error: {e}")
        return {"success": False}

def establish_p2p_connection(connection_details):
    """
    Given connection details from the server handshake, establish a P2P socket.
    Returns the peer socket connected to the opponent.
    """
    role = connection_details["role"]
    if role == "server":
        #act as server: wait for incoming p2p connection on default port 12345
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("", connection_details.get("opponent_port", 12345)))
        server_sock.listen(1)
        peer_socket, addr = server_sock.accept()
        server_sock.close()
    else:
        #act as client: connect to opponent's ip on given port
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(1)  # Brief pause to ensure server is ready
        peer_socket.connect((connection_details["opponent_ip"], connection_details["opponent_port"]))
    return peer_socket


#game loop (offline & online modes)

def run_game(options):
    """Launch the racing game loop with given options (map, difficulty, car choices, networking info)."""
    global LANE_LEFT, LANE_RIGHT, LANE_WIDTH, ROAD_LEFT, ROAD_RIGHT
    global running_network, network_role, events_queue, obstacles
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    if options.get("single_player"):
        pygame.display.set_caption("EECE 350 Racing Game (Single Player)")
    else:
        pygame.display.set_caption("EECE 350 Racing Game (Multiplayer)")
    pygame.mixer.init()

    #load audio and explosion image
    try:
        pygame.mixer.music.load("resources/Sound Effects/Game Music.mp3")
        collision_sound = pygame.mixer.Sound("resources/Sound Effects/Crash Sound.mp3")
        countdown_sound = pygame.mixer.Sound("resources/Sound Effects/Countdown.mp3")
        explosion_image = pygame.image.load("resources/Obstacles/BOOM.png").convert_alpha()
        explosion_image = pygame.transform.scale(explosion_image, (50, 50))
    except Exception as e:
        print(f"Error loading game assets: {e}")
        return  # Cannot proceed without assets

    explosion_effects = []
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24)

    #game settings
    map_choice = options["map_choice"]
    difficulty = options["difficulty"]
    settings = DIFFICULTY_SETTINGS[difficulty]
    starting_health = settings["health"]
    obstacle_multiplier = settings["obstacle_multiplier"]
    car_color_choice = options["car_color"]

    #apply map-specific lane limits
    if map_choice in MAP_LANE_LIMITS:
        LANE_LEFT, LANE_RIGHT = MAP_LANE_LIMITS[map_choice]
        LANE_WIDTH = (LANE_RIGHT - LANE_LEFT) // 2
        ROAD_LEFT = LANE_LEFT
        ROAD_RIGHT = LANE_RIGHT - CAR_W
        #decide which lane is local vs. remote based on server/client role ───
    if options.get("role") == "server":
        local_lane, remote_lane = 0, 1
    else:
        local_lane, remote_lane = 1, 0


    #initialize player car (car1) and opponent car (car2)
    game_map = GameMap(map_choice)
    bg = ScrollingBG(game_map.background)
    #pick the first available car path if user's choice isn't found
    default_car_path = next(iter(CAR_OPTIONS.values()))
    car1 = Car(lane=local_lane,car_image_path=CAR_OPTIONS.get(car_color_choice, default_car_path))

    if options.get("single_player"):
        car2 = None
    else:
        opp_car_choice = options.get("opponent_car")
        if opp_car_choice not in CAR_OPTIONS:
            #pick any color different from the local player's, or just the first one
            keys = list(CAR_OPTIONS.keys())
            #try to remove the player’s own choice so they’re not the same
            if car_color_choice in keys and len(keys) > 1:
                keys.remove(car_color_choice)
            opp_car_choice = keys[0]
        car2 = Car(lane=remote_lane,car_image_path=CAR_OPTIONS[opp_car_choice])

    #set starting health for cars
    car1.health = starting_health
    if car2:
        car2.health = starting_health

    #create obstacles based on difficulty
    obstacles = []
    base_count = 5
    total_obstacles = int(base_count * obstacle_multiplier)
    #avoid overlapping obstacles as much as possible by re-rolling positions if needed
    for i in range(total_obstacles):
        lane_choice = random.choice([0, 1])
        #choose a random obstacle image index (for consistency across players)
        img_idx = random.randrange(len(game_map.obstacle_images))
        obs_img = game_map.obstacle_images[img_idx]
        new_obs = Obstacle(obs_img, lane=lane_choice)
        #simple check to avoid vertical overlap in same lane
        retry = 0
        while retry < 5:
            overlap = False
            for obs in obstacles:
                if obs.rect.y - new_obs.rect.y < OBST_H and obs.rect.y - new_obs.rect.y > -OBST_H and obs.rect.x != new_obs.rect.x:
                    if lane_choice == getattr(obs, "lane", lane_choice):
                        overlap = True
                        break
            if overlap:
                new_obs.rect.y = random.randint(-SCREEN_HEIGHT, -50)
                retry += 1
            else:
                break
        new_obs.lane = lane_choice
        obstacles.append(new_obs)
    #prepare networking (if multiplayer)
    peer_socket = None
    send_thread = recv_thread = None
    running_network = False
    network_role = options.get("role") if not options.get("single_player") else None
    events_queue = []  # reset events queue for this game
    if options.get("role") in ["server", "client"] and "opponent_ip" in options:
        #establish peer-to-peer connection using udp for real-time sync
        try:
            opponent_ip = options["opponent_ip"]
            opponent_port = options.get("opponent_port", 12345)
            if options["role"] == "server":
                #as server (host), bind a udp socket on port+1 and send to opponent's port
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(("", opponent_port + 1))
                server_sock.connect((opponent_ip, opponent_port))
                server_sock.settimeout(0.1)
                peer_socket = server_sock
            else:
                #as client, bind udp socket on opponent_port and send to server's port+1
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                client_sock.bind(("", opponent_port))
                client_sock.connect((opponent_ip, opponent_port + 1))
                client_sock.settimeout(0.1)
                peer_socket = client_sock
            #start network threads for real-time sync
            running_network = True
            send_thread = threading.Thread(target=p2p_send_thread, args=(peer_socket, car1), daemon=True)
            recv_thread = threading.Thread(target=p2p_receive_thread, args=(peer_socket, car2, game_map), daemon=True)
            send_thread.start()
            recv_thread.start()
        except Exception as e:
            print(f"P2P connection error: {e}")
            running_network = False
    elif "server_ip" in options and options["server_ip"]:
        #fallback: perform legacy handshake via server if direct details not available
        opp_param = options.get("opponent") if options.get("role") == "client" else None
        conn_details = connect_to_server(options.get("username", ""), options["server_ip"], opp_param)
        if conn_details.get("success"):
            try:
                peer_socket = establish_p2p_connection(conn_details)
                if peer_socket:
                    #use tcp socket from fallback
                    peer_socket.settimeout(0.1)
                    running_network = True
                    send_thread = threading.Thread(target=p2p_send_thread, args=(peer_socket, car1), daemon=True)
                    recv_thread = threading.Thread(target=p2p_receive_thread, args=(peer_socket, car2, game_map), daemon=True)
                    send_thread.start()
                    recv_thread.start()
            except Exception as e:
                print(f"P2P connection error: {e}")
                running_network = False

    #if this side is host, prepare to send initial obstacle positions to client
    if network_role == "server":
        #populate events_queue with initial obstacle info (index, x, y, image index) for sync
        for idx, obs in enumerate(obstacles):
            #find which obstacle image index corresponds (by matching surface in list)
            img_index = 0
            for j, img in enumerate(game_map.obstacle_images):
                #compare by size/filename assumption or fallback to first if not found
                if img.get_size() == obs.image.get_size():
                    img_index = j
                    break
            events_queue.append({"index": idx, "x": obs.rect.x, "y": obs.rect.y, "img_index": img_index})

        #draw a single frame and pause 50 ms
    bg.draw(screen, speed=0)
    car1.draw(screen)
    if car2:
        car2.draw(screen)
    for obs in obstacles:
        if obs.rect.y < SCREEN_HEIGHT:
            obs.draw(screen)
    pygame.display.flip()
    pygame.time.delay(50)   # 0.05 s pause

    #countdown before the race starts
    countdown_sound.play()
    pygame.time.delay(4000)           # wait for 4 s countdown audio
    pygame.mixer.music.play(-1)      # now start background music
    start_time = time.time()         # kick off the race timer
    total_time = 30  # race duration in seconds
    running = True

    #main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False  # Window closed
        #continuous movement based on key state
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            car1.move(-7)
        elif keys[pygame.K_RIGHT]:
            car1.move(7)

        #move obstacles and handle recycling and collisions
        for idx, obstacle in enumerate(obstacles):
            obstacle.move(5)  # move obstacle down
            if obstacle.rect.y > SCREEN_HEIGHT:
                #if obstacle goes off screen bottom, recycle it to top with new position
                if not options.get("single_player") and network_role != "server":
                    #in client mode, skip local respawn – wait for host sync
                    continue
                #compute new random lane and position for respawn
                lane_choice = random.choice([0, 1])
                if lane_choice == 0:
                    lane_min = LANE_LEFT
                    lane_max = LANE_LEFT + LANE_WIDTH - obstacle.rect.width
                else:
                    lane_min = LANE_LEFT + LANE_WIDTH
                    lane_max = LANE_RIGHT - obstacle.rect.width
                obstacle.rect.x = random.randint(lane_min, lane_max)
                obstacle.rect.y = random.randint(-SCREEN_HEIGHT, -50)
                #randomly choose a new obstacle image from current map set
                new_img_idx = random.randrange(len(game_map.obstacle_images))
                obstacle.image = game_map.obstacle_images[new_img_idx].copy()
                obstacle.lane = lane_choice
                #if host, queue this update event to send to client
                if network_role == "server":
                    events_queue.append({"index": idx, "x": obstacle.rect.x, "y": obstacle.rect.y, "img_index": new_img_idx})
            #collision detection for player car (car1)
            if obstacle.rect.colliderect(car1.hitbox):
                car1.health -= 1
                collision_sound.play()
                #add an explosion effect centered on the player's car
                explosion_x = car1.rect.centerx - explosion_image.get_width() // 2
                explosion_y = car1.rect.centery - explosion_image.get_height() // 2
                explosion_effects.append({"x": explosion_x, "y": explosion_y, "timer": 10})
                #remove or reset the obstacle that was hit
                if not options.get("single_player"):
                    if network_role == "server":
                        #host: reposition obstacle (like spawning a new one) and sync to client
                        lane_choice = random.choice([0, 1])
                        if lane_choice == 0:
                            lane_min = LANE_LEFT
                            lane_max = LANE_LEFT + LANE_WIDTH - obstacle.rect.width
                        else:
                            lane_min = LANE_LEFT + LANE_WIDTH
                            lane_max = LANE_RIGHT - obstacle.rect.width
                        obstacle.rect.x = random.randint(lane_min, lane_max)
                        obstacle.rect.y = random.randint(-SCREEN_HEIGHT, -50)
                        new_img_idx = random.randrange(len(game_map.obstacle_images))
                        obstacle.image = game_map.obstacle_images[new_img_idx].copy()
                        obstacle.lane = lane_choice
                        #queue sync event for this collision reset
                        events_queue.append({"index": idx, "x": obstacle.rect.x, "y": obstacle.rect.y, "img_index": new_img_idx})
                    else:
                        #client: push obstacle out of view (host will handle actual reset)
                        obstacle.rect.y = SCREEN_HEIGHT + 100
                else:
                    #single-player: respawn obstacle at new random position
                    lane_choice = random.choice([0, 1])
                    if lane_choice == 0:
                        lane_min = LANE_LEFT
                        lane_max = LANE_LEFT + LANE_WIDTH - obstacle.rect.width
                    else:
                        lane_min = LANE_LEFT + LANE_WIDTH
                        lane_max = LANE_RIGHT - obstacle.rect.width
                    obstacle.rect.x = random.randint(lane_min, lane_max)
                    obstacle.rect.y = random.randint(-SCREEN_HEIGHT, -50)
                    obstacle.image = random.choice(game_map.obstacle_images).copy()
                    obstacle.lane = lane_choice
            #collision detection for opponent car (car2) - only handle in single-player or local context
            if car2 and obstacle.rect.colliderect(car2.hitbox):
                if options.get("single_player"):
                    #in single-player (if we had ai), reduce opponent health
                    car2.health -= 1
                #multiplayer remote car collisions are handled by that player's instance)
        #render background, cars, and obstacles
        bg.draw(screen, speed=5)
        #draw road boundary lines (for visual reference)
        pygame.draw.rect(screen, (200, 200, 200), (ROAD_LEFT - 4, 0, 4, SCREEN_HEIGHT))
        pygame.draw.rect(screen, (200, 200, 200), (ROAD_RIGHT + CAR_W, 0, 4, SCREEN_HEIGHT))
        car1.draw(screen)
        if car2:
            car2.draw(screen)
        for obstacle in obstacles:
            #only draw obstacles that are on screen
            if obstacle.rect.y < SCREEN_HEIGHT:
                obstacle.draw(screen)
        #draw explosion effects on top
        for effect in explosion_effects:
            if effect["timer"] > 0:
                screen.blit(explosion_image, (effect["x"], effect["y"]))
                effect["timer"] -= 1
        explosion_effects = [eff for eff in explosion_effects if eff["timer"] > 0]
        #hud: health & timer
        health_text = font.render(f"Health: {car1.health}", True, WHITE)
        time_left = max(0, int(total_time - (time.time() - start_time)))
        time_text = font.render(f"Time: {time_left}", True, WHITE)
        screen.blit(health_text, (10, 10))
        screen.blit(time_text, (10, 40))
        pygame.display.flip()
        clock.tick(FPS)
        #check for race end conditions
        if car1.health <= 0 or (car2 and car2.health <= 0) or time.time() - start_time >= total_time:
            running = False
    if options.get("single_player"):
        #single‑player: loss if health hit zero; otherwise time ran out → win
        img_path = YOU_LOST_IMAGE_PATH if car1.health <= 0 else YOU_WON_IMAGE_PATH

    elif car2:
        #multiplayer: win, lose, or tie → game over
        if car1.health > car2.health:
            img_path = YOU_WON_IMAGE_PATH
        elif car1.health < car2.health:
            img_path = YOU_LOST_IMAGE_PATH
        else:
            img_path = GAME_END_IMAGE_PATH

    else:
        #fallback, shouldn’t happen)
        img_path = GAME_END_IMAGE_PATH

    #load and display the selected end‑screen for 2 seconds
    try:
        end_img = pygame.image.load(img_path).convert()
        end_img = pygame.transform.scale(end_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(end_img, (0, 0))
        pygame.display.flip()
        pygame.time.delay(2000)
    except Exception as e:
        print(f"Error showing end‑screen ({img_path}): {e}")
    #

    #clean up networking threads and socket after the race
    if peer_socket:
        running_network = False
        if send_thread: send_thread.join(timeout=1.0)
        if recv_thread: recv_thread.join(timeout=1.0)
        try:
            peer_socket.close()
        except Exception:
            pass
    pygame.quit()

    #determine race result (if multiplayer)
    if car2:
        local_user = options.get("username", "")
        opp_user = options.get("opponent", "")
        if car1.health > (car2.health if car2 else 0):
            winner = local_user
        elif car2 and car1.health < car2.health:
            winner = opp_user
        else:
            winner = "DRAW"
        #send result to server to update stats (if connected)
        if options.get("network_handler") and getattr(options["network_handler"], "socket", None):
            try:
                options["network_handler"].socket.send(f"RESULT:{local_user}:{opp_user}:{winner}\n".encode())
            except Exception as e:
                print(f"Error sending result to server: {e}")


#challenge dialog (incoming challenge popup)

class ChallengeDialog(QDialog):
    def __init__(self, challenger_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Challenge Request")
        self.setModal(True)
        self.setup_ui(challenger_name)

    def setup_ui(self, challenger_name):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{challenger_name} wants to race with you!"))
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        button_box.accepted.connect(self.accept)   # fires on "OK"
        button_box.rejected.connect(self.reject)   # fires on "Cancel"
        layout.addWidget(button_box)
        self.setLayout(layout)


#network handler (client-side server communication)

class NetworkHandler(QObject):
    challenge_received = pyqtSignal(str)   #emitted when a challenge request arrives
    match_started = pyqtSignal(dict)       #emitted when a match start is triggered
    challenge_sent    = pyqtSignal()
    challenge_rejected   = pyqtSignal()   
    opponent_unavailable = pyqtSignal()  
 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.socket = None
        self.running = False
        self.receive_thread = None

    def connect_to_server(self, server_ip, username, password):
        """Connect to the main server and log in, starting the listener thread."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2)
            self.socket.connect((server_ip, 8005))
            self.socket.settimeout(None)
            self.socket.send(f"LOGIN:{username}:{password}".encode())
            response = self.socket.recv(1024).decode().strip()
            if response == "LOGIN_SUCCESS":
                #maintain connection and start listening thread for async messages
                self.running = True
                self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
                self.receive_thread.start()
                return True
            else:
                #login failed or unexpected response
                return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    #send_challenge function, simple overview
    def send_challenge(self, challenger, challenged, car_choice):
        """Send a challenge request that also carries the letter of my car."""
        try:
        #adds the 4th field
            self.socket.send(f"CHALLENGE:{challenger}:{challenged}:{car_choice}".encode())
            return True
        except Exception as e:
            print(f"Challenge error: {e}")
            return False

    def respond_to_challenge(self, username, response, car_choice=None):
        try:
            msg = f"CHALLENGE_RESPONSE:{username}:{response}"
            if car_choice:                
                msg += f":{car_choice}"  
            self.socket.send(msg.encode())
            return True
        except Exception as e:
            print(f"Challenge response error: {e}")
            return False

    def update_status(self, status):
        """Optional: send a status update (not used extensively)."""
        try:
            self.socket.send(f"STATUS:{status}".encode())
            response = self.socket.recv(1024).decode().strip()
            return response == "STATUS_UPDATED"
        except Exception:
            return False

    def receive_loop(self):
        """Background thread to handle incoming server messages (challenges, match start, etc.)."""
        while self.running:
            try:
                data = self.socket.recv(1024).decode().strip()
                if not data:
                    break  #connection closed
                elif data == "CHALLENGE_SENT":
                   self.challenge_sent.emit()
                   continue
                if data.startswith("CHALLENGE_REQUEST:"):
                    #incoming challenge from another player
                    challenger = data.split(":")[1]
                    self.challenge_received.emit(challenger)
                elif data.startswith("MATCH_START:"):
                    #match starting, format: match_start:matchid:role:opp_ip:opp_port:opp_car
                    parts = data.split(":")
                    if len(parts) >= 7 and parts[2] in ("server","client"):
                        match_id = parts[1]; role = parts[2]; opp_ip = parts[3]; opp_port =parts[4] ; opp_car = parts[5];opp_name = parts[6]
                        self.match_started.emit({
                            "match_id": match_id,
                            "role": role,
                            "opp_ip": opp_ip,
                            "opponent_port": int(opp_port),
                            "opp_car": opp_car,
                            "opponent_name": opp_name
                        })
                    elif len(parts) >= 3:
                        match_id = parts[1]; role = parts[2]
                        self.match_started.emit({"match_id": match_id, "role": role})
                elif data == "CHALLENGE_REJECTED":
                    self.challenge_rejected.emit()       
                elif data == "OPPONENT_NOT_AVAILABLE":
                    self.opponent_unavailable.emit()     
                #ignore other messages like result_updated or status acknowledgments
            except Exception as e:
                break
        #mark as disconnected if loop exits
        self.running = False
        if self.socket:
            self.socket.close()

    def cleanup(self):
        """Clean up the network connection (call on app exit)."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass


#main window (game setup ui)

class MainWindow(QWidget):
    def on_challenge_rejected(self):
        QMessageBox.information(self, "Challenge Declined",
                            "Your challenge was rejected by the opponent.")

    def on_opponent_unavailable(self):
        QMessageBox.warning(self, "Opponent Unavailable",
                        "The selected opponent is not available.")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multiplayer Racing Game Setup")
        self.setGeometry(100, 100, 900, 500)
        self.network_handler = NetworkHandler(self)
        #connect signals from network handler to ui handlers
        self.network_handler.challenge_received.connect(self.handle_challenge)
        self.network_handler.match_started.connect(self.handle_match_start)
        self.network_handler.challenge_rejected.connect(self.on_challenge_rejected)
        self.network_handler.opponent_unavailable.connect(self.on_opponent_unavailable)

        #show login dialog at startup
        login_dialog = LoginDialog(self)
        if login_dialog.exec_() == QDialog.Accepted:
            self.username = login_dialog.username
            self.is_guest = login_dialog.is_guest
            if not self.is_guest:
                server_ip = login_dialog.server_ip_edit.text().strip() or "127.0.0.1"
                #connect to server for persistent communication
                if not self.network_handler.connect_to_server(server_ip, self.username, login_dialog.password):
                    QMessageBox.critical(self, "Connection Error",
                                         "Failed to connect to server. Playing as guest.")
                    self.is_guest = True
                #set the server ip field in the options tab for reference
                try:
                    self.server_ip_edit.setText(server_ip)
                except AttributeError:
                    pass
        else:
            #login cancelled: use guest mode by default
            self.username = f"Guest_{random.randint(1000, 9999)}"
            self.is_guest = True
        #build the main ui tabs (game options)
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.options_tab = QWidget()
        self.tabs.addTab(self.options_tab, "Game Options")
        self.setup_options_tab()
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        #periodically refresh opponents list (every 5 seconds)
        self.opponent_timer = QTimer()
        self.opponent_timer.timeout.connect(self.fetch_opponents)
        self.opponent_timer.start(5000)
        #display the current username on the gui
        self.username_edit.setText(self.username)
        self.username_edit.setReadOnly(True)

    def setup_options_tab(self):
        #1)name the tab so the stylesheet only affects this page
        self.options_tab.setObjectName("OptionsTab")
        #2)apply your custom background (and lightly tint the groupbox)
        #absolute path to your “no‑word” image
        opts = r"resources/gui background/setup.png"
        opts = opts.replace("\\", "/")

        self.options_tab.setObjectName("OptionsTab")
        self.options_tab.setStyleSheet(f"""
        QWidget#OptionsTab {{
            border-image: url("{opts}") 0 0 0 0 stretch stretch;
        }}
        /* make all labels bold + white */
        QWidget#OptionsTab QLabel {{
            color: white;
            font-weight: bold;
        }}
        /* remove the opaque “card” behind the inputs */
        QGroupBox {{
            background: transparent;
            border: none;
        }}
    """)




        #now your normal layout code follows unchanged
        outer = QVBoxLayout(self.options_tab)
        outer.setContentsMargins(15,15,15,15)
        outer.setSpacing(20)

        #game settings group
        settings_gb = QGroupBox("Game Settings")
        settings_gb.setAlignment(Qt.AlignCenter)
        settings_layout = QGridLayout()
        settings_layout.setHorizontalSpacing(15)
        settings_layout.setVerticalSpacing(12)

        #row 0
        settings_layout.addWidget(QLabel("Server IP:"),    0,0)
        self.server_ip_edit = QLineEdit()
        self.server_ip_edit.setPlaceholderText("e.g. 127.0.0.1")
        settings_layout.addWidget(self.server_ip_edit,     0,1)

        settings_layout.addWidget(QLabel("Username:"),     0,2)
        self.username_edit = QLineEdit(self.username)
        self.username_edit.setReadOnly(True)
        settings_layout.addWidget(self.username_edit,      0,3)

        #row 1
        settings_layout.addWidget(QLabel("Map:"),          1,0)
        self.map_combo = QComboBox()
        custom_map_names = ["Candy", "Beach", "Halloween", "Urban", "Christmas"]
        self.map_combo.clear()
        self.map_combo.addItems(custom_map_names)
        settings_layout.addWidget(self.map_combo,          1,1)

        settings_layout.addWidget(QLabel("Difficulty:"),   1,2)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.clear()
        self.difficulty_combo.addItems(list(DIFFICULTY_SETTINGS.keys()))
        settings_layout.addWidget(self.difficulty_combo,   1,3)

        #row 2
        settings_layout.addWidget(QLabel("Car Option:"),   2,0)
        self.car_combo = QComboBox()
        custom_car_names = ["Red","Pink","Blue","Green"]
        self.car_combo.clear()
        self.car_combo.addItems(custom_car_names)
        settings_layout.addWidget(self.car_combo,          2,1)

        settings_layout.addWidget(QLabel("Opponent:"),     2,2)
        self.opponent_combo = QComboBox()
        self.opponent_combo.addItem("Fetching…")
        settings_layout.addWidget(self.opponent_combo,     2,3)

        settings_gb.setLayout(settings_layout)
        outer.addWidget(settings_gb)

        #action buttons 
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.addStretch()

        self.challenge_button = QPushButton("Challenge Opponent")
        self.challenge_button.setFixedHeight(38)
        self.challenge_button.setCursor(Qt.PointingHandCursor)
        self.challenge_button.clicked.connect(self.challenge_opponent)
        btn_layout.addWidget(self.challenge_button)

        self.singleplayer_button = QPushButton("Start Single Player")
        self.singleplayer_button.setFixedHeight(38)
        self.singleplayer_button.setCursor(Qt.PointingHandCursor)
        self.singleplayer_button.clicked.connect(self.start_singleplayer)
        btn_layout.addWidget(self.singleplayer_button)

        btn_layout.addStretch()
        outer.addLayout(btn_layout)

    def fetch_opponents(self):
        """Refresh the list of online opponents from the server."""
        if self.is_guest:
            #guests cannot list opponents
            self.opponent_combo.clear()
            self.opponent_combo.addItem("Guest mode - no opponents available")
            return
        server_ip = self.server_ip_edit.text().strip() or "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((server_ip, 8005))
            s.send("G".encode())  # Request list of players
            data = s.recv(4096).decode().strip()
            s.close()
            self.opponent_combo.clear()
            if data == "No active players":
                self.opponent_combo.addItem("No available opponents")
            else:
                #parse json or comma-separated list of players
                try:
                    players_info = json.loads(data)
                except json.JSONDecodeError:
                    opponents_list = data.split(",") if data else []
                    if self.username in opponents_list:
                        opponents_list.remove(self.username)
                    players_info = [{"username": u, "display_name": u} for u in opponents_list]
                added = False
                for player in players_info:
                    username = player.get("username", "")
                    if not username or username == self.username:
                        continue
                    display_name = player.get("display_name", username)
                    wins = player.get("wins", 0)
                    games = player.get("games", 0)
                    car = player.get("car", "N/A")
                    last_login = player.get("last_login", "")
                    last_date = last_login.split(" ")[0] if last_login else "N/A"
                    #format each entry with stats for clarity
                    item_text = f"{display_name} ({username}) - Wins:{wins} - Games:{games} - Car:{car} - Last:{last_date}"
                    self.opponent_combo.addItem(item_text)
                    added = True
                if not added:
                    self.opponent_combo.addItem("No available opponents")
        except socket.timeout:
            self.opponent_combo.clear()
            self.opponent_combo.addItem("Connection timed out")
        except ConnectionRefusedError:
            self.opponent_combo.clear()
            self.opponent_combo.addItem("Connection refused")
        except Exception as e:
            self.opponent_combo.clear()
            self.opponent_combo.addItem("Error fetching opponents")

    def challenge_opponent(self):
        """Send a challenge to the selected opponent from the dropdown."""
        opponent_item = self.opponent_combo.currentText()
        if opponent_item in [
            "No available opponents", "Error fetching opponents", "Fetching opponents...",
            "Guest mode - no opponents available", "Connection timed out", "Connection refused"
        ]:
            QMessageBox.warning(self, "No Opponent", "Please select a valid opponent to challenge.")
            return
        #extract the username from the combo box item text (format: name (username) - ...)
        opponent_username = opponent_item
        if "(" in opponent_item and ")" in opponent_item:
            opponent_username = opponent_item.split("(")[1].split(")")[0]
            car_letter = self.car_combo.currentText()

        #send challenge via network handler
        if self.network_handler.send_challenge(
                self.username,
                opponent_username,
            car_letter          #new third argument
):
            self.current_opponent = opponent_username
            QMessageBox.information(
        self, "Challenge Sent",
        f"Challenge sent to {opponent_username}. Waiting for response…"
    )
        else:
            QMessageBox.warning(
            self, "Challenge Failed",
             "Failed to send challenge. Please try again."
    )
    def handle_challenge(self, challenger_name):
        """Handle an incoming challenge request from another player."""
        dialog = ChallengeDialog(challenger_name, self)
        if dialog.exec_() == QDialog.Accepted:
            #user accepted the challenge
            self.current_opponent = challenger_name
            self.network_handler.respond_to_challenge(
                self.username,
                "ACCEPT",
                self.car_combo.currentText()     #send my live car letter
)

        else:
            #user rejected the challenge
            self.network_handler.respond_to_challenge(self.username, "REJECT")

    def handle_match_start(self, match_info):
        """Start the game when a match is confirmed by the server."""
        #prepare game options including networking details
        map_text = self.map_combo.currentText()
        map_choice = self.map_combo.currentIndex() + 1
        options = {
            "server_ip": self.server_ip_edit.text().strip() or "",
            "username": self.username,
            "map_choice": map_choice,
            "difficulty": self.difficulty_combo.currentText(),
            "car_color": self.car_combo.currentText(),
            "match_id": match_info.get("match_id", ""),
            "role": match_info.get("role", "")
        }
        options["opponent"] = match_info.get(          "opponent_name",
           getattr(self, "current_opponent", "")        )
        #include opponent connection info if provided
        if "opp_ip" in match_info:
            options["opponent_ip"] = match_info["opp_ip"]
        if "opponent_port" in match_info or "opp_port" in match_info:
            opp_port_val = match_info.get("opponent_port", match_info.get("opp_port", 12345))
            options["opponent_port"] = int(opp_port_val)
        if "opp_car" in match_info:
            options["opponent_car"] = match_info["opp_car"]
        #pass the network handler for result reporting
        options["network_handler"] = self.network_handler
        self.start_game(options)

    def start_singleplayer(self):
        """Launch a single-player race without any network opponent."""
        #build options for single-player game from current selections
        map_text = self.map_combo.currentText()            # e.g. "Map 1"
        map_choice = self.map_combo.currentIndex() + 1            # -> 1
        options = {
            "map_choice": map_choice,
            "difficulty": self.difficulty_combo.currentText(),
            "car_color": self.car_combo.currentText(),
            "username": self.username,
            "single_player": True
        }
        run_game(options)

    def start_game(self, options):
        """Launch the game loop with the specified options."""
        run_game(options)
        #after the game, the opponent list will refresh (stats may update if online)

    def closeEvent(self, event):
        """Handle window closing: clean up network connection."""
        self.network_handler.cleanup()
        event.accept()
    def on_challenge_sent(self):
        QMessageBox.information(
            self,
            "Challenge Sent",
            f"Challenge sent to {self.current_opponent}. Waiting for response…"
        )


#main application entry point

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
