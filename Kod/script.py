import os
import math
import collections
import cv2
import mediapipe as mp
import numpy as np

# --- USTAWIENIA GLOBALNE ---
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# --- ZMIENNE STANU (GLOBALNE) ---
# Te zmienne utrzymają stan (kamerę, historię wygładzania) między wywołaniami funkcji z LabVIEW
global_cap = None
global_hands = None
global_smoothers = {}
global_smooth_yaw = None
global_window_name = "Hand Tracking - LabVIEW Direct"
show_outlines = True

# --- KONFIGURACJA PALCÓW I GESTÓW ---
FINGERS_LOGIC = {
    "Thumb": (1, 2, 3),
    "Index": (5, 6, 7),
    "Middle": (9, 10, 11),
    "Ring": (13, 14, 15),
    "Pinky": (17, 18, 19),
}

FINGER_LANDMARKS_FOR_BOX = {
    "Thumb": [1, 2, 3, 4],
    "Index": [5, 6, 7, 8],
    "Middle": [9, 10, 11, 12],
    "Ring": [13, 14, 15, 16],
    "Pinky": [17, 18, 19, 20],
}

# Progi
EXTENDED_THRESH = {"Thumb": 170.0, "Index": 160.0, "Middle": 160.0, "Ring": 160.0, "Pinky": 160.0}
BENT_THRESH = {"Thumb": 130.0, "Index": 120.0, "Middle": 120.0, "Ring": 120.0, "Pinky": 120.0}

# Konfiguracja Serw
SERVO_CFG = {
    "Thumb": {"invert": True, "out_min": 500, "out_max": 2500},
    "Index": {"invert": False, "out_min": 500, "out_max": 2500},
    "Middle": {"invert": False, "out_min": 500, "out_max": 2500},
    "Ring": {"invert": False, "out_min": 500, "out_max": 2500},
    "Pinky": {"invert": False, "out_min": 500, "out_max": 2500},
}


# --- KLASY POMOCNICZE ---
class AngleSmoother:
    def __init__(self, window=7, alpha=0.15, deadband=2.0):
        self.hist = collections.deque(maxlen=window)
        self.alpha = float(alpha)
        self.dead = float(deadband)
        self.ema = None
        self.last_out = None

    def _median(self, vals):
        s = sorted(vals)
        n = len(s)
        if n == 0: return 0.0
        if n % 2: return s[n // 2]
        return 0.5 * (s[n // 2 - 1] + s[n // 2])

    def _round05(self, x):
        return round(x * 2.0) / 2.0

    def update(self, x):
        x = float(x)
        self.hist.append(x)
        med = self._median(self.hist)
        if self.ema is None:
            self.ema = med
        else:
            self.ema = (1 - self.alpha) * self.ema + self.alpha * med
        out = self.ema
        if self.last_out is not None and abs(out - self.last_out) < self.dead:
            out = self.last_out
        out = self._round05(out)
        self.last_out = out
        return out


def angle_deg(a, b, c):
    v1 = (a.x - b.x, a.y - b.y, a.z - b.z)
    v2 = (c.x - b.x, c.y - b.y, c.z - b.z)

    def nrm(v): return (v[0] ** 2 + v[1] ** 2 + v[2] ** 2) ** 0.5 + 1e-9

    v1n = (v1[0] / nrm(v1), v1[1] / nrm(v1), v1[2] / nrm(v1))
    v2n = (v2[0] / nrm(v2), v2[1] / nrm(v2), v2[2] / nrm(v2))
    dot = max(-1.0, min(1.0, v1n[0] * v2n[0] + v1n[1] * v2n[1] + v1n[2] * v2n[2]))
    return math.degrees(math.acos(dot))


def recognize_gesture(smoothed_fingers):
    straight = {name: smoothed_fingers[name] >= EXTENDED_THRESH[name] for name in FINGERS_LOGIC}
    bent = {name: smoothed_fingers[name] < BENT_THRESH[name] for name in FINGERS_LOGIC}
    if all(bent.values()): return "PIESC"
    if all(straight.values()): return "OTWARTA DLON"
    if straight["Index"] and straight["Middle"] and bent["Thumb"] and bent["Ring"] and bent["Pinky"]: return "POKOJ (V)"
    if straight["Thumb"] and bent["Index"] and bent["Middle"] and bent["Ring"] and bent["Pinky"]: return "KCIUK W GORE"
    if straight["Index"] and bent["Thumb"] and bent["Middle"] and bent["Ring"] and bent[
        "Pinky"]: return "WSKAZUJESZ (1)"
    return "---"


def map_angle_to_servo(angle_deg_value, in_min=50.0, in_max=170.0, out_min=500.0, out_max=2500.0, invert=False):
    a = max(min(angle_deg_value, in_max), in_min)
    norm = (a - in_min) / (in_max - in_min)
    if invert: norm = 1.0 - norm
    val = out_min + norm * (out_max - out_min)
    return int(round(val))


# --- GŁÓWNA FUNKCJA DLA LABVIEW ---
def process_frame():
    """
    Tę funkcję wywołuj w LabVIEW w pętli.
    Zwraca: NumPy Array [Thumb, Index, Middle, Ring, Pinky] (typ Int32)
    """
    global global_cap, global_hands, global_smoothers, global_smooth_yaw, show_outlines

    # 1. INICJALIZACJA (Lazy Loading - wykonuje się tylko przy pierwszym wywołaniu)
    if global_cap is None:
        global_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        global_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        global_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        global_hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )

        # Inicjalizacja smootherów
        global_smoothers = {name: AngleSmoother(window=7, alpha=0.15, deadband=2.0)
                            for name in FINGERS_LOGIC.keys() if name != "Thumb"}
        global_smoothers["Thumb"] = AngleSmoother(window=7, alpha=0.30, deadband=1.0)
        global_smooth_yaw = AngleSmoother(window=10, alpha=0.25, deadband=1.5)

        cv2.namedWindow(global_window_name, cv2.WINDOW_NORMAL)

    # 2. POBRANIE KLATKI
    ok, frame = global_cap.read()
    if not ok:
        # Jeśli błąd kamery, zwróć domyślne wartości
        return np.array([500, 500, 500, 500, 500], dtype=np.int32)

    frame = cv2.flip(frame, 1)
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = global_hands.process(rgb)

    servo_values = [500, 500, 500, 500, 500]  # Default
    current_gesture = "---"

    # 3. PRZETWARZANIE
    # 3. PRZETWARZANIE
    if res.multi_hand_landmarks:
        lm = res.multi_hand_landmarks[0].landmark

        # Kąty - tu używamy .items(), bo potrzebujemy punktów (a, b, c)
        raw_fingers = {name: angle_deg(lm[a], lm[b], lm[c]) for name, (a, b, c) in FINGERS_LOGIC.items()}

        # POPRAWKA TUTAJ: Iterujemy po kluczach FINGERS_LOGIC, a nie po .items()
        smoothed_fingers = {name: global_smoothers[name].update(raw_fingers[name]) for name in FINGERS_LOGIC}

        # Yaw
        v_yaw_x = lm[9].x - lm[0].x
        v_yaw_y = lm[9].y - lm[0].y
        raw_yaw = math.degrees(math.atan2(v_yaw_y, v_yaw_x))
        smoothed_yaw = global_smooth_yaw.update(raw_yaw)

        current_gesture = recognize_gesture(smoothed_fingers)

        # Mapowanie na serwa
        ordered_keys = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        servo_values = []
        for name in ordered_keys:
            cfg = SERVO_CFG[name]
            val = map_angle_to_servo(smoothed_fingers[name],
                                     out_min=cfg["out_min"],
                                     out_max=cfg["out_max"],
                                     invert=cfg["invert"])
            servo_values.append(val)

        # Rysowanie (uproszczone dla wydajności)
        if show_outlines:
            mp_draw.draw_landmarks(frame, res.multi_hand_landmarks[0], mp.solutions.hands.HAND_CONNECTIONS)
            # Dodanie gestu na ekranie
            cv2.putText(frame, f"GEST: {current_gesture}", (10, 50),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 2)

            # Wizualizacja wartości serw na obrazie
            y_pos = 100
            for i, val in enumerate(servo_values):
                cv2.putText(frame, f"S{i + 1}: {val}", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                y_pos += 30

    else:
        cv2.putText(frame, "BRAK DLONI", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    # 4. WYŚWIETLANIE OKNA (musi być obsługiwane tutaj, aby odświeżać podgląd)
    cv2.imshow(global_window_name, frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        cleanup()
        return np.array([-1, -1, -1, -1, -1], dtype=np.int32)  # Kod wyjścia

    # 5. ZWRACANIE WYNIKU DO LABVIEW
    # LabVIEW Python Node świetnie radzi sobie z numpy arrays
    return np.array(servo_values, dtype=np.int32)


def cleanup():
    """ Funkcja do sprzątania przy zamykaniu LabVIEW """
    global global_cap, global_hands
    if global_cap is not None:
        global_cap.release()
        global_cap = None
    if global_hands is not None:
        global_hands.close()
        global_hands = None
    cv2.destroyAllWindows()
    print("Zwolniono zasoby.")


if __name__ == "__main__":
    # Ten blok służy tylko do testowania kodu bez LabVIEW
    print("Tryb testowy (bez LabVIEW)... Naciśnij 'q' aby wyjść.")
    while True:
        vals = process_frame()
        if vals[0] == -1: break
        # print(vals) # opcjonalnie wypisuj w konsoli