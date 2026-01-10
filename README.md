# 🤖 Smart Robotic Hand Controller
### OpenCV & MediaPipe + LabVIEW + Arduino (LINX)

Projekt zaawansowanego systemu sterowania robotyczną dłonią w czasie rzeczywistym. System wykorzystuje AI do śledzenia dłoni użytkownika, a następnie przesyła dane do LabVIEW, które zarządza fizycznymi serwomechanizmami na Arduino.

---

## 🚀 Główne Funkcje (Features)
* **Śledzenie dłoni (Hand Tracking):** Wykorzystanie biblioteki MediaPipe do detekcji 21 punktów dłoni.
* **Precyzyjne Obliczenia:** Analiza kątów zgięcia 5 palców oraz obrotu nadgarstka (Yaw) z filtrami EMA/Median.
* **Komunikacja UDP:** Szybki przesył danych między Pythonem a LabVIEW (Port 5010).
* **Bezpieczeństwo Sprzętu:** Automatyczna konwersja kątów na bezpieczne wartości Duty Cycle.
* **Odczytywanie gestów** Automatyczne wykrywanie gestów w czasie rzeczywistym.


---

## 🛠️ Stos Technologiczny (Tech Stack)
* **Python 3.x:** OpenCV, MediaPipe (Logika wizyjna).
* **LabVIEW 2025:** Komunikacja UDP, Parsowanie danych, GUI.
* **LINX Toolkit:** Interfejs do komunikacji z Arduino.
* **Arduino:** Sterowanie fizycznymi serwomechanizmami PWM.

---

## 📐 Architektura Systemu

### 1. Moduł Python (`main.py`)
Skrypt analizuje obraz, oblicza delty zgięcia palców i wysyła 9 wartości (5 palców, yaw, pozycja X, pozycja Y, Gesture ID) jako string oddzielony przecinkami.

### 2. Moduł LabVIEW (`arduinoTest.vi`)
Główny program odbiorczy wykorzystujący rejestry przesuwne (Shift Registers) dla stabilności połączeń.
* **`Parse_All_Data.vi`**: Parsuje string UDP na wartości numeryczne.
* **`Angle_To_DutyCycle.vi`**: Przelicza kąty na sygnał PWM według wzoru:
$$DutyCycle = \left(\frac{Angle}{3600}\right) + 0.05$$

---

## 💻 Instalacja i Uruchomienie

1. Wgraj firmware LINX na Arduino.
2. **Uruchom Python:** `python main.py`
3. **Uruchom LabVIEW:** Otwórz `arduinoTest.vi`, wybierz port COM i kliknij Run.

---

### Autor
* **Twój Nick** - Integracja Python-LabVIEW-Arduino.
