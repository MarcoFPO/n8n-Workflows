# Implementierungsanleitung: osTicket Custom Fields Einrichtung

**Datum:** 2025-10-26
**Version:** 1.0
**Zweck:** Schritt-für-Schritt Anleitung zum Anlegen der Custom Fields in osTicket
**Zielgruppe:** osTicket Administratoren

---

## Übersicht

Für die Zabbix-osTicket Integration benötigen Sie **4 Custom Fields** in osTicket:

| Nr. | Feldname | Typ | Zweck | Status |
|-----|----------|-----|-------|--------|
| 1 | `root_ticket` | Link to Ticket | Verknüpfung zu Parent-Ticket | Phase 2 |
| 2 | `ursache` | Text (Textarea) | Ursachenanalyse | Phase 2 |
| 3 | `lösung` | Text (Textarea) | Lösungsmaßnahme | Phase 2 |
| 4 | `störungsende` | Date & Time | Problem-Endzeitpunkt | Phase 2 |

**Hinweis:** Diese Fields werden aktuell **NICHT** von der Zabbix-Integration gefüllt. Sie sind für zukünftige Phasen reserviert.

---

## Voraussetzungen

- osTicket 1.10+ (Custom Fields unterstützt)
- Admin-Zugriff auf osTicket
- MySQL/MariaDB Zugriff (für direktes Editing, falls nötig)

---

## Schritt 1: osTicket Admin Panel öffnen

1. Melden Sie sich als Admin in osTicket an
2. Gehen Sie zu: **Admin Panel → Manage → Custom Fields**

**URL:** `https://osticket.example.com/admin/forms.php`

---

## Schritt 2: Custom Field 1 - `root_ticket` (Verknüpfung)

### 2.1 Klicken Sie auf "Add New Custom Field"

### 2.2 Füllen Sie folgende Felder aus:

| Feld | Wert |
|------|------|
| **Label** | `Root Ticket` |
| **Name** | `root_ticket` |
| **Type** | `Link to Ticket` |
| **Required** | ❌ Nein (unchecked) |
| **Visibility** | `Admin Only` |
| **Searchable** | ☑️ Ja |
| **Description** | `Verknüpfung zu Parent-Ticket bei zusammenhängenden Problemen. Wird für Phase 2 genutzt.` |

### 2.3 Speichern

- Klicken Sie **Save** am Ende der Form
- Bestätigen Sie die Nachricht "Custom field added successfully"

---

## Schritt 3: Custom Field 2 - `ursache` (Ursachenanalyse)

### 3.1 Klicken Sie auf "Add New Custom Field"

### 3.2 Füllen Sie folgende Felder aus:

| Feld | Wert |
|------|------|
| **Label** | `Ursache` |
| **Name** | `ursache` |
| **Type** | `Text` |
| **Text Area** | ☑️ Ja (verwandelt es in Textarea) |
| **Max Length** | `1000` (mindestens 256) |
| **Required** | ❌ Nein (unchecked) |
| **Visibility** | `Public` |
| **Searchable** | ☑️ Ja |
| **Description** | `Ursachenanalyse des Zabbix-Problems. Wird vom Support manuell ausgefüllt.` |

### 3.3 Speichern

- Klicken Sie **Save**
- Bestätigen Sie die Nachricht "Custom field added successfully"

---

## Schritt 4: Custom Field 3 - `lösung` (Lösungsmaßnahme)

### 4.1 Klicken Sie auf "Add New Custom Field"

### 4.2 Füllen Sie folgende Felder aus:

| Feld | Wert |
|------|------|
| **Label** | `Lösung` |
| **Name** | `lösung` |
| **Type** | `Text` |
| **Text Area** | ☑️ Ja (verwandelt es in Textarea) |
| **Max Length** | `1000` (mindestens 256) |
| **Required** | ❌ Nein (unchecked) |
| **Visibility** | `Public` |
| **Searchable** | ☑️ Ja |
| **Description** | `Durchgeführte Lösungsmaßnahme zur Behebung des Problems. Wird vom Support oder via Recovery gefüllt.` |

### 4.3 Speichern

- Klicken Sie **Save**
- Bestätigen Sie die Nachricht "Custom field added successfully"

---

## Schritt 5: Custom Field 4 - `störungsende` (Endzeitpunkt)

### 5.1 Klicken Sie auf "Add New Custom Field"

### 5.2 Füllen Sie folgende Felder aus:

| Feld | Wert |
|------|------|
| **Label** | `Störungsende` |
| **Name** | `störungsende` |
| **Type** | `Date & Time` |
| **Required** | ❌ Nein (unchecked) |
| **Visibility** | `Public` |
| **Searchable** | ☑️ Ja |
| **Description** | `Zeitstempel wenn das Problem behoben wurde. Format: DD.MM.YYYY HH:MM:SS. Wird manuell oder via Zabbix-Recovery gefüllt.` |

### 5.3 Speichern

- Klicken Sie **Save**
- Bestätigen Sie die Nachricht "Custom field added successfully"

---

## Schritt 6: Verifikation der Custom Fields

### 6.1 Überprüfen Sie in der Custom Fields Liste

Gehen Sie zu: **Admin Panel → Manage → Custom Fields**

Sie sollten jetzt alle 4 Fields sehen:

```
✅ Root Ticket (Link to Ticket, Admin Only)
✅ Ursache (Text, Public)
✅ Lösung (Text, Public)
✅ Störungsende (Date & Time, Public)
```

### 6.2 Überprüfen Sie, ob Fields in Ticket-Form angezeigt werden

1. Gehen Sie zu: **Admin Panel → Manage → Forms**
2. Öffnen Sie das Form **"Ticket"** (oder das Standard-Ticket-Form)
3. Scrollen Sie nach unten in **Fields**
4. Überprüfen Sie, dass die 4 neuen Custom Fields sichtbar sind

Falls nicht sichtbar:
1. Klicken Sie **Edit** auf das Form
2. Suchen Sie unter **Available Fields** nach den Custom Fields
3. Klicken Sie auf **Add** für jedes Custom Field
4. Klicken Sie **Save**

### 6.3 Test-Ticket erstellen

1. Gehen Sie zu: **Support → Open a New Ticket**
2. Füllen Sie die Standard-Felder aus (Name, Email, Subject, Message)
3. Scrollen Sie nach unten
4. Überprüfen Sie, dass Sie die 4 neuen Custom Fields sehen:
   - [ ] Root Ticket (Dropdown/Link)
   - [ ] Ursache (Textarea)
   - [ ] Lösung (Textarea)
   - [ ] Störungsende (Datum/Zeit Picker)
5. Klicken Sie **Create Ticket**

---

## Schritt 7: Datenbank-Überprüfung (Optional)

Falls Sie direkten Datenbank-Zugriff haben, können Sie die Fields auch dort überprüfen:

### 7.1 SSH auf osTicket Server

```bash
ssh admin@osticket.example.com
```

### 7.2 MySQL-Verbindung

```bash
mysql -u osticket_user -p osticket_db
```

### 7.3 Überprüfen Sie die Custom Fields

```sql
SELECT * FROM ost_form_field WHERE name IN ('root_ticket', 'ursache', 'lösung', 'störungsende');
```

Erwartetes Ergebnis (4 Rows):
```
+----+---------+---------------+------+-------+
| id | name    | label         | type | ... |
+----+---------+---------------+------+-------+
| 25 | root_ticket | Root Ticket | custom | ... |
| 26 | ursache | Ursache | custom | ... |
| 27 | lösung  | Lösung        | custom | ... |
| 28 | störungsende | Störungsende | custom | ... |
+----+---------+---------------+------+-------+
```

---

## Schritt 8: osTicket API Key erstellen (falls noch nicht vorhanden)

Die Zabbix-Webhook-Integration benötigt einen osTicket API Key.

### 8.1 Gehen Sie zu Admin Panel

**Admin Panel → Manage → API Keys**

### 8.2 Erstellen Sie einen neuen API Key

1. Klicken Sie **Add API Key**
2. Füllen Sie aus:

| Feld | Wert |
|------|------|
| **Key** | (wird automatisch generiert) |
| **URL** | `https://osticket.example.com` |
| **Status** | `Active` |
| **Can Create Tickets** | ☑️ Ja |
| **Can Update Tickets** | ☑️ Ja (für Phase 2) |
| **Note** | `Zabbix Webhook Integration` |

3. Klicken Sie **Save**

### 8.3 Kopieren Sie den API Key

Der generierte Key wird angezeigt. Kopieren Sie ihn und speichern Sie ihn sicher:

```
API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Dieser Key wird später in der Zabbix/n8n Konfiguration benötigt!**

---

## Schritt 9: Troubleshooting

### Problem: Custom Fields sind nicht sichtbar im Form

**Lösung:**
1. Gehen Sie zu: **Admin Panel → Manage → Forms**
2. Öffnen Sie das Ticket-Form
3. Klicken Sie **Edit**
4. Scrollen Sie zu **Available Fields**
5. Suchen Sie die Custom Fields
6. Klicken Sie **Add** für jedes Field
7. Klicken Sie **Save**

### Problem: Custom Fields können nicht gelöscht werden

**Grund:** Sie sind bereits in Tickets verwendet.

**Lösung:** Verwenden Sie die Option **Disable** statt **Delete** (falls verfügbar)

### Problem: Field ist nicht im API verfügbar

**Grund:** osTicket Version zu alt oder Field nicht ordnungsgemäß erstellt.

**Lösung:**
- Überprüfen Sie osTicket Version (1.10+)
- Stellen Sie sicher, dass Field **Active** ist
- Überprüfen Sie in Datenbank, dass es einen gültigen Eintrag gibt

---

## Schritt 10: Production Checklist

- [ ] Custom Field `root_ticket` angelegt (Link to Ticket, Admin Only)
- [ ] Custom Field `ursache` angelegt (Text 1000 chars, Public)
- [ ] Custom Field `lösung` angelegt (Text 1000 chars, Public)
- [ ] Custom Field `störungsende` angelegt (DateTime, Public)
- [ ] Alle 4 Fields sind in der Custom Fields Liste sichtbar
- [ ] Alle 4 Fields sind im Ticket-Form sichtbar
- [ ] Test-Ticket erstellt und Fields überprüft
- [ ] osTicket API Key generiert und sicher gespeichert
- [ ] Datenbank überprüft (optional)

---

## Best Practices

### 1. Naming Convention
- Verwenden Sie **lowercase** für Field-Names (`root_ticket`, nicht `RootTicket`)
- Verwenden Sie **Umlaute** im Label (sichtbar für User): `Ursache`, `Lösung`, `Störungsende`

### 2. Visibility
- `root_ticket`: Admin Only (zu technisch für Enduser)
- `ursache`, `lösung`, `störungsende`: Public (User sollen sehen können)

### 3. Required Flag
- Alle 4 Fields sind **optional** (werden nicht von aktueller Integration gefüllt)
- Zukünftig könnten Sie einige auf **Required** setzen

### 4. Sicherung
- Sichern Sie regelmäßig Ihre osTicket Datenbank
- Custom Fields sind Teil der Datenbank

---

## Nächste Schritte

Nach der osTicket Custom Fields Einrichtung:

1. **Zabbix Webhook** → Siehe `IMPLEMENTATION_ZABBIX_WEBHOOK.md`
2. **n8n Workflow** → Siehe `IMPLEMENTATION_N8N_WORKFLOW.md`
3. **End-to-End Test** → Vollständigen Flow testen

---

**Dokument Ende**
