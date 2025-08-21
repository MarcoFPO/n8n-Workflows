### **LLD Datengewinnung & -vorverarbeitung 1: Technisches Modell (International)**

---

#### **1. Datengewinnung (Data Acquisition)**

*   **1.1. Quellen:** Globale Finanzdaten-APIs.
    *   **Option A (kostenlos, gut für PoC):** `yfinance` in Python.
    *   **Option B (kommerziell, robuster):** Polygon.io, EOD Historical Data, Alpha Vantage. Diese bieten breitere Abdeckung und höhere API-Limits.

*   **1.2. Prozess:**
    1.  **Definition internationaler Ticker:** Ticker müssen Börsen-spezifische Suffixe enthalten.
        *   **Beispiele für `yfinance`:** `AAPL` (NASDAQ), `VOW3.DE` (XETRA, Deutschland), `SHEL.L` (London Stock Exchange), `7203.T` (Toyota, Tokyo).
    2.  **Abruf der OHLCV-Daten:** Verwende die `yfinance.download()`-Funktion oder die entsprechende Methode der kommerziellen API.
    3.  **Behandlung von Zeitzonen & Handelskalendern:**
        *   Die APIs liefern in der Regel Zeitstempel in UTC oder der lokalen Börsenzeit. Standardisiere alle Daten bei der Speicherung auf UTC.
        *   Beachte, dass nationale Feiertage zu Lücken in den Daten führen, die im Vorverarbeitungsschritt korrekt behandelt werden müssen.
    4.  **Speicherung:** Speichere die Rohdaten in einer `raw_price_data`-Tabelle in der Datenbank. Der Primärschlüssel `(timestamp, ticker)` bleibt bestehen.

---

#### **2. Datenvorverarbeitung (Data Preprocessing)**

*   **2.1. Ziel:** Umwandlung der Rohdaten in einen skalierten, sequenzierten Feature-Satz, der als Input für das LSTM-Modell dient.

*   **2.2. Schritte:**

    1.  **Laden der Daten:** Lade die Rohdaten für einen Ticker aus der Datenbank.

    2.  **Erstellung eines Kalendertag-Index:** (Unverändert) Erstelle einen vollständigen Datumsbereich und `reindexe` den DataFrame.

    3.  **Umgang mit fehlenden Werten (Wochenenden/Feiertage):** (Unverändert) Wende `ffill()` an und setze das Volumen auf 0.

    4.  **Feature Engineering (Technische Indikatoren):** (Unverändert) Die Berechnung der Indikatoren ist universell und nicht von der Region abhängig.

    5.  **Bereinigung:** (Unverändert) Entferne Zeilen mit `NaN`-Werten nach der Indikator-Berechnung.

    6.  **Skalierung der Features:** (Unverändert) Passe den `MinMaxScaler` nur auf den Trainingsdaten an.

    7.  **Sequenzierung (Sliding Window):** (Unverändert) Erzeuge die `X`- und `y`-Arrays für das Modell-Training.

    8.  **Speicherung:** (Unverändert) Zwischenspeicherung der verarbeiteten Arrays.