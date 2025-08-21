#!/usr/bin/env python3
"""
Script zur Erweiterung des Dashboards um Pipeline-Monitoring
"""

import re

def add_pipeline_dashboard():
    """Fügt Pipeline-Monitoring zum Dashboard hinzu"""
    
    frontend_file = "/opt/aktienanalyse-ökosystem/services/frontend-service-modular/frontend_service_v7_0_1_20250816.py"
    
    # Read the current file
    with open(frontend_file, 'r') as f:
        content = f.read()
    
    # Finde die Dashboard-Content Funktion und erweitere sie
    dashboard_extension = '''
        # Pipeline Status Widget
        pipeline_widget = ""
        try:
            # Fetch pipeline status
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8080/api/content/pipeline-status") as response:
                    if response.status == 200:
                        pipeline_data = await response.json()
                        
                        # Pipeline Status Card
                        if pipeline_data.get("pipeline_script_exists"):
                            if pipeline_data.get("last_execution"):
                                pipeline_status = f'<span class="badge bg-success">Aktiv</span><br><small>Letzte Ausführung: {pipeline_data["last_execution"]}</small>'
                                pipeline_icon = "fas fa-cogs text-success"
                            else:
                                pipeline_status = '<span class="badge bg-warning">Bereit</span><br><small>Noch nicht ausgeführt</small>'
                                pipeline_icon = "fas fa-cogs text-warning"
                        else:
                            pipeline_status = '<span class="badge bg-danger">Nicht verfügbar</span>'
                            pipeline_icon = "fas fa-exclamation-triangle text-danger"
                        
                        # Cron Status
                        cron_status = pipeline_data.get("cron_status", "unknown")
                        if cron_status == "active":
                            cron_badge = '<span class="badge bg-success">Aktiv</span>'
                        elif cron_status == "inactive":
                            cron_badge = '<span class="badge bg-warning">Inaktiv</span>'
                        else:
                            cron_badge = '<span class="badge bg-danger">Fehler</span>'
                        
                        # Recent Predictions
                        predictions_count = pipeline_data.get("recent_predictions", 0)
                        if predictions_count > 10:
                            predictions_badge = f'<span class="badge bg-success">{predictions_count} Vorhersagen heute</span>'
                        elif predictions_count > 0:
                            predictions_badge = f'<span class="badge bg-warning">{predictions_count} Vorhersagen heute</span>'
                        else:
                            predictions_badge = '<span class="badge bg-danger">Keine Vorhersagen heute</span>'
                        
                        pipeline_widget = f"""
                        <div class="col-md-6 mb-3">
                            <div class="card status-card status-healthy">
                                <div class="card-body">
                                    <h6 class="card-title">
                                        <i class="{pipeline_icon}"></i> Pipeline Automation
                                    </h6>
                                    <p class="card-text">{pipeline_status}</p>
                                    <div class="mt-2">
                                        <strong>Cron Jobs:</strong> {cron_badge}<br>
                                        <strong>Predictions:</strong> {predictions_badge}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """
                    else:
                        pipeline_widget = f"""
                        <div class="col-md-6 mb-3">
                            <div class="card status-card status-error">
                                <div class="card-body">
                                    <h6 class="card-title">
                                        <i class="fas fa-exclamation-triangle text-danger"></i> Pipeline Status
                                    </h6>
                                    <p class="card-text"><span class="badge bg-danger">API Fehler</span></p>
                                </div>
                            </div>
                        </div>
                        """
        except Exception as e:
            pipeline_widget = f"""
            <div class="col-md-6 mb-3">
                <div class="card status-card status-error">
                    <div class="card-body">
                        <h6 class="card-title">
                            <i class="fas fa-times-circle text-danger"></i> Pipeline Status
                        </h6>
                        <p class="card-text"><span class="badge bg-danger">Fehler: {str(e)[:50]}</span></p>
                    </div>
                </div>
            </div>
            """
'''
    
    # Finde den Bereich nach status_cards und füge pipeline_widget hinzu
    pattern = r'(status_cards \+= f""".*?</div>\s*""".*?)(return f""")'
    
    replacement = r'''\\1
        
        # Add pipeline widget to status cards
        status_cards += pipeline_widget
''' + dashboard_extension + r'''
        
        \\2'''
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write back the modified content
    with open(frontend_file, 'w') as f:
        f.write(content)
    
    print("✅ Dashboard pipeline monitoring added successfully")

if __name__ == "__main__":
    add_pipeline_dashboard()