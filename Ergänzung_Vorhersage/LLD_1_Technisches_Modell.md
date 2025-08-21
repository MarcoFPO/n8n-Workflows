### **LLD 1: Technisches Modell ("Der Chart-Analyst")**

*   **1.1. Zweck/Ziel:** Dieses Modell soll Kursbewegungen ausschließlich auf Basis historischer Preis- und Volumendaten sowie daraus abgeleiteter technischer Indikatoren vorhersagen. Es operiert unter der Annahme, dass zukünftige Bewegungen in historischen Mustern enthalten sind.

*   **1.2. Input-Daten & Features:**
    *   **Rohdaten:** Open, High, Low, Close, Volume (OHLCV) auf täglicher Basis.
    *   **Berechnete Features (Beispiele):**
        *   **Momentum-Indikatoren:** RSI (14 Tage), MACD (12, 26, 9), Stochastik Oszillator.
        *   **Trend-Indikatoren:** SMA (20, 50, 200 Tage), EMA (20, 50 Tage).
        *   **Volatilitäts-Indikatoren:** Bollinger Bänder (20 Tage, 2 Standardabweichungen), Average True Range (ATR).
        *   **Lag-Features:** Prozentuale Veränderung zum Vortag, zur Vorwoche etc.

*   **1.3. Datenvorverarbeitung:**
    1.  **Fehlende Werte:** Forward-Fill (`ffill`) für Wochenenden/Feiertage, um eine kontinuierliche Zeitreihe zu gewährleisten.
    2.  **Feature-Berechnung:** Anwendung von Bibliotheken wie `pandas-ta` zur Berechnung der Indikatoren.
    3.  **Skalierung:** Alle Features werden mit einem `MinMaxScaler` auf den Bereich `[0, 1]` skaliert. Der Scaler wird auf den Trainingsdaten angepasst und für Validierungs-/Testdaten nur transformiert.
    4.  **Sequenzierung:** Die Daten werden in überlappende Sequenzen aufgeteilt.
        *   **Input-Shape (X):** `(Anzahl_Samples, 60, Anzahl_Features)` – z.B. die Daten der letzten 60 Kalendertage.
        *   **Output-Shape (y):** `(Anzahl_Samples, k)` – die prozentuale Kursveränderung für die nächsten `k` Tage (wobei `k` = 7, 30, 150 oder 365).

*   **1.4. Modell-Architektur: Stacked LSTM**
    *   **Typ:** Sequentielles Neuronales Netz (Keras/TensorFlow).
    *   **Layer-Aufbau:**
        1.  `InputLayer(shape=(60, Anzahl_Features))`
        2.  `LSTM(units=100, return_sequences=True)`: Erster Layer, verarbeitet die Sequenz.
        3.  `Dropout(0.2)`: Zur Regularisierung.
        4.  `LSTM(units=50, return_sequences=False)`: Zweiter Layer, gibt nur den letzten Output weiter.
        5.  `Dropout(0.2)`
        6.  `Dense(units=k, activation='linear')`: Output-Layer mit `k` Neuronen für die `k`-Tage-Prognose. Die lineare Aktivierung ist wichtig für ein Regressionsproblem.

*   **1.5. Output:** Ein Vektor mit `k` Fließkommazahlen, die die prognostizierte prozentuale Veränderung für jeden der nächsten `k` Tage darstellen.

*   **1.6. Trainings-Besonderheiten:**
    *   **Verlustfunktion:** `MeanSquaredError` (MSE).
    *   **Optimierer:** `Adam` mit einer anpassbaren Lernrate.
