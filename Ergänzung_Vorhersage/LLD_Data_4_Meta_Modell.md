### **LLD Datengewinnung & -vorverarbeitung 4: Meta-Modell**

---

#### **1. Datengewinnung (Data "Acquisition")**

*   **1.1. Quelle:** Die **Prognosen (Outputs)** der drei trainierten "Experten"-Modelle (Technisch, Sentiment, Fundamental/Makro). Es findet keine externe Datengewinnung statt.

*   **1.2. Prozess zur Vermeidung von Data Leakage:**
    *   Dieser Prozess ist entscheidend für die Gültigkeit des Modells. Das Meta-Modell darf **niemals** auf Prognosen trainiert werden, die auf Daten basieren, die das Experten-Modell bereits im Training gesehen hat.

    *   **Korrekter Workflow:**
        1.  **Datenaufteilung:** Teile den gesamten Datensatz chronologisch in drei Teile: `Trainings-Set_A` (z.B. 60%), `Trainings-Set_B` (z.B. 20%) und `Test-Set_C` (z.B. 20%).
        2.  **Experten-Training:** Trainiere die drei Experten-Modelle (Technisch, Sentiment, Fundamental/Makro) **ausschließlich** auf `Trainings-Set_A`.
        3.  **Prognose-Generierung (Input für Meta-Modell):**
            *   Lasse die auf Set A trainierten Experten-Modelle Prognosen für `Trainings-Set_B` erstellen. Diese Prognosen sind "out-of-sample" und dienen als **Trainingsdaten (X_meta_train)** für das Meta-Modell.
            *   Die tatsächlichen Kursveränderungen in `Trainings-Set_B` sind das **Trainings-Ziel (y_meta_train)**.
        4.  **Finale Evaluation:**
            *   Lasse die auf Set A trainierten Experten-Modelle ebenfalls Prognosen für das `Test-Set_C` erstellen. Diese Prognosen sind die **Testdaten (X_meta_test)** für das Meta-Modell.
            *   Die tatsächlichen Kursveränderungen in `Test-Set_C` sind das **Test-Ziel (y_meta_test)**.

---

#### **2. Datenvorverarbeitung (Data Preprocessing)**

*   **2.1. Ziel:** Zusammenfügen der Experten-Prognosen zu einem einzigen Feature-Vektor für das Meta-Modell.

*   **2.2. Schritte:**

    1.  **Laden der Prognosen:** Lade die generierten Prognose-Arrays der drei Experten-Modelle. Jedes Array hat die Form `(Anzahl_Samples, k)`, wobei `k` das Prognosefenster ist.
        *   `predictions_technical`
        *   `predictions_sentiment`
        *   `predictions_fundamental`

    2.  **Feature-Konkatenierung (Zusammenfügen):**
        *   Kombiniere die Arrays entlang der Feature-Achse.
        *   Beispiel-Code:
            ```python
            import numpy as np
            X_meta = np.concatenate([
                predictions_technical,
                predictions_sentiment,
                predictions_fundamental
            ], axis=1)
            ```
        *   Das resultierende `X_meta`-Array hat die Shape `(Anzahl_Samples, 3 * k)`.

    3.  **Skalierung:**
        *   Normalerweise **nicht notwendig**. Da alle drei Inputs Prognosen derselben Zielgröße (prozentuale Veränderung) sind, befinden sie sich bereits in einem vergleichbaren Wertebereich. Eine Skalierung würde die relative Sicherheit oder das Ausmaß der einzelnen Experten-Prognosen verzerren.

    4.  **Sequenzierung:**
        *   **Nicht notwendig.** Der Input für das Meta-Modell ist bereits ein flacher Vektor pro Vorhersage. Es wird nicht mehr mit Zeitsequenzen gearbeitet, sondern nur noch mit den Prognosen für einen bestimmten Zeitpunkt.
