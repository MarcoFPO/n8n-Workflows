# LLD: Evaluations- & Teststrategie (Punkt 5)

---

### 1. Zielsetzung

Dieses Dokument definiert die Metriken und Methoden zur Bewertung der Prognosequalität der KI-Modelle. Ziel ist es, eine objektive und realistische Einschätzung der Modell-Performance zu erhalten und Overfitting zu erkennen.

### 2. Baseline-Modell

Jedes KI-Modell muss gegen eine naive, aber sinnvolle Baseline antreten, um seinen Mehrwert zu beweisen.

*   **Baseline-Modell:** **Persistence Model (Naives Modell)**
    *   **Logik:** Die prozentuale Veränderung der letzten `n` Tage wird für die nächsten `k` Tage einfach fortgeschrieben. Für eine 1-Tages-Prognose wäre die Vorhersage "keine Veränderung" (0%).
    *   **Implementierung:** Einfache `pandas.shift()`-Operation.
    *   **Zweck:** Wenn das komplexe KI-Modell diese simple Heuristik nicht signifikant schlägt, ist es nicht nützlich.

### 3. Evaluations-Metriken

Da es sich um ein Regressionsproblem handelt, werden mehrere Metriken verwendet, um verschiedene Aspekte der Prognosequalität zu bewerten.

*   **3.1. Fehler-Metriken:**
    *   **Mean Absolute Error (MAE):** `mean(abs(y_true - y_pred))`
        *   **Interpretation:** Der durchschnittliche absolute Fehler in der Prognose (z.B. "Die Prognose lag im Schnitt um 0.5% daneben"). Intuitiv verständlich.
    *   **Root Mean Squared Error (RMSE):** `sqrt(mean((y_true - y_pred)^2))`
        *   **Interpretation:** Ähnlich wie MAE, bestraft aber größere Fehler stärker.

*   **3.2. Richtungs-Metrik (Wichtigste Metrik):**
    *   **Directional Accuracy (DA):** `(Anzahl der Fälle, wo sign(y_true) == sign(y_pred)) / (Gesamtzahl der Fälle)`
        *   **Interpretation:** "In wie viel Prozent der Fälle hat das Modell die Richtung der Kursbewegung (positiv/negativ) korrekt vorhergesagt?".
        *   **Zweck:** Für eine Handelsstrategie ist die korrekte Vorhersage der Richtung oft wichtiger als die exakte Höhe der Veränderung. Ein Wert > 50% ist erstrebenswert.

*   **3.3. Güte-Metrik:**
    *   **R-squared (R²):** `1 - (sum((y_true - y_pred)^2) / sum((y_true - mean(y_true))^2))`
        *   **Interpretation:** "Wie viel Prozent der Varianz in den Kursdaten kann das Modell erklären?". Ein Wert nahe 1.0 ist ideal, bei Finanzdaten sind aber schon Werte > 0.1 oft bemerkenswert.

### 4. Test-Methodik: Walk-Forward Validation

Eine einfache chronologische Aufteilung in Training/Test (85/15) ist gut, aber nicht ausreichend robust. Eine **Walk-Forward Validation** (auch als "Rolling Forecast" bekannt) simuliert den realen Einsatz des Modells über die Zeit.

*   **Prozess:**
    1.  **Initiales Training:** Trainiere das Modell auf einem initialen Datenblock (z.B. die ersten 5 Jahre).
    2.  **Prognose:** Erstelle eine Prognose für die nächste Periode (z.B. den nächsten Monat).
    3.  **Evaluation:** Speichere die Prognose und den tatsächlichen Wert.
    4.  **Fortschreiten:** Erweitere das Trainingsfenster um die prognostizierte Periode (den Monat aus Schritt 2).
    5.  **Retraining:** Trainiere das Modell auf den erweiterten Daten neu.
    6.  **Wiederholen:** Gehe zu Schritt 2 und wiederhole den Prozess, bis das Ende des Datensatzes erreicht ist.

*   **Vorteile:**
    *   Simuliert einen realen Einsatz, bei dem das Modell periodisch mit neuen Daten neu trainiert wird.
    *   Verhindert, dass das Modell auf Daten trainiert wird, die zeitlich nach den Testdaten liegen (Lookahead Bias).
    *   Erzeugt eine robuste Serie von "out-of-sample"-Prognosen, auf der die Metriken berechnet werden können.

### 5. Reporting

Die Evaluationsergebnisse werden in einer Tabelle pro Prognosehorizont (1W, 1M, etc.) zusammengefasst, die das KI-Modell mit der Baseline vergleicht.

**Beispiel-Tabelle (für 1W-Prognose):**

| Modell | MAE | RMSE | Directional Accuracy | R² |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline** | 0.025 | 0.035 | 50.1% | -0.05 |
| **Ensemble-KI** | **0.018** | **0.027** | **54.2%** | **0.12** |
