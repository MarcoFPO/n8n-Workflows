#!/usr/bin/env python3
"""
Duplicate Prevention Tool für ki_recommendations Datenbank
Stellt sicher, dass keine Duplikate in der Datenbank entstehen
"""

import sqlite3
from datetime import datetime
import sys

class DuplicatePrevention:
    """Tool zur Duplikatsvermeidung"""
    
    def __init__(self, db_path="/opt/aktienanalyse-ökosystem/data/ki_recommendations.db"):
        self.db_path = db_path
    
    def check_duplicates(self) -> dict:
        """Prüfe auf Duplikate in der Datenbank"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prüfe Duplikate für heute
            cursor.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM ki_recommendations 
                WHERE DATE(created_at) = DATE('now')
                GROUP BY symbol 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """)
            
            duplicates = cursor.fetchall()
            
            # Gesamtstatistik für heute
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM ki_recommendations 
                WHERE DATE(created_at) = DATE('now')
            """)
            
            total_entries, unique_symbols = cursor.fetchone()
            conn.close()
            
            return {
                "duplicates": duplicates,
                "total_entries": total_entries,
                "unique_symbols": unique_symbols,
                "has_duplicates": len(duplicates) > 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def remove_duplicates(self, keep_latest=True) -> dict:
        """Entferne Duplikate aus der Datenbank"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if keep_latest:
                # Behalte nur den neuesten Eintrag pro Symbol für heute
                cursor.execute("""
                    DELETE FROM ki_recommendations 
                    WHERE id NOT IN (
                        SELECT MAX(id)
                        FROM ki_recommendations 
                        WHERE DATE(created_at) = DATE('now')
                        GROUP BY symbol
                    ) AND DATE(created_at) = DATE('now')
                """)
            else:
                # Lösche alle heutigen Einträge und starte neu
                cursor.execute("DELETE FROM ki_recommendations WHERE DATE(created_at) = DATE('now')")
            
            removed_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return {
                "removed_count": removed_count,
                "strategy": "keep_latest" if keep_latest else "remove_all"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def enforce_unique_constraint(self) -> dict:
        """Stelle sicher, dass pro Symbol pro Tag nur ein Eintrag existiert"""
        check_result = self.check_duplicates()
        
        if check_result.get("has_duplicates", False):
            print(f"⚠️ Found duplicates for symbols: {[dup[0] for dup in check_result['duplicates']]}")
            
            # Automatisch die neuesten behalten
            removal_result = self.remove_duplicates(keep_latest=True)
            
            if "error" not in removal_result:
                print(f"✅ Removed {removal_result['removed_count']} duplicate entries")
                
                # Erneut prüfen
                final_check = self.check_duplicates()
                return {
                    "action": "duplicates_removed",
                    "removed_count": removal_result["removed_count"],
                    "final_status": final_check
                }
            else:
                return {"error": f"Failed to remove duplicates: {removal_result['error']}"}
        else:
            return {
                "action": "no_duplicates_found",
                "status": check_result
            }

def main():
    """CLI Interface"""
    dp = DuplicatePrevention()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            result = dp.check_duplicates()
            if "error" not in result:
                if result["has_duplicates"]:
                    print(f"❌ DUPLICATES FOUND:")
                    for symbol, count in result["duplicates"]:
                        print(f"  {symbol}: {count} entries")
                    print(f"Total: {result['total_entries']} entries, {result['unique_symbols']} unique symbols")
                else:
                    print(f"✅ NO DUPLICATES - {result['total_entries']} entries, {result['unique_symbols']} unique symbols")
            else:
                print(f"❌ Error: {result['error']}")
                
        elif command == "fix":
            result = dp.enforce_unique_constraint()
            print(f"Action: {result['action']}")
            if "removed_count" in result:
                print(f"Removed: {result['removed_count']} duplicates")
                
        elif command == "remove-all":
            result = dp.remove_duplicates(keep_latest=False)
            if "error" not in result:
                print(f"✅ Removed all {result['removed_count']} entries for today")
            else:
                print(f"❌ Error: {result['error']}")
        else:
            print("Unknown command. Available: check, fix, remove-all")
    else:
        # Default: Check und automatisch fixen
        result = dp.enforce_unique_constraint()
        if result["action"] == "duplicates_removed":
            print(f"✅ Fixed duplicates - removed {result['removed_count']} entries")
        else:
            print("✅ No duplicates found")

if __name__ == "__main__":
    main()