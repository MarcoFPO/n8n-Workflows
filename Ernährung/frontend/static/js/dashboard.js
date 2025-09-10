class ErnaehrungsAppDashboard {
    constructor() {
        this.currentUser = 1;
        this.apiBase = '/api/v1';
        this.weightChart = null;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.updateCurrentDate();
        await this.loadDashboard();
        this.initializeCharts();
    }
    
    setupEventListeners() {
        // User selector
        document.getElementById('userSelect').addEventListener('change', (e) => {
            this.currentUser = parseInt(e.target.value);
            this.loadDashboard();
        });
        
        // Receipt file input
        document.getElementById('receiptFile').addEventListener('change', (e) => {
            this.previewReceiptImage(e.target.files[0]);
        });
    }
    
    updateCurrentDate() {
        const today = new Date();
        const options = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            weekday: 'long'
        };
        document.getElementById('currentDate').textContent = 
            today.toLocaleDateString('de-DE', options);
    }
    
    async loadDashboard() {
        try {
            await Promise.all([
                this.loadMetrics(),
                this.loadRecipeSuggestions(),
                this.loadHealthData(),
                this.loadInventoryAlerts()
            ]);
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showError('Fehler beim Laden des Dashboards');
        }
    }
    
    async loadMetrics() {
        try {
            // Load various metrics
            const [healthData, mealData, inventoryData] = await Promise.all([
                this.apiCall(`/analytics/health/${this.currentUser}`),
                this.apiCall(`/users/${this.currentUser}/health`), // Recent health data
                this.apiCall('/inventory')
            ]);
            
            // Update metric cards
            document.getElementById('todayCalories').textContent = 
                this.calculateTodaysCalories(mealData) || '0';
            document.getElementById('currentWeight').textContent = 
                this.getLatestWeight(healthData) || '--';
            document.getElementById('weeklyMeals').textContent = 
                this.calculateWeeklyMeals(mealData) || '0';
            document.getElementById('inventoryItems').textContent = 
                Array.isArray(inventoryData) ? inventoryData.length : '0';
                
        } catch (error) {
            console.error('Error loading metrics:', error);
        }
    }
    
    async loadRecipeSuggestions() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const suggestions = await this.apiCall(`/recipes/suggestions/${this.currentUser}?suggestion_date=${today}`);
            
            this.renderMealSuggestions('breakfastSuggestions', suggestions.breakfast);
            this.renderMealSuggestions('lunchSuggestions', suggestions.lunch);
            this.renderMealSuggestions('dinnerSuggestions', suggestions.dinner);
        } catch (error) {
            console.error('Error loading recipe suggestions:', error);
            // Show fallback suggestions
            this.showFallbackRecipes();
        }
    }
    
    renderMealSuggestions(containerId, mealSuggestion) {
        const container = document.getElementById(containerId);
        
        if (!mealSuggestion || !mealSuggestion.shared) {
            container.innerHTML = '<p class="text-muted">Keine Vorschläge verfügbar</p>';
            return;
        }
        
        const sharedRecipe = mealSuggestion.shared;
        const individualRecipes = mealSuggestion.individual || [];
        
        container.innerHTML = `
            <!-- Shared Recipe -->
            <div class="col-12 mb-3">
                <div class="recipe-card card">
                    <span class="badge bg-success meal-type-badge">👫 Gemeinsam</span>
                    <div class="card-body">
                        <h6 class="card-title">${sharedRecipe.name}</h6>
                        <p class="card-text text-muted">${this.truncateText(sharedRecipe.instructions || 'Keine Beschreibung verfügbar', 100)}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                <i class="fas fa-fire me-1"></i>
                                ${sharedRecipe.estimated_calories_per_serving || 'N/A'} kcal
                            </small>
                            <div>
                                <span class="badge bg-light text-dark me-2">
                                    <i class="fas fa-clock me-1"></i>
                                    ${sharedRecipe.prep_time || 'N/A'} min
                                </span>
                                <span class="badge bg-light text-dark">
                                    Schwierigkeit: ${sharedRecipe.difficulty_level}/5
                                </span>
                            </div>
                        </div>
                        <div class="mt-2">
                            <button class="btn btn-sm btn-primary-custom me-2" onclick="dashboard.selectRecipe(${sharedRecipe.id})">
                                <i class="fas fa-check me-1"></i>
                                Auswählen
                            </button>
                            <button class="btn btn-sm btn-outline-custom" onclick="dashboard.viewRecipe(${sharedRecipe.id})">
                                <i class="fas fa-eye me-1"></i>
                                Details
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Individual Alternatives -->
            ${individualRecipes.map((recipe, index) => `
                <div class="col-6">
                    <div class="recipe-card card">
                        <span class="badge bg-info meal-type-badge">Alternative ${index + 1}</span>
                        <div class="card-body">
                            <h6 class="card-title">${recipe.name}</h6>
                            <p class="card-text text-muted">${this.truncateText(recipe.instructions || 'Keine Beschreibung verfügbar', 80)}</p>
                            <div class="text-center">
                                <small class="text-muted">
                                    <i class="fas fa-fire me-1"></i>
                                    ${recipe.estimated_calories_per_serving || 'N/A'} kcal
                                </small>
                            </div>
                            <div class="mt-2 d-grid gap-1">
                                <button class="btn btn-sm btn-outline-custom" onclick="dashboard.selectRecipe(${recipe.id})">
                                    Auswählen
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        `;
    }
    
    showFallbackRecipes() {
        const fallbackRecipes = {
            breakfast: {
                shared: { id: 0, name: 'Haferflocken mit Früchten', estimated_calories_per_serving: 320, prep_time: 10, difficulty_level: 1 },
                individual: [
                    { id: 0, name: 'Vollkornbrot mit Aufstrich', estimated_calories_per_serving: 280 },
                    { id: 0, name: 'Smoothie Bowl', estimated_calories_per_serving: 350 }
                ]
            },
            lunch: {
                shared: { id: 0, name: 'Gemüse-Pfanne', estimated_calories_per_serving: 420, prep_time: 25, difficulty_level: 3 },
                individual: [
                    { id: 0, name: 'Salat mit Hühnchen', estimated_calories_per_serving: 380 },
                    { id: 0, name: 'Suppe mit Brot', estimated_calories_per_serving: 320 }
                ]
            },
            dinner: {
                shared: { id: 0, name: 'Nudeln mit Tomatensauce', estimated_calories_per_serving: 480, prep_time: 30, difficulty_level: 2 },
                individual: [
                    { id: 0, name: 'Fisch mit Gemüse', estimated_calories_per_serving: 420 },
                    { id: 0, name: 'Vegetarisches Curry', estimated_calories_per_serving: 380 }
                ]
            }
        };
        
        this.renderMealSuggestions('breakfastSuggestions', fallbackRecipes.breakfast);
        this.renderMealSuggestions('lunchSuggestions', fallbackRecipes.lunch);
        this.renderMealSuggestions('dinnerSuggestions', fallbackRecipes.dinner);
    }
    
    async loadHealthData() {
        try {
            const healthData = await this.apiCall(`/users/${this.currentUser}/health?limit=30`);
            this.updateWeightChart(healthData);
        } catch (error) {
            console.error('Error loading health data:', error);
            this.showMockWeightChart();
        }
    }
    
    async loadInventoryAlerts() {
        try {
            const expiringItems = await this.apiCall('/inventory/expiring?days=7');
            this.renderInventoryAlerts(expiringItems);
        } catch (error) {
            console.error('Error loading inventory alerts:', error);
            this.showMockInventoryAlerts();
        }
    }
    
    renderInventoryAlerts(expiringItems) {
        const container = document.getElementById('inventoryAlerts');
        
        if (!expiringItems || expiringItems.length === 0) {
            container.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    Alle Produkte sind noch haltbar!
                </div>
            `;
            return;
        }
        
        const alertsHtml = expiringItems.map(item => {
            const daysUntilExpiry = this.calculateDaysUntilExpiry(item.expiry_date);
            const alertClass = daysUntilExpiry <= 2 ? 'expiring-alert' : 'inventory-alert';
            const icon = daysUntilExpiry <= 2 ? 'fas fa-exclamation-triangle' : 'fas fa-clock';
            
            return `
                <div class="alert ${alertClass}">
                    <i class="${icon} me-2"></i>
                    <strong>${item.product?.name || 'Unbekanntes Produkt'}</strong><br>
                    <small>Läuft in ${daysUntilExpiry} Tag${daysUntilExpiry !== 1 ? 'en' : ''} ab</small>
                </div>
            `;
        }).join('');
        
        container.innerHTML = alertsHtml;
    }
    
    showMockInventoryAlerts() {
        const container = document.getElementById('inventoryAlerts');
        container.innerHTML = `
            <div class="alert expiring-alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Milch</strong><br>
                <small>Läuft in 2 Tagen ab</small>
            </div>
            <div class="alert inventory-alert">
                <i class="fas fa-clock me-2"></i>
                <strong>Brot</strong><br>
                <small>Läuft in 5 Tagen ab</small>
            </div>
        `;
    }
    
    initializeCharts() {
        this.setupWeightChart();
    }
    
    setupWeightChart() {
        const ctx = document.getElementById('weightChart');
        this.weightChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Gewicht (kg)',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    updateWeightChart(healthData) {
        if (!this.weightChart || !healthData || healthData.length === 0) {
            this.showMockWeightChart();
            return;
        }
        
        const weightData = healthData
            .filter(entry => entry.weight)
            .sort((a, b) => new Date(a.date) - new Date(b.date))
            .slice(-14); // Last 14 days
        
        const labels = weightData.map(entry => {
            const date = new Date(entry.date);
            return date.toLocaleDateString('de-DE', { month: 'short', day: 'numeric' });
        });
        
        const weights = weightData.map(entry => parseFloat(entry.weight));
        
        this.weightChart.data.labels = labels;
        this.weightChart.data.datasets[0].data = weights;
        this.weightChart.update();
    }
    
    showMockWeightChart() {
        if (!this.weightChart) return;
        
        const mockLabels = ['1. Sep', '3. Sep', '5. Sep', '7. Sep', '9. Sep'];
        const mockData = [75.2, 74.8, 74.9, 74.5, 74.3];
        
        this.weightChart.data.labels = mockLabels;
        this.weightChart.data.datasets[0].data = mockData;
        this.weightChart.update();
    }
    
    // Utility Methods
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
    
    calculateTodaysCalories(mealData) {
        const today = new Date().toISOString().split('T')[0];
        if (!mealData || !Array.isArray(mealData)) return 0;
        
        return mealData
            .filter(meal => meal.date === today)
            .reduce((total, meal) => total + (meal.recipe?.estimated_calories_per_serving || 0), 0);
    }
    
    getLatestWeight(healthData) {
        if (!healthData || !Array.isArray(healthData) || healthData.length === 0) return null;
        
        const latestEntry = healthData.find(entry => entry.weight);
        return latestEntry ? parseFloat(latestEntry.weight).toFixed(1) : null;
    }
    
    calculateWeeklyMeals(mealData) {
        if (!mealData || !Array.isArray(mealData)) return 0;
        
        const oneWeekAgo = new Date();
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        
        return mealData.filter(meal => new Date(meal.date) >= oneWeekAgo).length;
    }
    
    calculateDaysUntilExpiry(expiryDate) {
        const today = new Date();
        const expiry = new Date(expiryDate);
        const diffTime = expiry - today;
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
    
    truncateText(text, maxLength) {
        return text && text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
    
    showError(message) {
        // Simple error display - could be enhanced with toast notifications
        console.error(message);
    }
    
    // Action Methods
    selectRecipe(recipeId) {
        console.log('Selected recipe:', recipeId);
        // TODO: Implement recipe selection logic
        this.showInfo(`Rezept ${recipeId} ausgewählt`);
    }
    
    viewRecipe(recipeId) {
        console.log('Viewing recipe:', recipeId);
        // TODO: Open recipe details modal or page
        window.location.href = `/recipes/${recipeId}`;
    }
    
    previewReceiptImage(file) {
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('receiptImage').src = e.target.result;
                document.getElementById('receiptPreview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    }
    
    async uploadReceipt() {
        const fileInput = document.getElementById('receiptFile');
        const file = fileInput.files[0];
        
        if (!file) {
            alert('Bitte wählen Sie eine Datei aus');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/v1/receipts/scan', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Kassenbon erfolgreich hochgeladen! Scan-ID: ${result.scan_id}`);
                bootstrap.Modal.getInstance(document.getElementById('receiptModal')).hide();
                // Refresh inventory after successful upload
                setTimeout(() => this.loadInventoryAlerts(), 2000);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Error uploading receipt:', error);
            alert('Fehler beim Hochladen des Kassenbons');
        }
    }
    
    showInfo(message) {
        // Simple info display - could be enhanced with toast notifications
        console.info(message);
    }
}

// Global Functions (called from HTML)
function openReceiptScanner() {
    new bootstrap.Modal(document.getElementById('receiptModal')).show();
}

function addHealthMetrics() {
    // TODO: Implement health metrics input
    alert('Gesundheitsdaten-Dialog wird implementiert');
}

function viewShoppingList() {
    window.location.href = '/shopping-list';
}

function uploadReceipt() {
    dashboard.uploadReceipt();
}

// Initialize Dashboard
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new ErnaehrungsAppDashboard();
});