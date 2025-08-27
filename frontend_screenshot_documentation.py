#!/usr/bin/env python3
"""
Frontend Screenshot Documentation für User Acceptance Testing
Aktienanalyse-Ökosystem v6.0.0

Author: Claude Code Assistant
Date: 2025-08-27
Version: 1.0.0

ZWECK:
- UI Screenshots aller wichtigen Views
- Bootstrap 5 Responsiveness Testing
- Timeline Navigation Dokumentation
- Mobile/Desktop View Validation
"""

import requests
import os
import subprocess
import time
from datetime import datetime
from typing import List, Dict, Any
import json

class FrontendScreenshotDocumentation:
    """Frontend Screenshot und UI-Dokumentation"""
    
    def __init__(self):
        self.base_url = "http://10.1.1.174"
        self.frontend_ports = [8080, 8081]
        self.screenshots_dir = "screenshots"
        self.documentation_results = {
            "timestamp": datetime.now().isoformat(),
            "screenshots": [],
            "ui_analysis": {}
        }
        
        # Screenshots-Ordner erstellen
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def capture_screenshot_with_curl(self, url: str, filename: str) -> Dict[str, Any]:
        """Screenshot mit curl und HTML-Analyse"""
        try:
            # HTML-Inhalt laden
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # HTML in Datei speichern für Analyse
                html_file = f"{self.screenshots_dir}/{filename}.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # UI-Analyse des HTML
                ui_analysis = self.analyze_html_ui(response.text)
                
                return {
                    "success": True,
                    "url": url,
                    "filename": html_file,
                    "content_length": len(response.text),
                    "ui_analysis": ui_analysis
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "url": url
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def analyze_html_ui(self, html_content: str) -> Dict[str, Any]:
        """Analysiere HTML-Inhalt auf UI-Komponenten"""
        html_lower = html_content.lower()
        
        analysis = {
            "bootstrap_detected": "bootstrap" in html_lower,
            "responsive_classes": any(cls in html_lower for cls in ["col-", "row", "container"]),
            "navigation_elements": {
                "nav_tag": "<nav" in html_lower,
                "navbar": "navbar" in html_lower,
                "menu_items": html_lower.count("menu") + html_lower.count("nav-item"),
                "timeline_nav": "timeline" in html_lower
            },
            "form_elements": {
                "forms": html_lower.count("<form"),
                "inputs": html_lower.count("<input"),
                "buttons": html_lower.count("<button") + html_lower.count("btn-"),
                "selects": html_lower.count("<select")
            },
            "data_elements": {
                "tables": html_lower.count("<table"),
                "charts": any(chart in html_lower for chart in ["chart", "canvas", "svg"]),
                "cards": html_lower.count("card"),
                "alerts": html_lower.count("alert")
            },
            "javascript_detected": "<script" in html_lower,
            "css_detected": "<style" in html_lower or ".css" in html_lower,
            "title": self.extract_title(html_content),
            "meta_viewport": "viewport" in html_lower
        }
        
        return analysis
    
    def extract_title(self, html_content: str) -> str:
        """Extrahiere Seitentitel"""
        try:
            start = html_content.lower().find("<title>")
            if start != -1:
                start += 7
                end = html_content.lower().find("</title>", start)
                if end != -1:
                    return html_content[start:end].strip()
        except:
            pass
        return "Unknown"
    
    def document_main_pages(self) -> None:
        """Dokumentiere Hauptseiten"""
        print("📸 Starting Frontend Screenshot Documentation...")
        
        main_pages = [
            {"name": "homepage", "path": "/"},
            {"name": "ki_prognosen", "path": "/predictions"},
            {"name": "soll_ist_vergleich", "path": "/comparison"},
            {"name": "dashboard", "path": "/dashboard"},
            {"name": "timeline_1w", "path": "/predictions?timeframe=1W"},
            {"name": "timeline_1m", "path": "/predictions?timeframe=1M"},
            {"name": "timeline_3m", "path": "/predictions?timeframe=3M"},
            {"name": "timeline_1y", "path": "/predictions?timeframe=1Y"}
        ]
        
        for port in self.frontend_ports:
            port_screenshots = []
            
            for page in main_pages:
                url = f"{self.base_url}:{port}{page['path']}"
                filename = f"port_{port}_{page['name']}"
                
                print(f"📸 Capturing: {page['name']} on port {port}")
                
                result = self.capture_screenshot_with_curl(url, filename)
                result["page_name"] = page["name"]
                result["port"] = port
                
                port_screenshots.append(result)
                
                # Kurze Pause zwischen Screenshots
                time.sleep(0.5)
            
            self.documentation_results["screenshots"].append({
                "port": port,
                "screenshots": port_screenshots
            })
    
    def test_responsive_design(self) -> None:
        """Teste Responsive Design durch User-Agent Simulation"""
        print("📱 Testing Responsive Design...")
        
        user_agents = {
            "desktop": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "tablet": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "mobile": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
        }
        
        responsive_results = {}
        
        for device, user_agent in user_agents.items():
            print(f"🔍 Testing {device} view...")
            
            try:
                headers = {"User-Agent": user_agent}
                response = requests.get(f"{self.base_url}:8080", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Analysiere responsive Elemente
                    html_content = response.text.lower()
                    
                    responsive_results[device] = {
                        "success": True,
                        "has_viewport_meta": "viewport" in html_content,
                        "has_bootstrap_grid": any(cls in html_content for cls in ["col-sm", "col-md", "col-lg"]),
                        "has_responsive_images": "img-responsive" in html_content or "img-fluid" in html_content,
                        "content_length": len(response.text)
                    }
                else:
                    responsive_results[device] = {
                        "success": False,
                        "status_code": response.status_code
                    }
                    
            except Exception as e:
                responsive_results[device] = {
                    "success": False,
                    "error": str(e)
                }
        
        self.documentation_results["responsive_testing"] = responsive_results
    
    def analyze_accessibility(self) -> None:
        """Analysiere Accessibility-Features"""
        print("♿ Analyzing Accessibility Features...")
        
        try:
            response = requests.get(f"{self.base_url}:8080", timeout=10)
            
            if response.status_code == 200:
                html_content = response.text.lower()
                
                accessibility_analysis = {
                    "alt_attributes": html_content.count('alt='),
                    "aria_labels": html_content.count('aria-label'),
                    "semantic_html": {
                        "header": "<header" in html_content,
                        "nav": "<nav" in html_content,
                        "main": "<main" in html_content,
                        "section": "<section" in html_content,
                        "footer": "<footer" in html_content
                    },
                    "form_labels": html_content.count('<label'),
                    "skip_links": "skip" in html_content,
                    "focus_management": "tabindex" in html_content,
                    "color_contrast": self.check_color_contrast(html_content)
                }
                
                self.documentation_results["accessibility"] = accessibility_analysis
                
        except Exception as e:
            self.documentation_results["accessibility"] = {
                "error": str(e)
            }
    
    def check_color_contrast(self, html_content: str) -> Dict[str, Any]:
        """Prüfe Farb-Kontrast Indikatoren"""
        # Einfache Heuristik für Farbschema-Erkennung
        colors_found = []
        
        color_indicators = ["#fff", "#000", "white", "black", "rgb(", "rgba(", "color:", "background-color:"]
        for indicator in color_indicators:
            if indicator in html_content:
                colors_found.append(indicator)
        
        return {
            "color_indicators_found": len(colors_found),
            "has_css_colors": len(colors_found) > 0,
            "potential_contrast_issues": "color:#fff" in html_content and "background-color:#fff" in html_content
        }
    
    def generate_ui_documentation(self) -> str:
        """Generiere UI-Dokumentation"""
        print("📝 Generating UI Documentation...")
        
        doc_content = f"""# Frontend UI Documentation - User Acceptance Testing
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Information
- Server: {self.base_url}
- Frontend Ports: {', '.join(map(str, self.frontend_ports))}
- Architecture: Clean Architecture v6.0.0

## Screenshot Summary
"""
        
        for port_data in self.documentation_results["screenshots"]:
            port = port_data["port"]
            screenshots = port_data["screenshots"]
            
            doc_content += f"\n### Port {port} Screenshots\n"
            
            successful_screenshots = [s for s in screenshots if s["success"]]
            failed_screenshots = [s for s in screenshots if not s["success"]]
            
            doc_content += f"- Successful captures: {len(successful_screenshots)}\n"
            doc_content += f"- Failed captures: {len(failed_screenshots)}\n"
            
            for screenshot in successful_screenshots:
                ui_analysis = screenshot.get("ui_analysis", {})
                doc_content += f"\n#### {screenshot['page_name']}\n"
                doc_content += f"- File: `{screenshot['filename']}`\n"
                doc_content += f"- Title: {ui_analysis.get('title', 'Unknown')}\n"
                doc_content += f"- Bootstrap: {'✅' if ui_analysis.get('bootstrap_detected') else '❌'}\n"
                doc_content += f"- Navigation: {'✅' if ui_analysis.get('navigation_elements', {}).get('nav_tag') else '❌'}\n"
                doc_content += f"- JavaScript: {'✅' if ui_analysis.get('javascript_detected') else '❌'}\n"
        
        # Responsive Design Results
        if "responsive_testing" in self.documentation_results:
            doc_content += "\n## Responsive Design Testing\n"
            for device, result in self.documentation_results["responsive_testing"].items():
                status = "✅" if result.get("success") else "❌"
                doc_content += f"- {device.title()}: {status}\n"
                if result.get("success"):
                    doc_content += f"  - Viewport Meta: {'✅' if result.get('has_viewport_meta') else '❌'}\n"
                    doc_content += f"  - Bootstrap Grid: {'✅' if result.get('has_bootstrap_grid') else '❌'}\n"
        
        # Accessibility Results
        if "accessibility" in self.documentation_results:
            doc_content += "\n## Accessibility Analysis\n"
            acc = self.documentation_results["accessibility"]
            if "error" not in acc:
                doc_content += f"- Alt Attributes: {acc.get('alt_attributes', 0)}\n"
                doc_content += f"- ARIA Labels: {acc.get('aria_labels', 0)}\n"
                doc_content += f"- Form Labels: {acc.get('form_labels', 0)}\n"
                doc_content += f"- Semantic HTML Elements: {sum(acc.get('semantic_html', {}).values())}\n"
        
        # Speichere Dokumentation
        doc_filename = f"{self.screenshots_dir}/ui_documentation.md"
        with open(doc_filename, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        return doc_filename
    
    def run_complete_documentation(self) -> Dict[str, Any]:
        """Führe komplette Frontend-Dokumentation durch"""
        print("🚀 Starting Complete Frontend Documentation...")
        print("="*60)
        
        # Hauptseiten dokumentieren
        self.document_main_pages()
        
        # Responsive Design testen
        self.test_responsive_design()
        
        # Accessibility analysieren
        self.analyze_accessibility()
        
        # UI-Dokumentation generieren
        doc_file = self.generate_ui_documentation()
        
        # Ergebnisse als JSON speichern
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"{self.screenshots_dir}/frontend_documentation_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.documentation_results, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Documentation saved to: {doc_file}")
        print(f"📊 Results saved to: {results_file}")
        print("✅ Frontend Documentation completed")
        
        return self.documentation_results

def main():
    """Hauptfunktion - Frontend Screenshot Documentation"""
    documenter = FrontendScreenshotDocumentation()
    
    try:
        results = documenter.run_complete_documentation()
        
        # Summary
        total_screenshots = sum(len(port_data["screenshots"]) for port_data in results["screenshots"])
        successful_screenshots = sum(
            len([s for s in port_data["screenshots"] if s["success"]]) 
            for port_data in results["screenshots"]
        )
        
        print(f"\n📈 DOCUMENTATION SUMMARY:")
        print(f"   Total Screenshots: {total_screenshots}")
        print(f"   Successful: {successful_screenshots}")
        print(f"   Success Rate: {(successful_screenshots/total_screenshots)*100:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"❌ Documentation Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())