#!/bin/bash
# Beispiel-Script für Modul-Umbenennung mit Versioning

# Variablen
OLD_FILE="order_execution_module.py"
NEW_VERSION="1.3.3"
DATE=$(date +%Y%m%d)
MODULE_NAME="order_execution_module"
UPGRADE_DESC="Fixed timeout handling in order execution"

# Neuer Dateiname
NEW_FILE="${MODULE_NAME}_v${NEW_VERSION}_${DATE}.py"

echo "🔄 Umbenennung: $OLD_FILE → $NEW_FILE"

# 1. Datei umbenennen
if [ -f "$OLD_FILE" ]; then
    mv "$OLD_FILE" "$NEW_FILE"
    echo "✅ Datei umbenannt"
else
    echo "❌ Datei $OLD_FILE nicht gefunden"
    exit 1
fi

# 2. Release Register aktualisieren
echo "📋 Aktualisiere Release Register..."
sed -i "s/| \*\*${MODULE_NAME}\*\* | v.* | .* | .* | ✅ AKTIV |/| **${MODULE_NAME}** | v${NEW_VERSION} | ${DATE:0:4}-${DATE:4:2}-${DATE:6:2} | ${UPGRADE_DESC} | ✅ AKTIV |/" MODUL_RELEASE_REGISTER.md

# 3. Imports suchen und aktualisieren
echo "🔍 Suche nach Import-Statements..."
grep -r "from.*${MODULE_NAME}" . --include="*.py" | grep -v "$NEW_FILE" | while read line; do
    file=$(echo $line | cut -d: -f1)
    echo "⚠️  Import gefunden in: $file"
    echo "   Bitte manuell aktualisieren: $line"
done

echo "✅ Umbenennung abgeschlossen!"
echo "📝 Nächste Schritte:"
echo "   1. Imports in anderen Dateien aktualisieren"
echo "   2. Git commit mit: git commit -m 'feat: ${MODULE_NAME} v${NEW_VERSION} - ${UPGRADE_DESC}'"
echo "   3. Release Register Änderungen committen"