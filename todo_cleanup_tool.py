#!/usr/bin/env python3
"""
Intelligentes TODO/FIXME Cleanup Tool
Kategorisiert und bearbeitet TODO-Kommentare basierend auf Typ und Komplexität
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import argparse

class TodoType(Enum):
    """Kategorien von TODO-Kommentaren"""
    SIMPLE_FIX = "simple_fix"          # Einfache Fixes (Kommentare, kleine Änderungen)
    IMPLEMENTATION = "implementation"   # Fehlende Implementierungen
    OPTIMIZATION = "optimization"       # Performance-Verbesserungen
    TESTING = "testing"                # Tests hinzufügen
    DOCUMENTATION = "documentation"     # Dokumentation verbessern
    REFACTORING = "refactoring"        # Code-Refactoring
    FEATURE = "feature"                # Neue Features
    BUG_FIX = "bug_fix"               # Bug-Fixes
    SECURITY = "security"              # Sicherheitsverbesserungen
    UNKNOWN = "unknown"                # Unkategorisiert

@dataclass
class TodoItem:
    """Einzelner TODO-Kommentar"""
    file_path: Path
    line_number: int
    line_content: str
    todo_text: str
    todo_type: TodoType
    priority: int  # 1=hoch, 2=mittel, 3=niedrig
    estimated_effort: int  # Minuten

class TodoAnalyzer:
    """Analysiert und kategorisiert TODO-Kommentare"""
    
    # Patterns für verschiedene TODO-Typen
    PATTERNS = {
        TodoType.SIMPLE_FIX: [
            r'add.*comment', r'fix.*comment', r'remove.*debug', r'clean.*up',
            r'format.*code', r'rename.*variable', r'typo', r'spelling'
        ],
        TodoType.IMPLEMENTATION: [
            r'implement', r'add.*method', r'create.*class', r'finish.*function',
            r'complete.*implementation', r'missing.*implementation'
        ],
        TodoType.OPTIMIZATION: [
            r'optimize', r'performance', r'faster', r'cache', r'efficiency',
            r'memory.*leak', r'slow.*query'
        ],
        TodoType.TESTING: [
            r'test', r'unittest', r'coverage', r'mock', r'assert',
            r'test.*case', r'integration.*test'
        ],
        TodoType.DOCUMENTATION: [
            r'document', r'docstring', r'readme', r'comment.*explain',
            r'api.*doc', r'help.*text'
        ],
        TodoType.REFACTORING: [
            r'refactor', r'restructure', r'reorganize', r'clean.*architecture',
            r'extract.*method', r'split.*class'
        ],
        TodoType.BUG_FIX: [
            r'fix.*bug', r'bug', r'error.*handling', r'exception',
            r'crash', r'fix.*issue'
        ],
        TodoType.SECURITY: [
            r'security', r'vulnerability', r'sanitize', r'validate.*input',
            r'encrypt', r'authentication'
        ]
    }
    
    def __init__(self):
        self.todos: List[TodoItem] = []
    
    def analyze_file(self, file_path: Path) -> List[TodoItem]:
        """Analysiert eine Datei nach TODO-Kommentaren"""
        file_todos = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if self._contains_todo(line):
                    todo_text = self._extract_todo_text(line)
                    todo_type = self._categorize_todo(todo_text)
                    priority = self._estimate_priority(todo_text, todo_type)
                    effort = self._estimate_effort(todo_text, todo_type)
                    
                    todo_item = TodoItem(
                        file_path=file_path,
                        line_number=line_num,
                        line_content=line.strip(),
                        todo_text=todo_text,
                        todo_type=todo_type,
                        priority=priority,
                        estimated_effort=effort
                    )
                    file_todos.append(todo_item)
                    
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return file_todos
    
    def _contains_todo(self, line: str) -> bool:
        """Prüft ob eine Zeile TODO-Kommentare enthält"""
        return bool(re.search(r'(TODO|FIXME|XXX|HACK)', line, re.IGNORECASE))
    
    def _extract_todo_text(self, line: str) -> str:
        """Extrahiert den TODO-Text aus einer Zeile"""
        match = re.search(r'(TODO|FIXME|XXX|HACK)[:]*\s*(.*)', line, re.IGNORECASE)
        if match:
            return match.group(2).strip()
        return line.strip()
    
    def _categorize_todo(self, todo_text: str) -> TodoType:
        """Kategorisiert einen TODO-Kommentar"""
        todo_lower = todo_text.lower()
        
        for todo_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, todo_lower):
                    return todo_type
        
        return TodoType.UNKNOWN
    
    def _estimate_priority(self, todo_text: str, todo_type: TodoType) -> int:
        """Schätzt die Priorität eines TODOs (1=hoch, 3=niedrig)"""
        todo_lower = todo_text.lower()
        
        # Hohe Priorität: Security, Bugs, kritische Implementierungen
        if todo_type in [TodoType.SECURITY, TodoType.BUG_FIX]:
            return 1
        if 'critical' in todo_lower or 'important' in todo_lower or 'urgent' in todo_lower:
            return 1
            
        # Mittlere Priorität: Implementierungen, Tests
        if todo_type in [TodoType.IMPLEMENTATION, TodoType.TESTING]:
            return 2
            
        # Niedrige Priorität: Dokumentation, Optimierung
        return 3
    
    def _estimate_effort(self, todo_text: str, todo_type: TodoType) -> int:
        """Schätzt den Aufwand in Minuten"""
        effort_map = {
            TodoType.SIMPLE_FIX: 5,
            TodoType.DOCUMENTATION: 10,
            TodoType.BUG_FIX: 15,
            TodoType.TESTING: 20,
            TodoType.OPTIMIZATION: 30,
            TodoType.IMPLEMENTATION: 45,
            TodoType.REFACTORING: 60,
            TodoType.FEATURE: 120,
            TodoType.SECURITY: 90,
            TodoType.UNKNOWN: 15
        }
        return effort_map.get(todo_type, 15)
    
    def analyze_directory(self, directory: Path, exclude_dirs: List[str] = None) -> List[TodoItem]:
        """Analysiert alle Python-Dateien in einem Verzeichnis"""
        if exclude_dirs is None:
            exclude_dirs = ['venv', '__pycache__', '.git', 'node_modules', 'backups']
        
        all_todos = []
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        for file_path in python_files:
            file_todos = self.analyze_file(file_path)
            all_todos.extend(file_todos)
        
        self.todos = all_todos
        return all_todos
    
    def generate_report(self) -> Dict:
        """Generiert einen Analysebericht"""
        if not self.todos:
            return {"error": "No TODOs analyzed"}
        
        # Statistiken nach Typ
        type_stats = {}
        for todo in self.todos:
            todo_type = todo.todo_type.value
            if todo_type not in type_stats:
                type_stats[todo_type] = {"count": 0, "effort": 0}
            type_stats[todo_type]["count"] += 1
            type_stats[todo_type]["effort"] += todo.estimated_effort
        
        # Prioritäts-Statistiken
        priority_stats = {1: 0, 2: 0, 3: 0}
        for todo in self.todos:
            priority_stats[todo.priority] += 1
        
        # Top-Dateien mit meisten TODOs
        file_stats = {}
        for todo in self.todos:
            file_path = str(todo.file_path)
            if file_path not in file_stats:
                file_stats[file_path] = 0
            file_stats[file_path] += 1
        
        top_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_todos": len(self.todos),
            "by_type": type_stats,
            "by_priority": priority_stats,
            "estimated_total_effort_hours": sum(t.estimated_effort for t in self.todos) / 60,
            "top_files": top_files,
            "quick_wins": [t for t in self.todos if t.estimated_effort <= 10 and t.priority <= 2]
        }
    
    def get_actionable_todos(self, max_effort: int = 15, max_priority: int = 2) -> List[TodoItem]:
        """Gibt actionable TODOs zurück (niedrig Aufwand, hohe Priorität)"""
        return [
            todo for todo in self.todos
            if todo.estimated_effort <= max_effort and todo.priority <= max_priority
        ]


def main():
    parser = argparse.ArgumentParser(description='Analyze TODO/FIXME comments')
    parser.add_argument('path', help='Path to directory or file to analyze')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--actionable', action='store_true', help='Show actionable TODOs only')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path {path} does not exist")
        return 1
    
    analyzer = TodoAnalyzer()
    
    if path.is_file():
        todos = analyzer.analyze_file(path)
    else:
        todos = analyzer.analyze_directory(path)
    
    if args.report:
        report = analyzer.generate_report()
        
        print("TODO/FIXME Analysis Report")
        print("=" * 50)
        print(f"Total TODOs: {report['total_todos']}")
        print(f"Estimated effort: {report['estimated_total_effort_hours']:.1f} hours")
        print()
        
        print("By Type:")
        for todo_type, stats in report['by_type'].items():
            print(f"  {todo_type}: {stats['count']} items ({stats['effort']} min)")
        
        print(f"\nBy Priority:")
        print(f"  High (1): {report['by_priority'][1]} items")
        print(f"  Medium (2): {report['by_priority'][2]} items") 
        print(f"  Low (3): {report['by_priority'][3]} items")
        
        print(f"\nQuick wins (≤10 min, priority ≤2): {len(report['quick_wins'])} items")
    
    elif args.actionable:
        actionable = analyzer.get_actionable_todos()
        print(f"Actionable TODOs (≤15 min effort, priority ≤2): {len(actionable)} items")
        print()
        
        for todo in actionable[:20]:  # Top 20
            print(f"{todo.file_path}:{todo.line_number}")
            print(f"  Type: {todo.todo_type.value}, Priority: {todo.priority}, Effort: {todo.estimated_effort}min")
            print(f"  TODO: {todo.todo_text}")
            print()
    
    else:
        print(f"Found {len(todos)} TODO/FIXME comments")
        print("Use --report for detailed analysis or --actionable for quick wins")
    
    return 0


if __name__ == "__main__":
    exit(main())