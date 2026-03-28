# High-Level Design: Ernährungs- und Gesundheits-App

## 1. SYSTEMARCHITEKTUR-DIAGRAMM

```
┌─────────────────────────────────────────────────────────────────┐
│                        LXC Container                             │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Layer                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Client    │  │   PWA Service   │  │  Static Assets  │ │
│  │ (HTML/CSS/JS)   │  │    Worker       │  │ (Bootstrap/     │ │
│  │   + Chart.js    │  │                 │  │  Chart.js)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Backend Layer                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 FastAPI Server                              │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│  │  │     API      │ │   ML Engine  │ │   External Services  │ │ │
│  │  │  Controllers │ │   (Recipe    │ │   Integration        │ │ │
│  │  │              │ │   Optimizer) │ │   (OCR/Vision APIs)  │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL Database                       │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │ │
│  │  │  Core Data   │ │ Health Data  │ │   Aldi Database      │ │ │
│  │  │ (Users/Prefs)│ │ (Vitals/     │ │   (Products/         │ │ │
│  │  │              │ │  Tracking)   │ │    Nutrition)        │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
              External KI Services (Internet)
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   OpenAI Vision │  │ Google Cloud    │  │   Aldi API      │
    │      API        │  │   Vision API    │  │   (optional)    │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 2. DATENMODELL

### 2.1 Core Entities

```sql
-- Benutzer
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Benutzereinstellungen
CREATE TABLE user_settings (
    user_id INTEGER REFERENCES users(id),
    daily_calorie_goal INTEGER NOT NULL,
    weight_goal DECIMAL(5,2),
    activity_level VARCHAR(20) DEFAULT 'moderate',
    dietary_restrictions TEXT[],
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id)
);

-- Aldi Produktdatenbank
CREATE TABLE aldi_products (
    id SERIAL PRIMARY KEY,
    barcode VARCHAR(50) UNIQUE,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(100),
    price_per_unit DECIMAL(8,2),
    unit_type VARCHAR(20), -- 'g', 'ml', 'piece'
    unit_size DECIMAL(10,2),
    availability VARCHAR(20) DEFAULT 'regular', -- 'regular', 'seasonal', 'special'
    nutrition_per_100g JSONB, -- Kalorien, Protein, Kohlenhydrate, Fett, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bestandsmanagement
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES aldi_products(id),
    quantity DECIMAL(10,2) NOT NULL,
    expiry_date DATE,
    purchase_date DATE DEFAULT CURRENT_DATE,
    location VARCHAR(100) DEFAULT 'Kühlschrank',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rezepte
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    meal_type VARCHAR(20) NOT NULL, -- 'breakfast', 'lunch', 'dinner'
    servings INTEGER DEFAULT 2,
    prep_time INTEGER, -- Minuten
    cook_time INTEGER, -- Minuten
    instructions TEXT,
    difficulty_level INTEGER DEFAULT 1, -- 1-5
    estimated_calories_per_serving INTEGER,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rezept-Zutaten
CREATE TABLE recipe_ingredients (
    recipe_id INTEGER REFERENCES recipes(id),
    product_id INTEGER REFERENCES aldi_products(id),
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    is_essential BOOLEAN DEFAULT true,
    PRIMARY KEY (recipe_id, product_id)
);
```

### 2.2 Health & Tracking

```sql
-- Gesundheitsdaten
CREATE TABLE health_metrics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE NOT NULL,
    weight DECIMAL(5,2),
    blood_pressure_systolic INTEGER,
    blood_pressure_diastolic INTEGER,
    pulse INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Mahlzeiten-Tracking
CREATE TABLE meal_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recipe_id INTEGER REFERENCES recipes(id),
    meal_type VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    servings_consumed DECIMAL(3,1) DEFAULT 1.0,
    rating INTEGER, -- 1-5 Sterne
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Einkaufslisten
CREATE TABLE shopping_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    list_type VARCHAR(20) DEFAULT 'weekly', -- 'daily', 'weekly'
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'archived'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE shopping_list_items (
    id SERIAL PRIMARY KEY,
    shopping_list_id INTEGER REFERENCES shopping_lists(id),
    product_id INTEGER REFERENCES aldi_products(id),
    quantity DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    priority INTEGER DEFAULT 1, -- 1-3
    is_checked BOOLEAN DEFAULT false,
    estimated_price DECIMAL(8,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.3 ML & Optimization

```sql
-- ML Bewertungen
CREATE TABLE recipe_ratings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recipe_id INTEGER REFERENCES recipes(id),
    rating INTEGER NOT NULL, -- 1-5
    complexity_rating INTEGER, -- 1-5 (wie schwer war es?)
    satisfaction_rating INTEGER, -- 1-5 (wie satt/zufrieden?)
    health_impact_rating INTEGER, -- 1-5 (wie gesund gefühlt?)
    would_cook_again BOOLEAN,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, recipe_id, created_at::date)
);

-- ML Trainingsdaten
CREATE TABLE ml_training_data (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    recipe_id INTEGER REFERENCES recipes(id),
    features JSONB, -- Nutritional features, complexity, etc.
    target_score DECIMAL(3,2), -- Kombinierter Score aus Ratings
    weight DECIMAL(5,4) DEFAULT 1.0, -- Gewichtung für Training
    created_at TIMESTAMP DEFAULT NOW()
);

-- Kassenbon-Verarbeitung
CREATE TABLE receipt_scans (
    id SERIAL PRIMARY KEY,
    image_path VARCHAR(500) NOT NULL,
    scan_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    ocr_service VARCHAR(50), -- 'openai', 'google_vision'
    raw_ocr_result JSONB,
    processed_items JSONB, -- Array von erkannten Produkten
    confidence_score DECIMAL(3,2),
    manual_corrections JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

## 3. API-DESIGN

### 3.1 REST API Endpoints

```python
# Basis-URL: /api/v1

# Benutzer & Einstellungen
GET    /users                     # Liste der Benutzer
GET    /users/{user_id}          # Benutzerdetails
PUT    /users/{user_id}/settings # Einstellungen aktualisieren

# Gesundheitsdaten
GET    /users/{user_id}/health          # Gesundheitsverlauf
POST   /users/{user_id}/health          # Neue Messung hinzufügen
PUT    /users/{user_id}/health/{date}   # Tageswerte aktualisieren

# Rezepte & ML
GET    /recipes/suggestions/{user_id}   # Tagesvorschläge (ML)
GET    /recipes                         # Alle Rezepte
GET    /recipes/{recipe_id}             # Rezeptdetails
POST   /recipes/{recipe_id}/rate        # Rezept bewerten

# Bestandsmanagement
GET    /inventory                       # Aktueller Bestand
POST   /inventory/update               # Bestand aktualisieren
GET    /inventory/expiring             # Ablaufende Produkte

# Einkaufslisten
GET    /shopping-lists                  # Alle Listen
POST   /shopping-lists                  # Neue Liste erstellen
PUT    /shopping-lists/{list_id}/items  # Items hinzufügen/entfernen

# Kassenbon-Scanning
POST   /receipts/scan                   # Upload & Verarbeitung
GET    /receipts/{scan_id}/status       # Verarbeitungsstatus
POST   /receipts/{scan_id}/confirm      # Erkannte Items bestätigen

# Analytics & Reports
GET    /analytics/health/{user_id}      # Gesundheitstrends
GET    /analytics/nutrition/{user_id}   # Ernährungsanalyse
GET    /analytics/costs                 # Kostenauswertung
```

### 3.2 FastAPI Implementation Structure

```python
# app/main.py
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ernährungs-App", version="1.0.0")

# Static files serving
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
from .routers import users, health, recipes, inventory, shopping, analytics
app.include_router(users.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(recipes.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(shopping.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")

# app/models/
# - user.py (Pydantic models)
# - health.py
# - recipe.py
# - inventory.py
# - ml_models.py

# app/services/
# - ml_service.py (Recipe optimization)
# - ocr_service.py (Receipt scanning)
# - nutrition_service.py
# - inventory_service.py

# app/database/
# - connection.py (SQLAlchemy setup)
# - crud.py (Database operations)
# - migrations/ (Alembic)
```

## 4. ML-PIPELINE

### 4.1 Recipe Recommendation Engine

```python
# services/ml_service.py
class RecipeOptimizer:
    def __init__(self):
        self.model = None
        self.feature_scaler = StandardScaler()
        
    def generate_daily_suggestions(self, user_id: int, date: str) -> Dict[str, List[Recipe]]:
        """
        Generiert tägliche Rezeptvorschläge:
        - 1 gemeinsames Rezept pro Mahlzeit
        - 2 individuelle Alternativen pro Person
        """
        user_preferences = self._get_user_preferences(user_id)
        available_ingredients = self._get_available_inventory()
        health_goals = self._get_health_goals(user_id)
        
        suggestions = {
            'breakfast': {
                'shared': self._recommend_shared_recipe('breakfast', user_preferences),
                'individual': self._recommend_individual_recipes('breakfast', user_id, 2)
            },
            'lunch': {
                'shared': self._recommend_shared_recipe('lunch', user_preferences),
                'individual': self._recommend_individual_recipes('lunch', user_id, 2)
            },
            'dinner': {
                'shared': self._recommend_shared_recipe('dinner', user_preferences),
                'individual': self._recommend_individual_recipes('dinner', user_id, 2)
            }
        }
        
        return suggestions
    
    def _calculate_recipe_score(self, recipe: Recipe, user_id: int) -> float:
        """
        ML-Score Berechnung basierend auf:
        - Historische Bewertungen (50%)
        - Nutritional Goals Alignment (30%)
        - Verfügbare Zutaten (20%)
        """
        features = self._extract_recipe_features(recipe, user_id)
        if self.model:
            return self.model.predict([features])[0]
        else:
            # Fallback: einfach positiv
            return 0.7
    
    def update_model(self):
        """
        Wöchentliches Modell-Update basierend auf neuen Bewertungen
        """
        training_data = self._get_training_data()
        if len(training_data) >= 50:  # Minimum für sinnvolles Training
            X, y = self._prepare_training_data(training_data)
            self.model = RandomForestRegressor(n_estimators=100)
            self.model.fit(X, y)
            self._save_model()
```

### 4.2 Feature Engineering

```python
def _extract_recipe_features(self, recipe: Recipe, user_id: int) -> List[float]:
    """
    Feature-Extraktion für ML-Modell:
    """
    features = []
    
    # Nutritional Features (normalisiert auf 100g)
    nutrition = recipe.get_nutrition_per_serving()
    features.extend([
        nutrition.get('calories', 0) / 1000,  # Normalisierung
        nutrition.get('protein', 0) / 100,
        nutrition.get('carbs', 0) / 100,
        nutrition.get('fat', 0) / 100,
        nutrition.get('fiber', 0) / 50
    ])
    
    # Complexity Features
    features.extend([
        recipe.prep_time / 60,  # Normalisiert auf Stunden
        recipe.cook_time / 60,
        recipe.difficulty_level / 5,
        len(recipe.ingredients) / 20
    ])
    
    # User History Features
    user_history = self._get_user_recipe_history(user_id)
    features.extend([
        user_history.get('avg_rating', 0) / 5,
        user_history.get('completion_rate', 0),
        user_history.get('similar_recipes_liked', 0) / 10
    ])
    
    # Seasonal/Time Features
    features.extend([
        self._get_seasonal_factor(recipe),
        self._get_time_of_day_factor(recipe),
        self._get_day_of_week_factor()
    ])
    
    return features
```

### 4.3 OCR Pipeline

```python
# services/ocr_service.py
class ReceiptProcessor:
    def __init__(self):
        self.openai_client = OpenAI()
        self.google_vision_client = vision.ImageAnnotatorClient()
        
    async def process_receipt(self, image_path: str, scan_id: int) -> Dict:
        """
        Mehrstufige OCR-Verarbeitung:
        1. Primär: OpenAI Vision
        2. Fallback: Google Cloud Vision
        3. Produktabgleich mit Aldi-DB
        """
        try:
            # Versuche OpenAI Vision zuerst
            result = await self._process_with_openai(image_path)
            ocr_service = 'openai'
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}, trying Google Vision")
            result = await self._process_with_google_vision(image_path)
            ocr_service = 'google_vision'
            
        # Produktabgleich
        matched_products = await self._match_products(result['items'])
        
        # Speichere Ergebnis
        await self._save_scan_result(scan_id, result, matched_products, ocr_service)
        
        return {
            'status': 'completed',
            'confidence': result['confidence'],
            'items': matched_products,
            'service_used': ocr_service
        }
    
    async def _process_with_openai(self, image_path: str) -> Dict:
        """
        OpenAI Vision API für Kassenbon-Analyse
        """
        with open(image_path, 'rb') as image_file:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """
                                Analysiere diesen Aldi Kassenbon und extrahiere:
                                1. Produktname
                                2. Menge/Gewicht
                                3. Einzelpreis
                                4. Gesamtpreis
                                
                                Antwort als JSON Array:
                                [{"name": "...", "quantity": "...", "unit_price": "...", "total_price": "..."}]
                                """
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"}
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
        return {
            'items': json.loads(response.choices[0].message.content),
            'confidence': 0.9  # OpenAI typischerweise sehr genau
        }
```

## 5. DEPLOYMENT-ARCHITEKTUR

### 5.1 LXC Container Setup

```bash
# Container-Erstellung
lxc-create -t debian -n ernaehrung-app
lxc-start -n ernaehrung-app

# System-Setup
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv nginx postgresql-15 supervisor

# Python Environment
cd /opt/ernaehrung-app
python3.11 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn psycopg2-binary sqlalchemy alembic pydantic

# Database Setup
sudo -u postgres createdb ernaehrung_app
sudo -u postgres createuser ernaehrung_user
```

### 5.2 Production Configuration

```yaml
# supervisor/ernaehrung-app.conf
[program:ernaehrung-app]
command=/opt/ernaehrung-app/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
directory=/opt/ernaehrung-app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ernaehrung-app/app.log

# nginx/sites-available/ernaehrung-app
server {
    listen 80;
    server_name ernaehrung-app.local;
    
    # Static files
    location /static/ {
        alias /opt/ernaehrung-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API & Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 5.3 Database Management

```python
# alembic/env.py - Migration Setup
from app.database.connection import DATABASE_URL

config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Migration Commands
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Backup Strategy
#!/bin/bash
# backup_db.sh
pg_dump ernaehrung_app > /backups/ernaehrung_app_$(date +%Y%m%d_%H%M%S).sql

# Cron Job für tägliche Backups
0 2 * * * /opt/scripts/backup_db.sh
```

## 6. SICHERHEITSKONZEPT

### 6.1 Minimale Sicherheitsmaßnahmen (Private Umgebung)

```python
# app/security.py
from fastapi import HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

# Basis-Authentifizierung (optional für externe API-Zugriffe)
security = HTTPBasic()

class SecurityManager:
    def __init__(self):
        self.allowed_ips = ['10.1.1.0/24', '127.0.0.1']  # Lokales Netzwerk
        
    def validate_request_source(self, request: Request):
        """Einfache IP-Validierung für externe API-Calls"""
        client_ip = request.client.host
        if not self._is_local_network(client_ip):
            raise HTTPException(status_code=403, detail="Access denied")
    
    def _is_local_network(self, ip: str) -> bool:
        # Vereinfachte Implementierung
        return ip.startswith('10.1.1.') or ip == '127.0.0.1'

# API Rate Limiting (einfach)
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        
    def check_limit(self, client_ip: str, limit: int = 100, window: int = 3600):
        """100 Requests pro Stunde"""
        now = time.time()
        self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] 
                                   if now - req_time < window]
        
        if len(self.requests[client_ip]) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
        self.requests[client_ip].append(now)
```

### 6.2 Daten-Sicherheit

```python
# app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://ernaehrung_user:secure_password@localhost/ernaehrung_app"
    
    # External APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_CLOUD_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    UPLOAD_DIR: str = "/opt/ernaehrung-app/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Feature Flags
    ENABLE_ML: bool = True
    ENABLE_OCR: bool = True
    DEBUG: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

### 6.3 Backup & Recovery

```bash
#!/bin/bash
# backup_complete.sh - Vollständiges Backup-System

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Database Backup
pg_dump ernaehrung_app > $BACKUP_DIR/database.sql

# Application Files
tar -czf $BACKUP_DIR/application.tar.gz /opt/ernaehrung-app --exclude=venv --exclude=__pycache__

# Uploads (Kassenbons)
tar -czf $BACKUP_DIR/uploads.tar.gz /opt/ernaehrung-app/uploads

# Configuration
cp /etc/nginx/sites-available/ernaehrung-app $BACKUP_DIR/
cp /etc/supervisor/conf.d/ernaehrung-app.conf $BACKUP_DIR/

# Cleanup old backups (keep last 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

## 7. TECHNISCHE IMPLEMENTIERUNGSDETAILS

### 7.1 Frontend Architecture

```html
<!-- index.html - PWA Setup -->
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ernährungs-App</title>
    
    <!-- PWA Manifest -->
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#2196F3">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div id="app">
        <!-- Navigation -->
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">🥗 Ernährungs-App</a>
                <!-- User Switcher -->
                <select id="userSelect" class="form-select form-select-sm">
                    <option value="1">Person 1</option>
                    <option value="2">Person 2</option>
                </select>
            </div>
        </nav>
        
        <!-- Content Sections -->
        <main class="container mt-4">
            <section id="dashboard" class="row">
                <!-- Daily Suggestions -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Heutige Rezeptvorschläge</h5>
                        </div>
                        <div class="card-body" id="recipeSuggestions">
                            <!-- Dynamisch geladen via API -->
                        </div>
                    </div>
                </div>
                
                <!-- Health Dashboard -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5>Gesundheitstrends</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="healthChart"></canvas>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    </div>
    
    <!-- Service Worker Registration -->
    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }
    </script>
    
    <!-- Application Logic -->
    <script src="/static/js/app.js"></script>
</body>
</html>
```

```javascript
// static/js/app.js - Frontend Logic
class ErnaehrungsApp {
    constructor() {
        this.currentUser = 1;
        this.apiBase = '/api/v1';
        this.init();
    }
    
    async init() {
        await this.loadDashboard();
        this.setupEventListeners();
        this.initializeCharts();
    }
    
    async loadDashboard() {
        // Tägliche Rezeptvorschläge laden
        const suggestions = await this.apiCall(`/recipes/suggestions/${this.currentUser}`);
        this.renderRecipeSuggestions(suggestions);
        
        // Gesundheitsdaten laden
        const healthData = await this.apiCall(`/analytics/health/${this.currentUser}`);
        this.updateHealthChart(healthData);
    }
    
    async apiCall(endpoint, options = {}) {
        const response = await fetch(this.apiBase + endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    renderRecipeSuggestions(suggestions) {
        const container = document.getElementById('recipeSuggestions');
        container.innerHTML = '';
        
        ['breakfast', 'lunch', 'dinner'].forEach(mealType => {
            const mealDiv = document.createElement('div');
            mealDiv.className = 'meal-suggestions mb-3';
            mealDiv.innerHTML = `
                <h6 class="text-capitalize">${mealType}</h6>
                <div class="row">
                    <div class="col-12">
                        <div class="card border-success">
                            <div class="card-body">
                                <h6 class="card-title">👫 Gemeinsam</h6>
                                <p class="card-text">${suggestions[mealType].shared.name}</p>
                                <small class="text-muted">${suggestions[mealType].shared.estimated_calories_per_serving} kcal</small>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="row mt-2">
                    ${suggestions[mealType].individual.map((recipe, index) => `
                        <div class="col-6">
                            <div class="card border-info">
                                <div class="card-body">
                                    <h6 class="card-title">Alternative ${index + 1}</h6>
                                    <p class="card-text">${recipe.name}</p>
                                    <small class="text-muted">${recipe.estimated_calories_per_serving} kcal</small>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            container.appendChild(mealDiv);
        });
    }
}

// App initialisieren
document.addEventListener('DOMContentLoaded', () => {
    new ErnaehrungsApp();
});
```

### 7.2 Performance Optimierung

```python
# app/middleware/caching.py
from functools import lru_cache
import asyncio
from typing import Dict, Any

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}
        
    @lru_cache(maxsize=100)
    def get_aldi_products_cached(self, category: str = None):
        """Cache für Aldi Produktdatenbank"""
        return self._get_aldi_products_from_db(category)
    
    async def get_recipe_suggestions_cached(self, user_id: int, date: str):
        """Cache für tägliche Rezeptvorschläge"""
        cache_key = f"suggestions_{user_id}_{date}"
        
        if cache_key in self._cache and self._is_cache_valid(cache_key):
            return self._cache[cache_key]
            
        # Generiere neue Vorschläge
        suggestions = await self._generate_suggestions(user_id, date)
        
        # Cache für 4 Stunden
        self._cache[cache_key] = suggestions
        self._cache_ttl[cache_key] = time.time() + 4 * 3600
        
        return suggestions

# Database Connection Pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

## 8. MONITORING & OBSERVABILITY

```python
# app/monitoring.py
import logging
from prometheus_client import Counter, Histogram, Gauge
import time

# Metriken Definition
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
ML_PREDICTIONS = Counter('ml_predictions_total', 'Total ML predictions made', ['model_type'])

class MonitoringMiddleware:
    async def __call__(self, request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        REQUEST_DURATION.observe(duration)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        return response

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ernaehrung-app/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

Dieses High-Level Design bietet eine vollständige technische Grundlage für die Implementierung der Ernährungs- und Gesundheits-App mit allen spezifizierten Anforderungen. Die Architektur ist modular aufgebaut, skalierbar und für den Einsatz in einer LXC-Container-Umgebung optimiert.