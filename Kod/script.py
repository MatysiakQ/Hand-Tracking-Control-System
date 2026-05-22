import os
import cv2
import mediapipe as mp
import numpy as np
import time
import math

import board
import busio
from adafruit_pca9685 import PCA9685

DEBUG = True

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["GLOG_minloglevel"] = "2"

FINGER_ALPHA = 0.6
FINGER_DEADBAND = 1.5
WRIST_ALPHA = 0.35
WRIST_DEADBAND = 0.03
RETURN_ALPHA = 0.2
TIMEOUT_SECONDS = 1.5
TIME_TO_SLEEP = 2.0
ACTIVATION_TIME = 3.0
MIN_HAND_SIZE = 0.15

mp_hands = mp.solutions.hands

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c)
    pca.frequency = 50
except Exception as e:
    if DEBUG:
        print(f"Brak PCA9685: {e}")


    class DummyPCA:
        class Channel:
            duty_cycle = 0

        channels = [Channel() for _ in range(16)]


    pca = DummyPCA()

SERVO_CHANNELS = {"Thumb": 1, "Index": 4, "Middle": 3, "Ring": 2, "Pinky": 0}
# SERVO_CHANNELS = {"Thumb": 1, "Index": 4, "Middle": 3, "Ring": 2, "Pinky": 0, "Wrist": 5}
LAST_WRITTEN_DUTY = {name: -1 for name in SERVO_CHANNELS.keys()}

SERVO_MAP = {
    "Thumb": {"open_pwm": 10, "close_pwm": 470, "input_min": 110, "input_max": 177},
    "Index": {"open_pwm": 20, "close_pwm": 420, "input_min": 15, "input_max": 177},
    "Middle": {"open_pwm": 500, "close_pwm": 150, "input_min": 16, "input_max": 179},
    "Ring": {"open_pwm": 20, "close_pwm": 420, "input_min": 18, "input_max": 176},
    "Pinky": {"open_pwm": 20, "close_pwm": 350, "input_min": 33, "input_max": 171},
    # "Wrist": {"open_pwm": 110, "close_pwm": 580, "input_min": 0.10, "input_max": 0.85}
}
ORDER = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
# ORDER = ["Thumb", "Index", "Middle", "Ring", "Pinky", "Wrist"]


def set_servo_pwm(name, pwm, force=False):
    if name not in SERVO_CHANNELS:
        return
    channel = SERVO_CHANNELS[name]
    duty = int(np.interp(pwm, [0, 600], [1500, 8500]))

    if duty != LAST_WRITTEN_DUTY[name] or force:
        try:
            pca.channels[channel].duty_cycle = duty
            LAST_WRITTEN_DUTY[name] = duty
            if DEBUG:
                print(f"[SERWO] {name}: {pwm}")
        except OSError:
            pass


def apply_servo_positions(values, force=False):
    for name, val in zip(ORDER, values):
        set_servo_pwm(name, val, force)


def release_all_servos():
    if DEBUG:
        return
    for name, channel in SERVO_CHANNELS.items():
        try:
            pca.channels[channel].duty_cycle = 0
            LAST_WRITTEN_DUTY[name] = -1
        except OSError:
            pass


def get_fist_pwm():
    return [SERVO_MAP[name]["close_pwm"] for name in ORDER]


def get_open_pwm():
    return [SERVO_MAP[name]["open_pwm"] for name in ORDER]


def run_calibration_wave():
    if DEBUG:
        print("Animacja FALI...")

    current_vals = get_open_pwm()
    apply_servo_positions(current_vals, force=True)
    time.sleep(0.4)

    for finger in ["Pinky", "Ring", "Middle", "Index", "Thumb"]:
        idx = ORDER.index(finger)
        current_vals[idx] = SERVO_MAP[finger]["close_pwm"]
        apply_servo_positions(current_vals)
        time.sleep(0.15)

    time.sleep(0.3)
    apply_servo_positions(get_open_pwm(), force=True)
    time.sleep(0.5)


class AngleSmoother:
    def __init__(self, alpha=0.4, deadband=2.0):
        self.alpha, self.dead = float(alpha), float(deadband)
        self.ema, self.last_target = None, None

    def update(self, new_val):
        new_val = float(new_val)
        if self.ema is None:
            self.ema = self.last_target = new_val
            return new_val

        if abs(new_val - self.last_target) > self.dead:
            self.last_target = new_val

        self.ema = (1.0 - self.alpha) * self.ema + self.alpha * self.last_target
        return self.ema


class ReturnSmoother:
    def __init__(self, alpha=0.05):
        self.alpha = float(alpha)
        self.current = {}

    def init_value(self, name, default_val):
        self.current[name] = float(default_val)

    def update_toward_default(self, name, default_val):
        self.current[name] = (1.0 - self.alpha) * self.current[name] + self.alpha * float(default_val)
        return self.current[name]

    def set_value(self, name, val):
        self.current[name] = float(val)


FINGERS_INDEXES = {
    "Thumb": (1, 2, 4),
    "Index": (5, 6, 8),
    "Middle": (9, 10, 12),
    "Ring": (13, 14, 16),
    "Pinky": (17, 18, 20)
}


def get_wrist_pronation_3d(lm, is_right_hand=True):
    ux, uy, uz = lm[5].x - lm[0].x, lm[5].y - lm[0].y, lm[5].z - lm[0].z
    vx, vy, vz = lm[17].x - lm[0].x, lm[17].y - lm[0].y, lm[17].z - lm[0].z
    nx, nz = uy * vz - uz * vy, uz * vy - uy * vx
    if not is_right_hand:
        nx, nz = -nx, -nz
    return float(np.clip(np.arctan2(nx, -nz) / np.pi, -1.0, 1.0))


def get_hand_rotation_angle(lm):
    return np.degrees(np.arctan2(lm[9].x - lm[0].x, -(lm[9].y - lm[0].y)))


def normalize_landmarks(lm, angle):
    rad = np.radians(angle)
    cos, sin = np.cos(-rad), np.sin(-rad)
    rot = np.array([[cos, -sin], [sin, cos]])
    origin = np.array([lm[0].x, lm[0].y])
    return [rot @ (np.array([p.x, p.y]) - origin) for p in lm]


def calc_angle(norm, p1, p2, p3):
    ba = norm[p1] - norm[p2]
    bc = norm[p3] - norm[p2]
    norm_ba, norm_bc = np.linalg.norm(ba), np.linalg.norm(bc)

    if norm_ba == 0 or norm_bc == 0:
        return 0.0

    return np.degrees(np.arccos(np.clip(np.dot(ba, bc) / (norm_ba * norm_bc), -1.0, 1.0)))


def map_smart(value, cfg):
    val = max(cfg["input_min"], min(value, cfg["input_max"]))
    norm = (val - cfg["input_min"]) / (cfg["input_max"] - cfg["input_min"])
    return int(cfg["close_pwm"] + norm * (cfg["open_pwm"] - cfg["close_pwm"]))


if DEBUG:
    print("Start - DEBUG")

cam_index = 0
cap = cv2.VideoCapture(cam_index)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=0)

smoothers = {
    name: AngleSmoother(FINGER_ALPHA, FINGER_DEADBAND)
    for name in SERVO_MAP
}

returner = ReturnSmoother(RETURN_ALPHA)

for n, v in zip(ORDER, get_fist_pwm()):
    returner.init_value(n, v)

MODE = "IDLE"
activation_start_time = 0.0
last_seen_time = time.time()
idle_timer_start = time.time()
servos_sleeping = False
failed_frames = 0

try:
    while True:
        try:
            ok, frame = cap.read()
            if not ok:
                failed_frames += 1
                if failed_frames > 30:
                    cap.release()
                    cam_index = (cam_index + 1) % 3
                    cap = cv2.VideoCapture(cam_index)
                    failed_frames = 0
                continue

            failed_frames = 0
            res = hands.process(cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB))

            if res.multi_hand_landmarks:
                handedness_label = res.multi_handedness[0].classification[0].label
                is_right = (handedness_label == "Right")
                lm = res.multi_hand_landmarks[0].landmark

                hand_size = math.hypot(lm[9].x - lm[0].x, lm[9].y - lm[0].y)
                if hand_size < MIN_HAND_SIZE:
                    is_right = False

                if MODE == "IDLE":
                    if is_right:
                        if servos_sleeping:
                            servos_sleeping = False

                        if activation_start_time == 0.0:
                            activation_start_time = time.time()
                        elif time.time() - activation_start_time >= ACTIVATION_TIME:
                            run_calibration_wave()
                            for _ in range(15):
                                cap.grab()

                            MODE = "TRACKING"
                            last_seen_time = time.time()
                            activation_start_time = 0.0

                            for name, val in zip(ORDER, get_open_pwm()):
                                returner.set_value(name, val)
                            continue
                    else:
                        if activation_start_time > 0.0:
                            activation_start_time = 0.0

                    if not servos_sleeping:
                        output = [int(returner.update_toward_default(name, val)) for name, val in
                                  zip(ORDER, get_fist_pwm())]
                        apply_servo_positions(output)

                        if not DEBUG and (time.time() - idle_timer_start > TIME_TO_SLEEP):
                            release_all_servos()
                            servos_sleeping = True

                elif MODE == "TRACKING":
                    if is_right:
                        last_seen_time = time.time()
                        output = []

                        # wrist_pronation = get_wrist_pronation_3d(lm, is_right_hand=True)
                        # if DEBUG:
                        #     print(f"[RAW] Nadgarstek: {wrist_pronation:.3f}")

                        # wrist_val = map_smart(smoothers["Wrist"].update(wrist_pronation), SERVO_MAP["Wrist"])
                        # wrist_val = 355 # Stała wartość zamiast śledzenia
                        rot = get_hand_rotation_angle(lm)
                        norm_lm = normalize_landmarks(lm, rot)

                        for name in ["Thumb", "Index", "Middle", "Ring", "Pinky"]:
                            p1, p2, p3 = FINGERS_INDEXES[name]
                            angle = calc_angle(norm_lm, p1, p2, p3)
                            val = map_smart(smoothers[name].update(angle), SERVO_MAP[name])
                            output.append(val)
                            returner.set_value(name, val)

                        apply_servo_positions(output)
                    else:
                        output = [int(returner.current[n]) for n in ORDER]
                        apply_servo_positions(output)

            else:
                if MODE == "IDLE":
                    activation_start_time = 0.0
                    if not servos_sleeping:
                        output = [int(returner.update_toward_default(name, val)) for name, val in
                                  zip(ORDER, get_fist_pwm())]
                        apply_servo_positions(output)
                        if not DEBUG and (time.time() - idle_timer_start > TIME_TO_SLEEP):
                            release_all_servos()
                            servos_sleeping = True

                elif MODE == "TRACKING":
                    if time.time() - last_seen_time > TIMEOUT_SECONDS:
                        MODE = "IDLE"
                        idle_timer_start = time.time()
                        for name in smoothers:
                            smoothers[name].ema = None
                    else:
                        output = [int(returner.current[n]) for n in ORDER]
                        apply_servo_positions(output)

            time.sleep(0.01)

        except Exception as e:
            if DEBUG:
                print(f"[Błąd Pętli] {e}")
            time.sleep(0.05)
            continue

except KeyboardInterrupt:
    pass
finally:
    release_all_servos()
    if 'cap' in locals() and cap is not None:
        cap.release()