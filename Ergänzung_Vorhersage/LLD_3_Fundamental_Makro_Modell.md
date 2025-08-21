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
