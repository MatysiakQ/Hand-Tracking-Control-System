# 🤖 Smart Robotic Hand Controller

[![Status](https://img.shields.io/badge/Status-Closed-red)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)
[![Tech](https://img.shields.io/badge/Stack-Python%20%7C%20LabVIEW%20%7C%20Arduino-green)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)
[![AI](https://img.shields.io/badge/AI-MediaPipe%20%26%20OpenCV-blue)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)

## 📝 O Projekcie
Zaawansowany system sterowania robotyczną dłonią w czasie rzeczywistym, łączący sztuczną inteligencję z inżynierią sterowania. Projekt umożliwia bezdotykowe sterowanie fizycznym manipulatorem poprzez mapowanie ruchów ludzkiej dłoni na sygnały sterujące serwomechanizmami.

## 🛠️ Stos Technologiczny (Tech Stack)
- **Python 3.x:** OpenCV & MediaPipe – odpowiedzialne za tracking 21 punktów dłoni i analizę gestów.
- **LabVIEW 2025:** Centrum dowodzenia – odbiór danych UDP, parsująca logika sterowania i GUI.
- **LINX Toolkit:** Interfejs komunikacyjny między LabVIEW a mikrokontrolerem.
- **Hardware:** Arduino + Serwomechanizmy (sterowanie PWM).

## ✨ Główne Funkcje
- **Precyzyjny Hand Tracking:** Detekcja zgięcia 5 palców oraz rotacji nadgarstka (Yaw).
- **Komunikacja UDP:** Błyskawiczny przesył danych między modułem wizyjnym (Python) a sterownikiem (LabVIEW) na porcie 5010.
- **Filtrowanie Sygnału:** Stabilizacja ruchu za pomocą filtrów EMA (Exponential Moving Average) oraz filtrów medianowych, eliminujących drgania.
- **Bezpieczne Mapowanie:** Przeliczanie kątów na sygnał Duty Cycle według precyzyjnego wzoru:
  $$DutyCycle = \left(\frac{Angle}{3600}\right) + 0.05$$
- **Gesture Recognition:** System rozpoznaje unikalne ID gestów, co pozwala na automatyczne wyzwalanie sekwencji ruchowych.

## 🚀 Jak to uruchomić?
1. **Firmware:** Wgraj oprogramowanie LINX na Arduino.
2. **AI Module:** Uruchom skrypt `main.py` w folderze `Kod`, aby zainicjować kamerę i tracking.
3. **Control:** Otwórz `arduinoTest.vi` w LabVIEW, wybierz port COM i uruchom program.

## 📂 Zawartość Projektu
- **`Kod`** – Kompletna logika sterująca (Python & LabVIEW).
- **`REKA ROBOTA`** – Pliki projektowe dłoni.
- **`ADAPTER` / `PRZEDRAMIE`** – Elementy konstrukcyjne do druku/montażu.

## 👥 Autor
- Adam Jastrzębski
- Łukasz Koszołko

---
*Projekt łączy Computer Vision z robotyką, dostarczając gotowe rozwiązanie do interakcji człowiek-maszyna.*
