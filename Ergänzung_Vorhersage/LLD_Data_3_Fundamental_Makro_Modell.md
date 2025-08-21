### **LLD Datengewinnung & -vorverarbeitung 3: Fundamental-/Makro-Modell (International)**

---

#### **1. Datengewinnung (Data Acquisition)**

*   **1.1. Quellen:**
    *   **Fundamentaldaten:** Kommerzielle Anbieter mit breiter internationaler Abdeckung sind hier fast unerlässlich (z.B. EOD Historical Data, Alpha Vantage, FactSet, Refinitiv). `yfinance` kann für große internationale Unternehmen ausreichen, ist aber bei kleineren oft lückenhaft.
    *   **Makroökonomische Daten:**
        *   **USA:** FRED (Federal Reserve Economic Data).
        *   **Europa:** Eurostat API.
        *   **Weltweit/Industrieländer:** OECD (Organisation for Economic Co-operation and Development) API.
        *   **Globale Indikatoren:** World Bank Open Data.
        *   **Nationale Quellen:** Statistische Ämter der jeweiligen Länder (z.B. Destatis für Deutschland, ONS für UK).

*   **1.2. Prozess:**
    1.  **Fundamentaldaten:**
        *   Der Prozess bleibt gleich, aber die API-Aufrufe richten sich an die gewählte internationale Quelle.
        *   **Wichtiger Aspekt:** Rechnungslegungsstandards (z.B. IFRS vs. US-GAAP). Ein guter Datenanbieter normalisiert diese Unterschiede, sodass Kennzahlen wie "Revenue" oder "Net Income" vergleichbar sind.
    2.  **Makroökonomische Daten:**
        *   Erstelle separate Skripte für den Abruf von Daten aus den verschiedenen Makro-Quellen (OECD, Eurostat etc.).
        *   Speichere die Daten in einer `macro_data`-Tabelle mit Spalten für das Land/die Region, den Indikatornamen und den Wert.

---

#### **2. Datenvorverarbeitung (Data Preprocessing)**

*   **2.1. Ziel:** Kombination von Daten unterschiedlicher Frequenzen und geografischer Herkunft zu einem einheitlichen, täglichen Feature-Set.

*   **2.2. Schritte:**

    1.  **Erstellung des täglichen Ziel-Index:** (Unverändert).

    2.  **Frequenz-Anpassung & Zusammenführung (Join):**
        *   **Makro-Daten:** Wähle für jede Aktie die relevanten Makro-Indikatoren aus. Für ein deutsches Unternehmen (z.B. Volkswagen) wären dies Daten aus Deutschland (Destatis) und der Eurozone (Eurostat). Für ein globales Unternehmen wie Apple sind US-Daten (FRED) und globale Indikatoren (OECD) relevant. Führe diese dann per `merge` und `ffill()` zusammen.
        *   **Fundamental-Daten:** (Unverändert) `merge` und `ffill()`.

    3.  **Vermeidung von Lookahead Bias:** (Unverändert) Verschiebe die Fundamental-Daten, um die Meldeverzögerung zu simulieren.

    4.  **Feature Engineering:** (Unverändert).

    5.  **Umgang mit verbleibenden `NaN`s:** (Unverändert).

    6.  **Skalierung & Sequenzierung:** (Unverändert).