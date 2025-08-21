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
