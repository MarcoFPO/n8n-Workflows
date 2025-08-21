### **LLD Datengewinnung & -vorverarbeitung 2: Sentiment-Modell (International)**

---

#### **1. Datengewinnung (Data Acquisition)**

*   **1.1. Quellen:**
    *   **Nachrichten:** NewsAPI.
    *   **Social Media:** Twitter/X API.
    *   **Analysten-Ratings:** Internationale Finanzdaten-Anbieter.

*   **1.2. Prozess (Internationale Anpassungen):**
    1.  **Mehrsprachige Suchanfragen:**
        *   **NewsAPI:** Nutze die Parameter `language` und `country`, um die Suche auf relevante Regionen und Sprachen zu beschränken (z.B. `language='de'`, `country='de'` für deutsche Nachrichten über ein deutsches Unternehmen).
        *   **Twitter/X:** Verwende den `lang:`-Operator in der Suchanfrage.
    2.  **Keyword-Übersetzung:** Die Such-Keywords müssen für jede Zielsprache angepasst werden (z.B. "Aktie", "Gewinn", "share", "profit").
    3.  **Speicherung:** Die `raw_news_articles`-Tabelle sollte eine zusätzliche Spalte `language` enthalten, um die Sprache des Quelltextes zu speichern.

---

#### **2. Datenvorverarbeitung (Data Preprocessing)**

*   **2.1. Ziel:** Umwandlung von **mehrsprachigen**, unstrukturierten Textdaten in einen täglichen, aggregierten und numerischen Feature-Satz.

*   **2.2. Schritte:**

    1.  **Laden der Roh-Texte:** Lade Texte für einen Ticker, inklusive der Sprachinformation.

    2.  **NLP-Pipeline (Sentiment-Analyse pro Text) - **KRITISCHE ANPASSUNG**:**
        *   **Modellwahl:** Ein rein englisches Modell wie FinBERT ist nicht mehr ausreichend.
            *   **Option A (Bevorzugt): Multilinguale Modelle:** Verwende ein mehrsprachiges Transformer-Modell (z.B. `XLM-RoBERTa` oder `BERT Base Multilingual`) aus der `Hugging Face`-Bibliothek. Diese Modelle verstehen mehrere Sprachen nativ. Eventuell ist ein Fine-Tuning auf Finanztexten verschiedener Sprachen notwendig.
            *   **Option B (Alternativ): Translation-Pipeline:** Übersetze alle nicht-englischen Texte zuerst mit einem Dienst wie Google Translate API oder DeepL API ins Englische und wende dann das englische `FinBERT`-Modell an. (Nachteil: Kosten und potenzieller Informationsverlust durch Übersetzung).
        *   Der restliche Prozess (Bereinigung, Tokenisierung, Inferenz) bleibt konzeptionell gleich, verwendet aber das gewählte multilinguale Modell.

    3.  **Tägliche Aggregation:** (Unverändert) Gruppiere die analysierten Texte nach Datum und berechne die aggregierten Features.

    4.  **Integration & Umgang mit fehlenden Werten:** (Unverändert) Fülle Tage ohne Aktivität mit neutralen Werten.

    5.  **Skalierung & Sequenzierung:** (Unverändert) Führe die Skalierung und Sequenzerstellung wie beim technischen Modell durch.