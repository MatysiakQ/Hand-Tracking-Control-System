# 🤖 Smart Robotic Hand Controller

[![Status](https://img.shields.io/badge/Status-Closed-red)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)
[![Tech](https://img.shields.io/badge/Stack-Python%20%7C%20LabVIEW%20%7C%20Arduino-green)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)
[![AI](https://img.shields.io/badge/AI-MediaPipe%20%26%20OpenCV-blue)](https://github.com/MatysiakQ/Hand-Tracking-Control-System)

## 📝 O Projekcie
Zaawansowany system sterowania robotyczną dłonią w czasie rzeczywistym. Projekt integruje sztuczną inteligencję (Computer Vision) z inżynierią sterowania (LabVIEW/Arduino), umożliwiając bezdotykowe sterowanie fizycznym urządzeniem za pomocą gestów dłoni.

## 🛠️ Stos Technologiczny (Tech Stack)
- **Python 3.x:** OpenCV, MediaPipe (detekcja 21 punktów dłoni, logika wizyjna).
- **LabVIEW 2025:** Komunikacja UDP, parsowanie danych, interfejs GUI.
- **LINX Toolkit:** Komunikacja i sterowanie Arduino.
- **Hardware:** Arduino + Serwomechanizmy (sterowanie PWM).

## ✨ Główne Funkcje
- **Precyzyjny Hand Tracking:** Detekcja kątów zgięcia 5 palców oraz obrotu nadgarstka (Yaw).
- **Stabilizacja Ruchu:** Zastosowanie filtrów EMA (Exponential Moving Average) oraz Medianowych dla eliminacji drgań.
- **Szybka Komunikacja UDP:** Przesył danych między Pythonem a LabVIEW (Port 5010) z minimalnym opóźnieniem.
- **Automatyczna Konwersja Sygnałów:** Przeliczanie kątów na bezpieczne wartości Duty Cycle dla serw:
  $$DutyCycle = \left(\frac{Angle}{3600}\right) + 0.05$$
- **Rozpoznawanie Gestów:** Wbudowany Gesture ID pozwalający na wyzwalanie konkretnych akcji.

## 🚀 Uruchomienie
1. **Hardware:** Wgraj firmware LINX na swoje Arduino.
2. **AI Module:** Uruchom skrypt Python (`main.py`), aby rozpocząć tracking i nadawanie danych UDP.
3. **Control Center:** Otwórz `arduinoTest.vi` w LabVIEW, wybierz odpowiedni port COM i uruchom program.

## 📂 Zawartość Repozytorium
- `Kod/` – Skrypty Python oraz pliki LabVIEW (.vi).
- `REKA ROBOTA/` – Pliki powiązane z konstrukcją fizyczną dłoni.
- `ADAPTER/` & `PRZEDRAMIE/` – Elementy konstrukcyjne/montażowe.

## 👥 Autor
- Adam Jastrzębski
-Łukasz Koszołko

---
*Projekt z obszaru robotyki i integracji systemów AI.*
