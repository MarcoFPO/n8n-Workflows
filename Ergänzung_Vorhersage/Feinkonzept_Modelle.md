### **Feinkonzept (Low-Level Design): KI-Prognosemodelle**

Dieses Dokument beschreibt das detaillierte Design der einzelnen KI-Modelle, die als Komponenten des Ensemble-Systems zur Aktienprognose dienen.

---

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

---

### **LLD 2: Sentiment-Modell ("Der Stimmungs-Fänger")**

*   **2.1. Zweck/Ziel:** Dieses Modell prognostiziert Kursbewegungen basierend auf der öffentlichen und medialen Stimmung. Es soll Hype, Angst und allgemeine Meinungsänderungen erfassen, die oft kurzfristige Kursreaktionen auslösen.

*   **2.2. Input-Daten & Features:**
    *   **Rohdaten:** Nachrichten-Schlagzeilen, Twitter/X-Beiträge, Analysten-Ratings.
    *   **Aggregierte Features (pro Tag):**
        *   `avg_sentiment_score`: Durchschnittlicher Sentiment-Score (-1 bis 1) aller Nachrichten/Beiträge.
        *   `news_volume`: Anzahl der Artikel/Beiträge pro Tag.
        *   `positive_buzz_ratio`: Verhältnis von positiven zu negativen Erwähnungen.
        *   `analyst_rating_encoded`: One-Hot-Encoding der "Kaufen", "Halten", "Verkaufen"-Empfehlungen.

*   **2.3. Datenvorverarbeitung:**
    1.  **NLP-Pipeline:** Für jeden Textbeitrag: Bereinigung (Entfernen von URLs, Sonderzeichen) -> Sentiment-Analyse mit einem vortrainierten Finanz-Modell (z.B. FinBERT) oder einer Bibliothek wie VADER.
    2.  **Aggregation:** Zusammenfassen der individuellen Scores auf Tagesbasis.
    3.  **Encoding:** Umwandlung der kategorialen Analysten-Ratings in numerische Vektoren.
    4.  **Skalierung:** `MinMaxScaler` für numerische Features wie `news_volume`.
    5.  **Sequenzierung:** Analog zum Technischen Modell (z.B. Input-Sequenz von 30-60 Tagen).

*   **2.4. Modell-Architektur: Gradient Boosting (XGBoost)**
    *   **Typ:** XGBoost Regressor. LSTMs sind möglich, aber XGBoost ist oft sehr stark bei heterogenen, tabellarischen Zeitreihendaten und einfacher zu tunen.
    *   **Konfiguration (Beispiele für Hyperparameter-Tuning):**
        *   `n_estimators`: 100 - 1000 (Anzahl der Bäume).
        *   `max_depth`: 3 - 10 (Tiefe der Bäume).
        *   `learning_rate`: 0.01 - 0.3.
        *   `objective`: `reg:squarederror`.

*   **2.5. Output:** Ein Vektor mit `k` Fließkommazahlen (Prognose für die nächsten `k` Tage).

*   **2.6. Herausforderungen:** Die Qualität der Prognose hängt extrem von der Qualität und dem Umfang der Sentiment-Daten ab. Rauschen, Sarkasmus und Bots sind eine große Herausforderung.

---

### **LLD 3: Fundamental-/Makro-Modell ("Der Ökonom")**

*   **3.1. Zweck/Ziel:** Dieses Modell soll langfristige Trends basierend auf der finanziellen Gesundheit des Unternehmens und dem gesamtwirtschaftlichen Umfeld vorhersagen. Es ist besonders relevant für die 5M- und 12M-Prognosen.

*   **3.2. Input-Daten & Features:**
    *   **Fundamental (pro Quartal):** EPS, P/E Ratio, Debt-to-Equity, Umsatz.
    *   **Makroökonomisch (pro Monat/Woche):** Leitzins, Inflationsrate (CPI), Arbeitslosenquote, VIX.

*   **3.3. Datenvorverarbeitung:**
    1.  **Frequenz-Anpassung:** Die größte Herausforderung. Da die Daten eine niedrige Frequenz haben (z.B. quartalsweise), werden sie für die tägliche Modellierung **forward-filled**. Der EPS-Wert aus dem Q2-Bericht gilt also für jeden Tag in Q3.
    2.  **Skalierung:** `MinMaxScaler` für alle Features.
    3.  **Sequenzierung:** Hier kann eine längere Input-Sequenz sinnvoll sein (z.B. 365 Tage), um die langsam ändernden Daten besser zu erfassen.

*   **3.4. Modell-Architektur: Gradient Boosting (XGBoost)**
    *   **Typ:** XGBoost Regressor. Ähnlich wie beim Sentiment-Modell eignet sich XGBoost hervorragend für diese Art von tabellarischen, niedrigfrequenten Daten.
    *   **Konfiguration:** Ähnliche Hyperparameter wie beim Sentiment-Modell.

*   **3.5. Output:** Ein Vektor mit `k` Fließkommazahlen.

*   **3.6. Anmerkungen:** Dieses Modell wird alleinstehend eine schlechte kurzfristige Performance haben. Sein Wert liegt in der Kombination mit den anderen Modellen im Meta-Modell.

---

### **LLD 4: Meta-Modell ("Der Entscheider")**

*   **4.1. Zweck/Ziel:** Intelligente Konsolidierung der Prognosen der drei "Experten"-Modelle zu einer einzigen, robusteren Endprognose. Es lernt, welchem Experten in welcher Situation zu vertrauen ist.

*   **4.2. Input-Daten & Features:**
    *   Die **Outputs** der drei Experten-Modelle.
    *   Für eine `k`-Tage-Prognose ist der Input-Vektor: `[pred_tech_1...k, pred_sent_1...k, pred_fund_1...k]`.
    *   Die Gesamtzahl der Features ist also `3 * k`.

*   **4.3. Datenvorverarbeitung:**
    *   Im Normalfall ist keine weitere Skalierung notwendig, da die Inputs bereits Prognosen im selben Wertebereich (prozentuale Veränderung) sind.

*   **4.4. Modell-Architektur: LightGBM oder einfaches Neuronales Netz**
    *   **Option A (Bevorzugt): LightGBM Regressor:** Sehr schnell und effizient, gut für die relativ kleine Feature-Anzahl geeignet.
    *   **Option B (Alternativ): Simples Feed-Forward Neuronales Netz:**
        1.  `InputLayer(shape=(3 * k))`
        2.  `Dense(units=16, activation='relu')`
        3.  `Dense(units=8, activation='relu')`
        4.  `Dense(units=k, activation='linear')`

*   **4.5. Output:** Der finale Prognose-Vektor mit `k` Fließkommazahlen.

*   **4.6. Trainings-Besonderheiten:**
    *   **WICHTIG:** Das Meta-Modell darf nur auf **out-of-sample**-Prognosen der Experten-Modelle trainiert werden, um Data Leakage zu vermeiden.
    *   **Workflow:**
        1.  Teile die Daten in Training, Validierung und Test.
        2.  Trainiere die Experten-Modelle auf dem **Trainings-Set**.
        3.  Erzeuge mit den trainierten Experten-Modellen Prognosen für das **Validierungs-Set**.
        4.  Trainiere das Meta-Modell auf diesen **Validierungs-Prognosen**.
        5.  Die finale Evaluation des gesamten Systems erfolgt auf dem **Test-Set**.
