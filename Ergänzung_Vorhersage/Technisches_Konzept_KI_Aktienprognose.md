### **Technisches Konzept (High-Level Design): KI-gestützte Aktienprognose**

#### 1. Zielsetzung
Entwicklung eines KI-gestützten Systems zur Prognose der prozentualen Kursveränderung einer Aktie für **variable Zeiträume in der Zukunft**. Die Prognosefenster sind **1 Woche (7 Tage), 1 Monat (ca. 30 Tage), 5 Monate (ca. 150 Tage) und 12 Monate (ca. 365 Tage)**. Alle Berechnungen basieren auf **Kalendertagen**. Das System soll historische Marktdaten und technische Indikatoren nutzen, um eine möglichst genaue Vorhersage zu treffen. Das Ergebnis ist keine Anlageberatung, sondern ein technisches Forschungsprodukt.

#### 2. Systemarchitektur (High-Level)
Die Architektur lässt sich in mehrere logische Blöcke unterteilen, die einen Datenfluss von der Rohdatenerfassung bis zur finalen Prognose abbilden.

```
[Datenquellen] -> [Datenakquise-Modul] -> [Datenbank] -> [Datenvorverarbeitungs- & Feature-Engineering-Modul] -> [KI-Prognosemodell] -> [Prognose-Output]
      ^                                        |                                                                     ^
      |                                        |                                                                     |
      +----------------------------------------+------------------- [Modell-Trainings-Pipeline] <---------------------+
```

#### 3. Komponenten im Detail

**3.1. Datenquellen (Data Sources)**
*   **Primärquelle: Historische Kursdaten:**
    *   Inhalte: Open, High, Low, Close, Volume (OHLCV).
    *   Granularität: Täglich.
    *   Beispiele für APIs: Alpha Vantage, Yahoo Finance (via `yfinance`), Polygon.io.
*   **Sekundärquelle (Optional): Sentiment-Daten:**
    *   Inhalte: Nachrichten-Schlagzeilen, Social-Media-Beiträge.
    *   Beispiele für APIs: NewsAPI, Twitter API.

**3.2. Datenakquise-Modul (Data Ingestion)**
*   **Funktion:** Regelmäßiges und automatisiertes Abrufen von Daten aus den definierten Quellen.
*   **Implementierung:** Python-Skripte, die über einen Scheduler (z.B. Airflow, cronjob) täglich ausgeführt werden.
*   **Speicherung:** Die Rohdaten und abgeleiteten Features werden in einer **Zeitreihen-Datenbank** gespeichert. Dies ermöglicht effiziente Abfragen und Skalierbarkeit.
    *   **Beispiele:** PostgreSQL mit der **TimescaleDB**-Erweiterung (bevorzugt für relationale und Zeitreihen-Daten), InfluxDB.

**3.3. Datenvorverarbeitung & Feature Engineering**
*   **Datenbereinigung:** Umgang mit fehlenden Werten. Da wir Kalendertage betrachten, werden Wochenenden und Feiertage keine Kursdaten haben. Diese Lücken müssen bewusst behandelt werden (z.B. durch Auffüllen mit dem letzten bekannten Wert - "forward fill").
*   **Normalisierung:** Skalierung aller numerischen Features auf einen einheitlichen Bereich (z.B. 0 bis 1).
*   **Feature Engineering (Merkmalserstellung):**
    *   **Technische Indikatoren:** RSI, MACD, Bollinger Bänder, Gleitende Durchschnitte (SMA, EMA) etc.
    *   **Zeitbasierte Features:** Kalendertag im Jahr, Wochentag, Monat, Quartal.
    *   **Lag-Features:** Kursveränderungen der letzten `n` Tage.
*   **Sequenzierung:** Die Daten werden in überlappende Fenster (Sequenzen) aufgeteilt.
    *   **Input (X):** Daten der letzten 60-180 Tage (z.B. `[180 Tage x N Features]`).
    *   **Output (y):** Prozentuale Kursveränderung für die nächsten `k` Kalendertage, wobei `k` dem gewählten Prognosefenster entspricht (7, 30, 150 oder 365).

**3.4. KI-Prognosemodell (AI Core Model)**
*   **Modellwahl: LSTM (Long Short-Term Memory) Netzwerk:** LSTMs sind ideal für das Erkennen von Mustern in langen Zeitsequenzen.
*   **Architektur:** Für jedes Prognosefenster wird ein **eigenes, spezialisiertes Modell** trainiert.
    *   Ein Stack aus mehreren LSTM-Layern, gefolgt von `Dropout`-Layern.
    *   Ein finaler `Dense`-Layer mit `k` Neuronen, wobei `k` die Länge des Prognosefensters ist (z.B. 7 Neuronen für die 1-Wochen-Prognose, 30 für die 1-Monats-Prognose usw.).
*   **Baseline-Modell:** Zum Vergleich sollte immer ein einfaches Modell (z.B. ARIMA) implementiert werden.
*   **Verlustfunktion:** Mean Squared Error (MSE).
*   **Optimierer:** Adam.

**3.5. Modell-Trainings-Pipeline**
*   **Datensplitting:** Strikte chronologische Aufteilung der Daten in Trainings- (70%), Validierungs- (15%) und Testsets (15%), um "Data Leakage" zu vermeiden.
*   **Training:** Jedes der vier Modelle (1W, 1M, 5M, 12M) wird separat auf den Trainingsdaten trainiert und auf den Validierungsdaten optimiert.
*   **Evaluation:** Die finale Leistung wird auf den Testdaten bewertet (Metriken: R², MSE, MAE, Directional Accuracy).

**3.6. Prognose-Output (Inference)**
*   Ein Skript oder API-Endpunkt nimmt die neuesten verfügbaren Daten, wählt das gewünschte Prognosemodell (z.B. "12M"), führt die Vorverarbeitung durch und generiert die Prognose.
*   Das Ergebnis ist ein Array von `k` Werten, die die prognostizierte prozentuale Veränderung für die kommenden `k` Kalendertage darstellen.

#### 4. Technologie-Stack (Vorschlag)
*   **Programmiersprache:** Python
*   **Datenbank:** PostgreSQL mit TimescaleDB
*   **Datenanalyse & -verarbeitung:** Pandas, NumPy
*   **KI/Machine Learning Framework:** TensorFlow/Keras oder PyTorch
*   **Technische Indikatoren:** `pandas-ta`
*   **Datenakquise:** `yfinance`, `requests`
*   **API (optional):** FastAPI oder Flask

#### 5. Risiken und Limitationen
*   **Marktvolatilität:** Unvorhersehbare Ereignisse können nicht modelliert werden.
*   **Lange Prognosefenster:** Die Unsicherheit und der Fehler einer Prognose nehmen mit der Länge des Prognosefensters drastisch zu. Insbesondere 5- und 12-Monats-Prognosen sind hochspekulativ.
*   **Kalendertage vs. Handelstage:** Die Verwendung von Kalendertagen vereinfacht die Modellierung, ignoriert aber die Tatsache, dass der Handel nur an bestimmten Tagen stattfindet. Das Modell muss lernen, mit den "stillen" Tagen (Wochenenden/Feiertagen) umzugehen.

#### 6. Nächste Schritte
1.  **Proof of Concept (PoC):**
    *   Aufsetzen der Datenbank (PostgreSQL/TimescaleDB).
    *   Implementierung der Datenpipeline für eine Aktie.
    *   Aufbau und Training des **1-Wochen-Modells** als ersten Testfall.
    *   Evaluation der Ergebnisse.
2.  **Iteration und Erweiterung:**
    *   Training der Modelle für die längeren Prognosezeiträume.
    *   Optimierung der Feature-Auswahl und Modellarchitektur.