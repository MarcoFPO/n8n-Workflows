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
