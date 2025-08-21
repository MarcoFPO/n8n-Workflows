# LLD: Modell-Training und Inferenz-Pipeline (Punkt 3.4)

---

### 1. Zielsetzung und Geltungsbereich

Dieses Dokument beschreibt die detaillierte technische Implementierung der KI-Modell-Komponente. Es umfasst den Trainingsprozess für die spezialisierten "Experten"-Modelle und das konsolidierende "Meta"-Modell sowie die Inferenz-Pipeline zur Erstellung einer finalen Prognose.

### 2. Verzeichnisstruktur für Modelle und Artefakte

Alle trainierten Modelle und zugehörigen Artefakte werden in einem dedizierten Verzeichnis gespeichert, um eine klare Trennung von Code und Daten zu gewährleisten.

```
/Forschungsprojekt/
|-- models/
|   |-- 1W/  (Prognosefenster 1 Woche)
|   |   |-- technical_expert.h5
|   |   |-- technical_scaler.pkl
|   |   |-- sentiment_expert.pkl
|   |   |-- sentiment_scaler.pkl
|   |   |-- fundamental_expert.pkl
|   |   |-- fundamental_scaler.pkl
|   |   |-- meta_model.pkl
|   |-- 1M/  (Prognosefenster 1 Monat)
|   |   |-- ... (gleiche Struktur)
|   |-- ... (weitere Fenster)
```

*   `.h5`: Format für Keras/TensorFlow-Modelle (LSTM).
*   `.pkl`: Standard-Serialisierungsformat (pickle) für Scikit-learn-Objekte (Scaler) und XGBoost/LightGBM-Modelle.

### 3. Stufe 1: Training der "Experten"-Modelle

Dieser Prozess wird für jedes Prognosefenster (1W, 1M etc.) und für jedes Experten-Modell (Technisch, Sentiment, Fundamental/Makro) separat ausgeführt.

#### 3.1. Implementierung (`train_experts.py`)

Ein zentrales Skript, das über Parameter gesteuert wird (z.B. `python train_experts.py --model_type technical --horizon 1W`).

#### 3.2. Prozess-Schritte

1.  **Daten laden:**
    *   Stelle eine Verbindung zur PostgreSQL-Datenbank her.
    *   Lade die relevanten Features aus der entsprechenden Tabelle (z.B. `features_technical_daily` für das technische Modell).
    *   Lade die Zielvariable (z.B. die zukünftige prozentuale Kursänderung) aus der `raw_price_data`-Tabelle.
    *   Führe einen Join über `security_id` und `timestamp` durch.

2.  **Datenaufteilung:**
    *   Teile den gesamten Datensatz chronologisch in `Trainings-Set` (z.B. 70%) und `Validierungs-Set` (z.B. 15%) und `Test-Set` (z.B. 15%). **Kein Mischen der Daten (`shuffle=False`)!**

3.  **Skalierung:**
    *   Initialisiere einen `MinMaxScaler` von `sklearn.preprocessing`.
    *   Passe den Scaler **ausschließlich** auf dem `Trainings-Set` an: `scaler.fit(X_train)`.
    *   Transformiere Trainings-, Validierungs- und Test-Set: `X_train_scaled = scaler.transform(X_train)`.
    *   Speichere den angepassten Scaler: `joblib.dump(scaler, 'models/1W/technical_scaler.pkl')`.

4.  **Sequenzierung (nur für LSTM):**
    *   Wandle die skalierten Daten in überlappende Sequenzen um (z.B. Input-Länge 60 Tage).

5.  **Modell-Definition & Training:**

    *   **Für Technisches Modell (LSTM):**
        *   **Framework:** TensorFlow/Keras.
        *   **Architektur:**
            ```python
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dropout, Dense

            model = Sequential([
                LSTM(100, return_sequences=True, input_shape=(60, num_features)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(k) # k = 7 für 1W-Prognose
            ])
            model.compile(optimizer='adam', loss='mean_squared_error')
            ```
        *   **Training:**
            ```python
            model.fit(X_train_seq, y_train, validation_data=(X_val_seq, y_val), epochs=50, batch_size=32)
            ```
        *   **Speichern:** `model.save('models/1W/technical_expert.h5')`

    *   **Für Sentiment & Fundamental/Makro (Gradient Boosting):**
        *   **Framework:** LightGBM oder XGBoost.
        *   **Architektur:**
            ```python
            import lightgbm as lgb
            model = lgb.LGBMRegressor(objective='regression_l1', n_estimators=1000, learning_rate=0.05)
            ```
        *   **Training:**
            ```python
            model.fit(X_train_scaled, y_train, eval_set=[(X_val_scaled, y_val)], early_stopping_rounds=50)
            ```
        *   **Speichern:** `joblib.dump(model, 'models/1W/sentiment_expert.pkl')`

### 4. Stufe 2: Training des "Meta"-Modells

Dieser Prozess nutzt die trainierten Experten-Modelle, um den finalen Entscheider zu trainieren.

#### 4.1. Implementierung (`train_meta_model.py`)

#### 4.2. Prozess-Schritte

1.  **Laden der Artefakte:**
    *   Lade alle drei trainierten Experten-Modelle für das jeweilige Prognosefenster (z.B. `technical_expert.h5`, `sentiment_expert.pkl`, ...).
    *   Lade die zugehörigen Scaler.

2.  **Laden der Validierungsdaten:**
    *   Lade das `Validierungs-Set` (`X_val`, `y_val`), das beim Experten-Training zurückgelegt wurde.

3.  **"Out-of-Sample"-Prognosen erstellen:**
    *   Wende die passenden Scaler und Sequenzierung auf `X_val` an.
    *   Erstelle Prognosen mit jedem der drei geladenen Experten-Modelle:
        *   `preds_tech = technical_model.predict(X_val_tech_scaled_seq)`
        *   `preds_sent = sentiment_model.predict(X_val_sent_scaled)`
        *   `preds_fund = fundamental_model.predict(X_val_fund_scaled)`

4.  **Input für Meta-Modell erstellen:**
    *   Konkateniere die drei Prognose-Vektoren zu einem neuen Feature-Set.
        ```python
        import numpy as np
        X_meta_train = np.concatenate([preds_tech, preds_sent, preds_fund], axis=1)
        ```
    *   Die Zielvariable ist das unveränderte `y_val`.

5.  **Meta-Modell-Training:**
    *   **Framework:** LightGBM (bevorzugt wegen Geschwindigkeit und Effizienz).
    *   **Training:**
        ```python
        meta_model = lgb.LGBMRegressor(objective='regression_l1', n_estimators=200)
        meta_model.fit(X_meta_train, y_val)
        ```
    *   **Speichern:** `joblib.dump(meta_model, 'models/1W/meta_model.pkl')`

### 5. Inferenz-Pipeline

Dieser Prozess beschreibt, wie eine einzelne, neue Prognose für ein Wertpapier erstellt wird.

#### 5.1. Implementierung (`predict.py`)

#### 5.2. Prozess-Schritte

1.  **Input:** `security_id`, `prediction_date`, `horizon` (z.B. '1W').

2.  **Laden aller relevanten Artefakte:** Lade alle 4 Modelle und 3 Scaler aus dem Verzeichnis `/models/{horizon}/`.

3.  **Daten für Experten-Modelle holen:**
    *   Hole die letzten `n` Tage (z.B. 60) der Feature-Daten für die `security_id` vor dem `prediction_date` aus den `features_*_daily`-Tabellen.

4.  **Vorverarbeitung & Prognose pro Experte:**
    *   **Technisch:** Skaliere die Daten mit `technical_scaler.pkl`, erstelle eine Sequenz, erstelle Prognose mit `technical_expert.h5`.
    *   **Sentiment:** Skaliere die Daten mit `sentiment_scaler.pkl`, erstelle Prognose mit `sentiment_expert.pkl`.
    *   **Fundamental/Makro:** Skaliere die Daten mit `fundamental_scaler.pkl`, erstelle Prognose mit `fundamental_expert.pkl`.

5.  **Input für Meta-Modell erstellen:**
    *   Konkateniere die drei einzelnen Prognose-Vektoren (wie in Schritt 4.4).

6.  **Finale Prognose:**
    *   Erstelle die finale Prognose mit dem geladenen Meta-Modell: `final_prediction = meta_model.predict(X_meta_input)`.

7.  **Output:** Gib den `final_prediction`-Vektor zurück.
