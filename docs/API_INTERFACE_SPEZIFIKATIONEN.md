# 🔌 API-Interface-Spezifikationen - Vollständige Definitionen

## 🎯 **Übersicht**

**Kontext**: Vollständige OpenAPI 3.1 Spezifikationen für alle 5 Services im aktienanalyse-ökosystem
**Ziel**: Standardisierte APIs, Event-Protokolle und Service-Kommunikation
**Ansatz**: API-First-Design mit Versionierung, Rate-Limiting und Error-Standards

---

## 🏗️ **1. SERVICE-ARCHITECTURE OVERVIEW**

### 1.1 **Service-Port-Matrix & API-Endpoints**
```yaml
# config/api-service-mapping.yaml

services:
  intelligent_core_service:
    port: 8001
    base_path: "/api/v1"
    description: "Zentrale Business-Logic und Portfolio-Management"
    endpoints:
      - "/portfolios"
      - "/assets" 
      - "/analysis"
      - "/risk"
      - "/rebalancing"
    
  broker_gateway_service:
    port: 8002
    base_path: "/api/v1"
    description: "Broker-Integration und Trading-Operations"
    endpoints:
      - "/orders"
      - "/executions"
      - "/market-data"
      - "/positions"
    
  event_bus_service:
    port: 8003
    base_path: "/api/v1"
    description: "Event-Sourcing und Message-Queue"
    endpoints:
      - "/events"
      - "/subscriptions"
      - "/projections"
      - "/replay"
    
  monitoring_service:
    port: 8083
    base_path: "/api/v1"
    description: "System-Monitoring und Health-Checks"
    endpoints:
      - "/health"
      - "/metrics"
      - "/alerts"
      - "/dashboards"
    
  frontend_service:
    port: 8084
    base_path: "/api/v1"
    description: "Enhanced Frontend mit Sidebar-Navigation (GUI v2.0)"
    endpoints:
      - "/content/{section}"
      - "/proxy/{service}"
      - "/health"
      - "/static"

# Inter-Service Communication Matrix
inter_service_communication:
  intelligent_core_service:
    calls:
      - broker_gateway_service: ["/orders", "/market-data", "/positions"]
      - event_bus_service: ["/events", "/projections"]
      - monitoring_service: ["/metrics"]
    
  broker_gateway_service:
    calls:
      - event_bus_service: ["/events"]
      - monitoring_service: ["/metrics"]
    
  frontend_service:
    calls:
      - intelligent_core_service: ["/portfolios", "/assets", "/analysis"]
      - broker_gateway_service: ["/orders", "/positions"]
      - monitoring_service: ["/health", "/metrics"]
```

---

## 📋 **2. OPENAPI/SWAGGER-SPEZIFIKATIONEN**

### 2.1 **Intelligent Core Service API**
```yaml
# services/intelligent-core-service/openapi.yaml
openapi: 3.1.0
info:
  title: Aktienanalyse Intelligent Core Service API
  description: |
    Zentrale Business-Logic für Portfolio-Management, Asset-Analyse und Risk-Management.
    
    ## Features
    - Portfolio-Management mit automatischem Rebalancing
    - Asset-Analyse mit ML-basierten Scoring-Algorithmen  
    - Risk-Management mit konfigurierbaren Limits
    - Steuerberechnung nach deutschem Recht
    
  version: 1.0.0
  contact:
    name: API Support
    email: support@aktienanalyse-ecosystem.local
  license:
    name: Private License
    
servers:
  - url: http://127.0.0.1:8001/api/v1
    description: Local Development Server
  - url: https://127.0.0.1:8001/api/v1  
    description: Local HTTPS Server

security:
  - ApiKeyAuth: []
  - BearerAuth: []

paths:
  # Portfolio Management
  /portfolios:
    get:
      tags: [Portfolio Management]
      summary: Liste aller Portfolios
      description: Ruft alle verfügbaren Portfolios mit aktuellen Allokationen ab
      parameters:
        - name: include_positions
          in: query
          schema:
            type: boolean
            default: false
          description: Ob Positionen in Response inkludiert werden sollen
        - name: include_performance
          in: query
          schema:
            type: boolean
            default: false
          description: Ob Performance-Metriken inkludiert werden sollen
      responses:
        '200':
          description: Liste der Portfolios
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Portfolio'
                  meta:
                    $ref: '#/components/schemas/PaginationMeta'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '500':
          $ref: '#/components/responses/InternalServerError'
    
    post:
      tags: [Portfolio Management]
      summary: Erstelle neues Portfolio
      description: Erstellt ein neues Portfolio mit initialer Konfiguration
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePortfolioRequest'
      responses:
        '201':
          description: Portfolio erfolgreich erstellt
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/Portfolio'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          $ref: '#/components/responses/Conflict'
        '500':
          $ref: '#/components/responses/InternalServerError'

  /portfolios/{portfolio_id}:
    get:
      tags: [Portfolio Management]
      summary: Portfolio-Details abrufen
      parameters:
        - name: portfolio_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          example: "123e4567-e89b-12d3-a456-426614174000"
      responses:
        '200':
          description: Portfolio-Details
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/PortfolioDetails'
        '404':
          $ref: '#/components/responses/NotFound'
    
    put:
      tags: [Portfolio Management]
      summary: Portfolio aktualisieren
      parameters:
        - name: portfolio_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdatePortfolioRequest'
      responses:
        '200':
          description: Portfolio erfolgreich aktualisiert
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/Portfolio'
        '400':
          $ref: '#/components/responses/BadRequest'
        '404':
          $ref: '#/components/responses/NotFound'

  /portfolios/{portfolio_id}/rebalance:
    post:
      tags: [Portfolio Management]
      summary: Portfolio rebalancieren
      description: |
        Führt Rebalancing des Portfolios zur Ziel-Allokation durch.
        Berücksichtigt Risk-Limits und Trading-Kosten.
      parameters:
        - name: portfolio_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: dry_run
          in: query
          schema:
            type: boolean
            default: false
          description: Nur Simulation ohne tatsächliche Orders
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RebalanceRequest'
      responses:
        '200':
          description: Rebalancing erfolgreich gestartet
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/RebalanceResult'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          $ref: '#/components/responses/Conflict'

  # Asset Analysis
  /assets:
    get:
      tags: [Asset Analysis]
      summary: Asset-Suche und -Listing
      parameters:
        - name: symbol
          in: query
          schema:
            type: string
          description: Asset-Symbol (z.B. "AAPL", "BTC")
        - name: asset_class
          in: query
          schema:
            type: string
            enum: [stock, etf, crypto, commodity, bond]
          description: Asset-Klasse Filter
        - name: sector
          in: query
          schema:
            type: string
          description: Sektor-Filter
        - name: min_market_cap
          in: query
          schema:
            type: number
            format: float
          description: Mindest-Marktkapitalisierung
        - name: tradeable_only
          in: query
          schema:
            type: boolean
            default: true
          description: Nur handelbare Assets
      responses:
        '200':
          description: Asset-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Asset'
                  meta:
                    $ref: '#/components/schemas/PaginationMeta'

  /assets/{asset_symbol}/analysis:
    get:
      tags: [Asset Analysis]
      summary: Asset-Analyse abrufen
      parameters:
        - name: asset_symbol
          in: path
          required: true
          schema:
            type: string
          example: "AAPL"
        - name: analysis_type
          in: query
          schema:
            type: string
            enum: [technical, fundamental, sentiment, risk, all]
            default: all
      responses:
        '200':
          description: Asset-Analyse
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/AssetAnalysis'
        '404':
          $ref: '#/components/responses/NotFound'

  # Risk Management
  /risk/portfolio/{portfolio_id}/assessment:
    get:
      tags: [Risk Management]
      summary: Portfolio-Risk-Assessment
      parameters:
        - name: portfolio_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: horizon_days
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 365
            default: 30
          description: Risk-Horizont in Tagen
      responses:
        '200':
          description: Risk-Assessment-Report
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/RiskAssessment'

  /risk/limits:
    get:
      tags: [Risk Management]
      summary: Risk-Limits abrufen
      responses:
        '200':
          description: Aktuelle Risk-Limits
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/RiskLimits'
    
    put:
      tags: [Risk Management]
      summary: Risk-Limits aktualisieren
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateRiskLimitsRequest'
      responses:
        '200':
          description: Risk-Limits erfolgreich aktualisiert
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    $ref: '#/components/schemas/RiskLimits'

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Portfolio:
      type: object
      required: [portfolio_id, name, currency, created_at]
      properties:
        portfolio_id:
          type: string
          format: uuid
          example: "123e4567-e89b-12d3-a456-426614174000"
        name:
          type: string
          minLength: 1
          maxLength: 100
          example: "Mein Haupt-Portfolio"
        description:
          type: string
          maxLength: 500
          example: "Langfristige Anlagestrategie mit ETF-Fokus"
        currency:
          type: string
          enum: [EUR, USD]
          example: "EUR"
        total_value:
          type: number
          format: float
          minimum: 0
          example: 50000.00
        cash_balance:
          type: number
          format: float
          minimum: 0
          example: 2500.00
        created_at:
          type: string
          format: date-time
          example: "2024-01-15T10:30:00Z"
        updated_at:
          type: string
          format: date-time
          example: "2024-01-20T14:22:00Z"
        risk_profile:
          type: string
          enum: [conservative, moderate, aggressive]
          example: "moderate"
        target_allocation:
          type: object
          additionalProperties:
            type: number
            format: float
            minimum: 0
            maximum: 100
          example:
            stocks: 60.0
            bonds: 30.0
            cash: 10.0

    PortfolioDetails:
      allOf:
        - $ref: '#/components/schemas/Portfolio'
        - type: object
          properties:
            positions:
              type: array
              items:
                $ref: '#/components/schemas/Position'
            performance:
              $ref: '#/components/schemas/PerformanceMetrics'
            risk_metrics:
              $ref: '#/components/schemas/RiskMetrics'

    Position:
      type: object
      required: [position_id, asset_symbol, quantity, average_price]
      properties:
        position_id:
          type: string
          format: uuid
        asset_symbol:
          type: string
          example: "AAPL"
        asset_name:
          type: string
          example: "Apple Inc."
        quantity:
          type: number
          format: float
          minimum: 0
          example: 10.5
        average_price:
          type: number
          format: float
          minimum: 0
          example: 150.25
        current_price:
          type: number
          format: float
          minimum: 0
          example: 155.80
        market_value:
          type: number
          format: float
          minimum: 0
          example: 1635.90
        unrealized_pnl:
          type: number
          format: float
          example: 58.28
        unrealized_pnl_percent:
          type: number
          format: float
          example: 3.69
        allocation_percent:
          type: number
          format: float
          minimum: 0
          maximum: 100
          example: 3.27

    Asset:
      type: object
      required: [asset_symbol, name, asset_class]
      properties:
        asset_symbol:
          type: string
          example: "AAPL"
        name:
          type: string
          example: "Apple Inc."
        asset_class:
          type: string
          enum: [stock, etf, crypto, commodity, bond]
          example: "stock"
        sector:
          type: string
          example: "Technology"
        country:
          type: string
          example: "US"
        currency:
          type: string
          example: "USD"
        market_cap:
          type: number
          format: float
          minimum: 0
          example: 3000000000000
        is_tradeable:
          type: boolean
          example: true
        exchange:
          type: string
          example: "NASDAQ"

    AssetAnalysis:
      type: object
      properties:
        asset_symbol:
          type: string
          example: "AAPL"
        analysis_timestamp:
          type: string
          format: date-time
        technical_analysis:
          $ref: '#/components/schemas/TechnicalAnalysis'
        fundamental_analysis:
          $ref: '#/components/schemas/FundamentalAnalysis'
        sentiment_analysis:
          $ref: '#/components/schemas/SentimentAnalysis'
        risk_analysis:
          $ref: '#/components/schemas/AssetRiskAnalysis'
        ml_score:
          $ref: '#/components/schemas/MLScore'

    TechnicalAnalysis:
      type: object
      properties:
        trend:
          type: string
          enum: [bullish, bearish, neutral]
          example: "bullish"
        rsi:
          type: number
          format: float
          minimum: 0
          maximum: 100
          example: 65.4
        macd:
          $ref: '#/components/schemas/MACDIndicator'
        support_levels:
          type: array
          items:
            type: number
            format: float
          example: [150.0, 145.0, 140.0]
        resistance_levels:
          type: array
          items:
            type: number
            format: float
          example: [160.0, 165.0, 170.0]

    CreatePortfolioRequest:
      type: object
      required: [name, currency]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
          example: "Neues Portfolio"
        description:
          type: string
          maxLength: 500
        currency:
          type: string
          enum: [EUR, USD]
          example: "EUR"
        initial_cash:
          type: number
          format: float
          minimum: 0
          example: 10000.00
        risk_profile:
          type: string
          enum: [conservative, moderate, aggressive]
          example: "moderate"
        target_allocation:
          type: object
          additionalProperties:
            type: number
            format: float
            minimum: 0
            maximum: 100

    RebalanceRequest:
      type: object
      properties:
        target_allocation:
          type: object
          additionalProperties:
            type: number
            format: float
            minimum: 0
            maximum: 100
          example:
            stocks: 65.0
            bonds: 25.0
            cash: 10.0
        max_trade_amount:
          type: number
          format: float
          minimum: 0
          description: Maximaler Betrag pro Trade
        respect_risk_limits:
          type: boolean
          default: true
        min_trade_threshold:
          type: number
          format: float
          minimum: 0
          default: 100
          description: Mindestbetrag für Trade-Ausführung

    RiskAssessment:
      type: object
      properties:
        portfolio_id:
          type: string
          format: uuid
        assessment_date:
          type: string
          format: date-time
        overall_risk_score:
          type: number
          format: float
          minimum: 0
          maximum: 100
          example: 65.5
        risk_level:
          type: string
          enum: [low, moderate, high, very_high]
          example: "moderate"
        value_at_risk:
          $ref: '#/components/schemas/ValueAtRisk'
        concentration_risk:
          $ref: '#/components/schemas/ConcentrationRisk'
        liquidity_risk:
          $ref: '#/components/schemas/LiquidityRisk'
        currency_risk:
          $ref: '#/components/schemas/CurrencyRisk'

    # Standard Response Schemas
    ErrorResponse:
      type: object
      required: [success, error]
      properties:
        success:
          type: boolean
          example: false
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
              example: "VALIDATION_ERROR"
            message:
              type: string
              example: "Validation failed"
            details:
              type: object
              additionalProperties: true
            trace_id:
              type: string
              format: uuid
              example: "abc123-def456-ghi789"
        meta:
          type: object
          properties:
            timestamp:
              type: string
              format: date-time
            api_version:
              type: string
              example: "1.0.0"

    PaginationMeta:
      type: object
      properties:
        total_count:
          type: integer
          minimum: 0
          example: 150
        page:
          type: integer
          minimum: 1
          example: 1
        page_size:
          type: integer
          minimum: 1
          maximum: 1000
          example: 20
        total_pages:
          type: integer
          minimum: 1
          example: 8

  responses:
    BadRequest:
      description: Ungültige Anfrage - Validierungsfehler
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: "VALIDATION_ERROR"
              message: "Request validation failed"
              details:
                field_errors:
                  name: "Field is required"
                  amount: "Must be positive number"
    
    Unauthorized:
      description: Nicht autorisiert - Authentifizierung erforderlich
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: "UNAUTHORIZED"
              message: "Authentication required"
    
    NotFound:
      description: Ressource nicht gefunden
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: "NOT_FOUND"
              message: "Portfolio not found"
    
    Conflict:
      description: Konflikt - Ressource bereits vorhanden oder Zustandskonflikt
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: "CONFLICT"
              message: "Portfolio with this name already exists"
    
    InternalServerError:
      description: Interner Serverfehler
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: "INTERNAL_SERVER_ERROR"
              message: "An unexpected error occurred"

  parameters:
    PortfolioId:
      name: portfolio_id
      in: path
      required: true
      schema:
        type: string
        format: uuid
      description: Eindeutige Portfolio-ID
      example: "123e4567-e89b-12d3-a456-426614174000"
    
    AssetSymbol:
      name: asset_symbol
      in: path
      required: true
      schema:
        type: string
      description: Asset-Symbol
      example: "AAPL"
```

### 2.2 **Broker Gateway Service API**
```yaml
# services/broker-gateway-service/openapi.yaml
openapi: 3.1.0
info:
  title: Aktienanalyse Broker Gateway Service API
  description: |
    Broker-Integration für Trading-Operationen, Market-Data und Execution-Management.
    
    ## Features
    - Multi-Broker-Integration (Bitpanda Pro, weitere)
    - Order-Management mit verschiedenen Order-Types
    - Real-time Market-Data-Feeds
    - Position-Tracking und Reconciliation
    
  version: 1.0.0

servers:
  - url: http://127.0.0.1:8002/api/v1
    description: Local Development Server

security:
  - ApiKeyAuth: []

paths:
  # Order Management
  /orders:
    get:
      tags: [Order Management]
      summary: Liste aller Orders
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [pending, partially_filled, filled, cancelled, rejected]
        - name: portfolio_id
          in: query
          schema:
            type: string
            format: uuid
        - name: asset_symbol
          in: query
          schema:
            type: string
        - name: from_date
          in: query
          schema:
            type: string
            format: date
        - name: to_date
          in: query
          schema:
            type: string
            format: date
      responses:
        '200':
          description: Order-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Order'
    
    post:
      tags: [Order Management]
      summary: Neue Order erstellen
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateOrderRequest'
      responses:
        '201':
          description: Order erfolgreich erstellt
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/Order'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          $ref: '#/components/responses/Conflict'

  /orders/{order_id}:
    get:
      tags: [Order Management]
      summary: Order-Details abrufen
      parameters:
        - name: order_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Order-Details
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/OrderDetails'
    
    delete:
      tags: [Order Management]
      summary: Order stornieren
      parameters:
        - name: order_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Order erfolgreich storniert
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/CancelOrderResult'

  # Market Data
  /market-data/{asset_symbol}/price:
    get:
      tags: [Market Data]
      summary: Aktueller Asset-Preis
      parameters:
        - name: asset_symbol
          in: path
          required: true
          schema:
            type: string
          example: "AAPL"
      responses:
        '200':
          description: Aktueller Preis
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/AssetPrice'

  /market-data/{asset_symbol}/historical:
    get:
      tags: [Market Data]
      summary: Historische Kursdaten
      parameters:
        - name: asset_symbol
          in: path
          required: true
          schema:
            type: string
        - name: from_date
          in: query
          required: true
          schema:
            type: string
            format: date
        - name: to_date
          in: query
          required: true
          schema:
            type: string
            format: date
        - name: interval
          in: query
          schema:
            type: string
            enum: [1m, 5m, 15m, 1h, 1d]
            default: "1d"
      responses:
        '200':
          description: Historische Kursdaten
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/HistoricalData'

  # Positions
  /positions:
    get:
      tags: [Position Management]
      summary: Aktuelle Positionen
      parameters:
        - name: portfolio_id
          in: query
          schema:
            type: string
            format: uuid
        - name: broker
          in: query
          schema:
            type: string
          description: Filter nach Broker
      responses:
        '200':
          description: Position-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/BrokerPosition'

components:
  schemas:
    Order:
      type: object
      required: [order_id, portfolio_id, asset_symbol, side, order_type, quantity, status]
      properties:
        order_id:
          type: string
          format: uuid
        portfolio_id:
          type: string
          format: uuid
        asset_symbol:
          type: string
          example: "AAPL"
        side:
          type: string
          enum: [buy, sell]
        order_type:
          type: string
          enum: [market, limit, stop, stop_limit]
        quantity:
          type: number
          format: float
          minimum: 0
        price:
          type: number
          format: float
          minimum: 0
          description: "Limit/Stop-Preis (optional für Market-Orders)"
        status:
          type: string
          enum: [pending, partially_filled, filled, cancelled, rejected]
        filled_quantity:
          type: number
          format: float
          minimum: 0
          default: 0
        average_fill_price:
          type: number
          format: float
          minimum: 0
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        broker:
          type: string
          example: "bitpanda_pro"
        broker_order_id:
          type: string
          description: "Order-ID beim Broker"

    CreateOrderRequest:
      type: object
      required: [portfolio_id, asset_symbol, side, order_type, quantity]
      properties:
        portfolio_id:
          type: string
          format: uuid
        asset_symbol:
          type: string
          example: "AAPL"
        side:
          type: string
          enum: [buy, sell]
        order_type:
          type: string
          enum: [market, limit, stop, stop_limit]
        quantity:
          type: number
          format: float
          minimum: 0.000001
        price:
          type: number
          format: float
          minimum: 0
          description: "Erforderlich für Limit/Stop-Orders"
        stop_price:
          type: number
          format: float
          minimum: 0
          description: "Erforderlich für Stop-Limit-Orders"
        time_in_force:
          type: string
          enum: [GTC, IOC, FOK, DAY]
          default: "GTC"
          description: "Good Till Cancelled, Immediate or Cancel, Fill or Kill, Day"
        dry_run:
          type: boolean
          default: false
          description: "Nur Validierung, keine tatsächliche Order"

    AssetPrice:
      type: object
      properties:
        asset_symbol:
          type: string
          example: "AAPL"
        price:
          type: number
          format: float
          example: 155.50
        currency:
          type: string
          example: "USD"
        timestamp:
          type: string
          format: date-time
        bid:
          type: number
          format: float
        ask:
          type: number
          format: float
        spread:
          type: number
          format: float
        volume_24h:
          type: number
          format: float
        change_24h:
          type: number
          format: float
        change_24h_percent:
          type: number
          format: float

    BrokerPosition:
      type: object
      properties:
        position_id:
          type: string
        portfolio_id:
          type: string
          format: uuid
        asset_symbol:
          type: string
        quantity:
          type: number
          format: float
        average_price:
          type: number
          format: float
        current_price:
          type: number
          format: float
        market_value:
          type: number
          format: float
        unrealized_pnl:
          type: number
          format: float
        broker:
          type: string
        last_updated:
          type: string
          format: date-time
```

---

### 2.3 **Event Bus Service API**
```yaml
# services/event-bus-service/openapi.yaml
openapi: 3.1.0
info:
  title: Aktienanalyse Event Bus Service API
  description: |
    Event-Sourcing und Message-Queue für Inter-Service-Kommunikation.
    
    ## Features
    - Event-Store mit PostgreSQL-Backend
    - Redis-basierte Event-Distribution
    - Event-Replay und Time-Travel-Debugging
    - Event-Projections für Read-Models
    
  version: 1.0.0

servers:
  - url: http://127.0.0.1:8003/api/v1
    description: Local Development Server

security:
  - ApiKeyAuth: []

paths:
  # Event Management
  /events:
    get:
      tags: [Event Management]
      summary: Event-Stream abrufen
      parameters:
        - name: stream_name
          in: query
          schema:
            type: string
          description: Filter nach Event-Stream
        - name: event_type
          in: query
          schema:
            type: string
          description: Filter nach Event-Type
        - name: from_timestamp
          in: query
          schema:
            type: string
            format: date-time
          description: Ereignisse ab Zeitpunkt
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 1000
            default: 100
      responses:
        '200':
          description: Event-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Event'
                  meta:
                    $ref: '#/components/schemas/StreamMeta'
    
    post:
      tags: [Event Management]
      summary: Event publizieren
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PublishEventRequest'
      responses:
        '201':
          description: Event erfolgreich publiziert
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/EventResult'

  /events/{event_id}:
    get:
      tags: [Event Management]
      summary: Event-Details abrufen
      parameters:
        - name: event_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Event-Details
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/EventDetails'

  # Event Subscriptions
  /subscriptions:
    get:
      tags: [Subscriptions]
      summary: Aktive Subscriptions auflisten
      responses:
        '200':
          description: Subscription-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Subscription'
    
    post:
      tags: [Subscriptions]
      summary: Event-Subscription erstellen
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateSubscriptionRequest'
      responses:
        '201':
          description: Subscription erfolgreich erstellt
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/Subscription'

  /subscriptions/{subscription_id}:
    delete:
      tags: [Subscriptions]
      summary: Subscription löschen
      parameters:
        - name: subscription_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Subscription erfolgreich gelöscht
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean

  # Event Projections
  /projections:
    get:
      tags: [Projections]
      summary: Verfügbare Projections auflisten
      responses:
        '200':
          description: Projection-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Projection'

  /projections/{projection_name}/rebuild:
    post:
      tags: [Projections]
      summary: Projection neu aufbauen
      parameters:
        - name: projection_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '202':
          description: Projection-Rebuild gestartet
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/RebuildResult'

  # Event Replay
  /replay:
    post:
      tags: [Event Replay]
      summary: Event-Replay starten
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ReplayRequest'
      responses:
        '202':
          description: Replay erfolgreich gestartet
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/ReplayResult'

components:
  schemas:
    Event:
      type: object
      required: [event_id, stream_name, event_type, event_data, timestamp]
      properties:
        event_id:
          type: string
          format: uuid
        stream_name:
          type: string
          example: "portfolio-12345"
        event_type:
          type: string
          example: "PortfolioCreated"
        event_data:
          type: object
          description: "Event-spezifische Payload"
        metadata:
          type: object
          properties:
            user_id:
              type: string
            correlation_id:
              type: string
              format: uuid
            causation_id:
              type: string
              format: uuid
            version:
              type: integer
        timestamp:
          type: string
          format: date-time
        sequence_number:
          type: integer
          minimum: 1

    PublishEventRequest:
      type: object
      required: [stream_name, event_type, event_data]
      properties:
        stream_name:
          type: string
          pattern: "^[a-zA-Z0-9_-]+$"
          minLength: 1
          maxLength: 100
        event_type:
          type: string
          pattern: "^[A-Z][a-zA-Z0-9]+$"
          example: "PortfolioCreated"
        event_data:
          type: object
          description: "Event-Payload (muss Event-Schema entsprechen)"
        metadata:
          type: object
          properties:
            correlation_id:
              type: string
              format: uuid
            causation_id:
              type: string
              format: uuid
        expected_version:
          type: integer
          minimum: 0
          description: "Erwartete Stream-Version für Concurrency-Control"

    Subscription:
      type: object
      properties:
        subscription_id:
          type: string
          format: uuid
        subscriber_name:
          type: string
          example: "portfolio-service"
        event_types:
          type: array
          items:
            type: string
          example: ["PortfolioCreated", "PortfolioUpdated"]
        stream_patterns:
          type: array
          items:
            type: string
          example: ["portfolio-*", "trading-*"]
        webhook_url:
          type: string
          format: uri
          example: "http://127.0.0.1:8001/webhooks/events"
        delivery_mode:
          type: string
          enum: [push, pull]
          default: push
        created_at:
          type: string
          format: date-time
        last_delivered_event:
          type: string
          format: uuid

    CreateSubscriptionRequest:
      type: object
      required: [subscriber_name, event_types]
      properties:
        subscriber_name:
          type: string
          pattern: "^[a-zA-Z0-9_-]+$"
          minLength: 1
          maxLength: 50
        event_types:
          type: array
          items:
            type: string
          minItems: 1
        stream_patterns:
          type: array
          items:
            type: string
        webhook_url:
          type: string
          format: uri
        delivery_mode:
          type: string
          enum: [push, pull]
          default: push

    Projection:
      type: object
      properties:
        projection_name:
          type: string
          example: "portfolio-read-model"
        status:
          type: string
          enum: [running, stopped, rebuilding, error]
        last_processed_event:
          type: string
          format: uuid
        events_processed:
          type: integer
        last_updated:
          type: string
          format: date-time
        lag_seconds:
          type: number
          format: float
          description: "Verzögerung zur aktuellen Event-Time"

    ReplayRequest:
      type: object
      required: [from_timestamp, to_timestamp]
      properties:
        from_timestamp:
          type: string
          format: date-time
        to_timestamp:
          type: string
          format: date-time
        stream_patterns:
          type: array
          items:
            type: string
          example: ["portfolio-*"]
        event_types:
          type: array
          items:
            type: string
        target_subscriber:
          type: string
          description: "Replay nur an spezifischen Subscriber"
        replay_speed:
          type: number
          format: float
          minimum: 0.1
          maximum: 10.0
          default: 1.0
          description: "Replay-Geschwindigkeit (1.0 = Realzeit)"

    StreamMeta:
      type: object
      properties:
        total_events:
          type: integer
        stream_version:
          type: integer
        oldest_event_timestamp:
          type: string
          format: date-time
        newest_event_timestamp:
          type: string
          format: date-time
```

### 2.4 **Monitoring Service API**
```yaml
# services/monitoring-service/openapi.yaml
openapi: 3.1.0
info:
  title: Aktienanalyse Monitoring Service API
  description: |
    System-Monitoring, Metrics und Health-Checks für das aktienanalyse-ökosystem.
    
    ## Features
    - Real-time System-Metrics
    - Service-Health-Monitoring
    - Alert-Management
    - Performance-Dashboards
    
  version: 1.0.0

servers:
  - url: http://127.0.0.1:8004/api/v1
    description: Local Development Server

security:
  - ApiKeyAuth: []

paths:
  # System Metrics
  /metrics:
    get:
      tags: [Metrics]
      summary: System-Metrics abrufen
      parameters:
        - name: metric_type
          in: query
          schema:
            type: string
            enum: [system, business, technical, security]
        - name: from_time
          in: query
          schema:
            type: string
            format: date-time
        - name: to_time
          in: query
          schema:
            type: string
            format: date-time
        - name: resolution
          in: query
          schema:
            type: string
            enum: [1m, 5m, 15m, 1h, 1d]
            default: "5m"
      responses:
        '200':
          description: Metrics-Daten
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/MetricsResponse'

  /metrics/prometheus:
    get:
      tags: [Metrics]
      summary: Prometheus-Format Metrics
      description: "Metrics im Prometheus-Format für Scraping"
      responses:
        '200':
          description: Prometheus-Metrics
          content:
            text/plain:
              schema:
                type: string
                example: |
                  # HELP aktienanalyse_portfolio_total_value Total portfolio value in EUR
                  # TYPE aktienanalyse_portfolio_total_value gauge
                  aktienanalyse_portfolio_total_value{portfolio_id="123"} 50000.00

  # Health Checks
  /health:
    get:
      tags: [Health]
      summary: Gesamt-System-Health
      responses:
        '200':
          description: System ist gesund
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
        '503':
          description: System hat Probleme
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /health/services:
    get:
      tags: [Health]
      summary: Health-Status aller Services
      responses:
        '200':
          description: Service-Health-Status
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/ServiceHealth'

  /health/{service_name}:
    get:
      tags: [Health]
      summary: Health-Check für spezifischen Service
      parameters:
        - name: service_name
          in: path
          required: true
          schema:
            type: string
            enum: [core, broker, event-bus, frontend, database, redis]
      responses:
        '200':
          description: Service-Health-Details
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/ServiceHealthDetails'

  # Alerts
  /alerts:
    get:
      tags: [Alerts]
      summary: Aktive Alerts auflisten
      parameters:
        - name: severity
          in: query
          schema:
            type: string
            enum: [low, medium, high, critical]
        - name: status
          in: query
          schema:
            type: string
            enum: [active, acknowledged, resolved]
        - name: service
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Alert-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Alert'

  /alerts/{alert_id}/acknowledge:
    post:
      tags: [Alerts]
      summary: Alert bestätigen
      parameters:
        - name: alert_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                acknowledged_by:
                  type: string
                notes:
                  type: string
      responses:
        '200':
          description: Alert erfolgreich bestätigt
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean

  # Dashboards
  /dashboards:
    get:
      tags: [Dashboards]
      summary: Verfügbare Dashboards auflisten
      responses:
        '200':
          description: Dashboard-Liste
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Dashboard'

  /dashboards/{dashboard_id}/data:
    get:
      tags: [Dashboards]
      summary: Dashboard-Daten abrufen
      parameters:
        - name: dashboard_id
          in: path
          required: true
          schema:
            type: string
        - name: time_range
          in: query
          schema:
            type: string
            enum: [1h, 6h, 24h, 7d, 30d]
            default: "24h"
      responses:
        '200':
          description: Dashboard-Daten
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/DashboardData'

components:
  schemas:
    MetricsResponse:
      type: object
      properties:
        timestamp_from:
          type: string
          format: date-time
        timestamp_to:
          type: string
          format: date-time
        resolution:
          type: string
        metrics:
          type: object
          additionalProperties:
            type: array
            items:
              $ref: '#/components/schemas/MetricDataPoint'

    MetricDataPoint:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        value:
          type: number
          format: float
        labels:
          type: object
          additionalProperties:
            type: string

    HealthResponse:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time
        version:
          type: string
        uptime_seconds:
          type: integer
        checks:
          type: object
          additionalProperties:
            $ref: '#/components/schemas/HealthCheck'

    HealthCheck:
      type: object
      properties:
        status:
          type: string
          enum: [pass, warn, fail]
        last_checked:
          type: string
          format: date-time
        response_time_ms:
          type: number
        message:
          type: string

    ServiceHealth:
      type: object
      properties:
        service_name:
          type: string
        status:
          type: string
          enum: [healthy, degraded, unhealthy, unknown]
        last_heartbeat:
          type: string
          format: date-time
        response_time_ms:
          type: number
        error_rate_percent:
          type: number
          format: float
        cpu_usage_percent:
          type: number
          format: float
        memory_usage_mb:
          type: number
        version:
          type: string

    Alert:
      type: object
      properties:
        alert_id:
          type: string
          format: uuid
        rule_name:
          type: string
        severity:
          type: string
          enum: [low, medium, high, critical]
        status:
          type: string
          enum: [active, acknowledged, resolved]
        message:
          type: string
        service:
          type: string
        metric:
          type: string
        threshold:
          type: number
        current_value:
          type: number
        triggered_at:
          type: string
          format: date-time
        acknowledged_at:
          type: string
          format: date-time
        acknowledged_by:
          type: string
        resolved_at:
          type: string
          format: date-time

    Dashboard:
      type: object
      properties:
        dashboard_id:
          type: string
        title:
          type: string
        description:
          type: string
        category:
          type: string
          enum: [system, business, trading, security]
        widgets:
          type: array
          items:
            $ref: '#/components/schemas/DashboardWidget'

    DashboardWidget:
      type: object
      properties:
        widget_id:
          type: string
        title:
          type: string
        type:
          type: string
          enum: [line_chart, bar_chart, gauge, counter, table]
        metrics:
          type: array
          items:
            type: string
        position:
          type: object
          properties:
            x:
              type: integer
            y:
              type: integer
            width:
              type: integer
            height:
              type: integer
```

### 2.5 **Frontend Service API**
```yaml
# services/frontend-service/openapi.yaml
openapi: 3.1.0
info:
  title: Aktienanalyse Frontend Service API
  description: |
    Frontend-API und WebSocket-Gateway für die Benutzeroberfläche.
    
    ## Features
    - API-Proxy für Backend-Services
    - WebSocket-Gateway für Real-time-Updates
    - Configuration-Management-Interface
    - Session-Management
    
  version: 1.0.0

servers:
  - url: https://127.0.0.1:8443/api/v1
    description: Local HTTPS Server (NGINX-Only)

security:
  - SessionAuth: []

paths:
  # Authentication
  /auth/login:
    post:
      tags: [Authentication]
      summary: Benutzer-Anmeldung
      security: []  # No auth required for login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Anmeldung erfolgreich
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/AuthResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'

  /auth/logout:
    post:
      tags: [Authentication]
      summary: Benutzer-Abmeldung
      responses:
        '200':
          description: Abmeldung erfolgreich
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean

  /auth/status:
    get:
      tags: [Authentication]
      summary: Authentifizierungs-Status prüfen
      responses:
        '200':
          description: Authentifizierungs-Status
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/AuthStatus'

  # API Proxy
  /proxy/{service}/{path}:
    get:
      tags: [API Proxy]
      summary: GET-Request an Backend-Service
      parameters:
        - name: service
          in: path
          required: true
          schema:
            type: string
            enum: [core, broker, event-bus, monitoring]
        - name: path
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Proxy-Response
          content:
            application/json:
              schema:
                type: object
        '503':
          description: Backend-Service nicht verfügbar
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
    
    post:
      tags: [API Proxy]
      summary: POST-Request an Backend-Service
      parameters:
        - name: service
          in: path
          required: true
          schema:
            type: string
            enum: [core, broker, event-bus, monitoring]
        - name: path
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: Proxy-Response
          content:
            application/json:
              schema:
                type: object

  # WebSocket Gateway
  /websocket/connect:
    get:
      tags: [WebSocket]
      summary: WebSocket-Verbindung aufbauen
      description: "Upgrade zu WebSocket-Verbindung für Real-time-Updates"
      responses:
        '101':
          description: "WebSocket-Upgrade erfolgreich"
        '400':
          description: "WebSocket-Upgrade fehlgeschlagen"

  # Configuration Management
  /configuration:
    get:
      tags: [Configuration]
      summary: Aktuelle Konfiguration abrufen
      responses:
        '200':
          description: Konfigurationsdaten
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    $ref: '#/components/schemas/ConfigurationData'

  /configuration/{section}:
    get:
      tags: [Configuration]
      summary: Konfiguration für spezifischen Bereich
      parameters:
        - name: section
          in: path
          required: true
          schema:
            type: string
            enum: [risk_management, trading_rules, notifications, display]
      responses:
        '200':
          description: Bereichs-Konfiguration
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object
    
    put:
      tags: [Configuration]
      summary: Konfiguration aktualisieren
      parameters:
        - name: section
          in: path
          required: true
          schema:
            type: string
            enum: [risk_management, trading_rules, notifications, display]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
      responses:
        '200':
          description: Konfiguration erfolgreich aktualisiert
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  data:
                    type: object

components:
  securitySchemes:
    SessionAuth:
      type: apiKey
      in: cookie
      name: session_id

  schemas:
    LoginRequest:
      type: object
      required: [username, password]
      properties:
        username:
          type: string
          minLength: 1
        password:
          type: string
          minLength: 1
        remember_me:
          type: boolean
          default: false

    AuthResponse:
      type: object
      properties:
        user:
          type: object
          properties:
            username:
              type: string
            display_name:
              type: string
            roles:
              type: array
              items:
                type: string
        session:
          type: object
          properties:
            session_id:
              type: string
            expires_at:
              type: string
              format: date-time

    AuthStatus:
      type: object
      properties:
        authenticated:
          type: boolean
        user:
          type: object
          properties:
            username:
              type: string
            display_name:
              type: string
        session_expires_at:
          type: string
          format: date-time

    ConfigurationData:
      type: object
      properties:
        risk_management:
          type: object
          properties:
            max_position_size_percent:
              type: number
              format: float
            stop_loss_percent:
              type: number
              format: float
            daily_loss_limit_eur:
              type: number
              format: float
        trading_rules:
          type: object
          properties:
            auto_rebalancing_enabled:
              type: boolean
            rebalancing_threshold_percent:
              type: number
              format: float
            min_trade_amount_eur:
              type: number
              format: float
        notifications:
          type: object
          properties:
            email_alerts_enabled:
              type: boolean
            alert_thresholds:
              type: object
        display:
          type: object
          properties:
            theme:
              type: string
              enum: [light, dark, auto]
            language:
              type: string
              enum: [de, en]
            currency_display:
              type: string
              enum: [EUR, USD]
```

---

## 🔗 **3. WEBSOCKET-EVENT-PROTOKOLLE**

### 3.1 **WebSocket-Event-Schema-Definition**
```yaml
# config/websocket-event-schemas.yaml

websocket_events:
  # Portfolio-Events
  portfolio_updated:
    schema:
      type: object
      required: [event_type, data, timestamp]
      properties:
        event_type:
          type: string
          const: "portfolio_updated"
        data:
          type: object
          required: [portfolio_id, total_value, positions]
          properties:
            portfolio_id:
              type: string
              format: uuid
            total_value:
              type: number
              format: float
            cash_balance:
              type: number
              format: float
            positions:
              type: array
              items:
                type: object
                required: [asset_symbol, quantity, current_price, market_value]
                properties:
                  asset_symbol:
                    type: string
                  quantity:
                    type: number
                    format: float
                  current_price:
                    type: number
                    format: float
                  market_value:
                    type: number
                    format: float
                  unrealized_pnl:
                    type: number
                    format: float
        timestamp:
          type: string
          format: date-time
        correlation_id:
          type: string
          format: uuid
    
    frequency: "real_time"
    target_clients: ["portfolio_dashboard", "position_monitor"]
    
  # Trading-Events
  order_status_changed:
    schema:
      type: object
      required: [event_type, data, timestamp]
      properties:
        event_type:
          type: string
          const: "order_status_changed"
        data:
          type: object
          required: [order_id, old_status, new_status]
          properties:
            order_id:
              type: string
              format: uuid
            portfolio_id:
              type: string
              format: uuid
            asset_symbol:
              type: string
            old_status:
              type: string
              enum: [pending, partially_filled, filled, cancelled, rejected]
            new_status:
              type: string
              enum: [pending, partially_filled, filled, cancelled, rejected]
            filled_quantity:
              type: number
              format: float
            average_fill_price:
              type: number
              format: float
            remaining_quantity:
              type: number
              format: float
        timestamp:
          type: string
          format: date-time
    
    frequency: "immediate"
    target_clients: ["trading_dashboard", "order_monitor"]
    
  # Market-Data-Events
  price_update:
    schema:
      type: object
      required: [event_type, data, timestamp]
      properties:
        event_type:
          type: string
          const: "price_update"
        data:
          type: object
          required: [asset_symbol, price, change_percent]
          properties:
            asset_symbol:
              type: string
            price:
              type: number
              format: float
            currency:
              type: string
            change_24h:
              type: number
              format: float
            change_percent:
              type: number
              format: float
            volume_24h:
              type: number
              format: float
            bid:
              type: number
              format: float
            ask:
              type: number
              format: float
        timestamp:
          type: string
          format: date-time
    
    frequency: "5_seconds"
    target_clients: ["price_monitor", "trading_dashboard"]
    
  # Risk-Alert-Events
  risk_alert:
    schema:
      type: object
      required: [event_type, data, timestamp]
      properties:
        event_type:
          type: string
          const: "risk_alert"
        data:
          type: object
          required: [alert_type, severity, message]
          properties:
            alert_type:
              type: string
              enum: [position_limit, daily_loss, concentration_risk, margin_call]
            severity:
              type: string
              enum: [low, medium, high, critical]
            message:
              type: string
            portfolio_id:
              type: string
              format: uuid
            affected_positions:
              type: array
              items:
                type: string
            threshold_value:
              type: number
              format: float
            current_value:
              type: number
              format: float
            recommended_action:
              type: string
        timestamp:
          type: string
          format: date-time
    
    frequency: "immediate"
    target_clients: ["risk_dashboard", "alert_center"]
    
  # System-Health-Events
  system_health_update:
    schema:
      type: object
      required: [event_type, data, timestamp]
      properties:
        event_type:
          type: string
          const: "system_health_update"
        data:
          type: object
          required: [overall_status, services]
          properties:
            overall_status:
              type: string
              enum: [healthy, degraded, unhealthy]
            services:
              type: object
              additionalProperties:
                type: object
                properties:
                  status:
                    type: string
                    enum: [healthy, degraded, unhealthy]
                  response_time_ms:
                    type: number
                  error_rate_percent:
                    type: number
                    format: float
                  last_check:
                    type: string
                    format: date-time
        timestamp:
          type: string
          format: date-time
    
    frequency: "30_seconds"
    target_clients: ["system_dashboard", "monitoring_center"]

# Client-Subscription-Management
client_subscriptions:
  portfolio_dashboard:
    subscribed_events:
      - portfolio_updated
      - order_status_changed
      - risk_alert
    filters:
      portfolio_id: "${user.portfolio_id}"
    
  trading_dashboard:
    subscribed_events:
      - order_status_changed
      - price_update
      - risk_alert
    filters:
      portfolio_id: "${user.portfolio_id}"
    
  system_dashboard:
    subscribed_events:
      - system_health_update
    filters: {}
    
  price_monitor:
    subscribed_events:
      - price_update
    filters:
      asset_symbols: ["${user.watched_assets}"]
```

### 3.2 **WebSocket-Gateway-Implementation**
```python
# services/frontend-service/src/websocket_gateway.py
import asyncio
import json
import logging
from typing import Dict, Set, List, Optional
from datetime import datetime
import websockets
import redis.asyncio as redis
from jsonschema import validate, ValidationError

class WebSocketGateway:
    def __init__(self):
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.redis_client = None
        self.event_schemas = self._load_event_schemas()
        
    async def start_gateway(self, host: str = "127.0.0.1", port: int = 8445):
        """Startet WebSocket-Gateway"""
        
        # Redis-Verbindung für Event-Subscription
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )
        
        # Event-Subscription Task starten
        asyncio.create_task(self._subscribe_to_events())
        
        # WebSocket-Server starten
        logging.info(f"🔌 Starting WebSocket Gateway on {host}:{port}")
        
        async with websockets.serve(
            self._handle_client_connection,
            host,
            port,
            ping_interval=30,
            ping_timeout=10
        ):
            await asyncio.Future()  # Run forever
    
    async def _handle_client_connection(self, websocket, path):
        """Behandelt neue Client-Verbindungen"""
        
        client_id = f"client_{id(websocket)}"
        self.clients[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        
        logging.info(f"📱 Client {client_id} connected")
        
        try:
            # Welcome-Message senden
            await self._send_to_client(client_id, {
                "event_type": "connection_established",
                "data": {
                    "client_id": client_id,
                    "server_time": datetime.utcnow().isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Client-Messages verarbeiten
            async for message in websocket:
                await self._handle_client_message(client_id, message)
                
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"📱 Client {client_id} disconnected")
        except Exception as e:
            logging.error(f"❌ Error handling client {client_id}: {e}")
        finally:
            # Cleanup
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]
    
    async def _handle_client_message(self, client_id: str, message: str):
        """Verarbeitet Nachrichten von Clients"""
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe":
                await self._handle_subscription(client_id, data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscription(client_id, data)
            elif message_type == "ping":
                await self._send_to_client(client_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                await self._send_error_to_client(client_id, "unknown_message_type")
                
        except json.JSONDecodeError:
            await self._send_error_to_client(client_id, "invalid_json")
        except Exception as e:
            logging.error(f"❌ Error processing message from {client_id}: {e}")
            await self._send_error_to_client(client_id, "processing_error")
    
    async def _handle_subscription(self, client_id: str, data: dict):
        """Behandelt Event-Subscriptions"""
        
        event_types = data.get("event_types", [])
        filters = data.get("filters", {})
        
        for event_type in event_types:
            if event_type in self.event_schemas:
                self.client_subscriptions[client_id].add(event_type)
                
                # Redis-Subscription für Event-Type
                await self.redis_client.subscribe(f"events:{event_type}")
                
                logging.info(f"📡 Client {client_id} subscribed to {event_type}")
        
        # Bestätigung senden
        await self._send_to_client(client_id, {
            "type": "subscription_confirmed",
            "data": {
                "subscribed_events": list(self.client_subscriptions[client_id])
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _subscribe_to_events(self):
        """Abonniert Redis-Event-Channels"""
        
        pubsub = self.redis_client.pubsub()
        
        # Alle Event-Types abonnieren
        for event_type in self.event_schemas.keys():
            await pubsub.subscribe(f"events:{event_type}")
        
        logging.info(f"📡 Subscribed to {len(self.event_schemas)} event types")
        
        # Event-Loop
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self._process_redis_event(message)
    
    async def _process_redis_event(self, redis_message):
        """Verarbeitet Events aus Redis und leitet sie an Clients weiter"""
        
        try:
            # Event-Data parsen
            event_data = json.loads(redis_message["data"])
            event_type = event_data.get("event_type")
            
            # Event-Schema validieren
            if event_type in self.event_schemas:
                validate(event_data, self.event_schemas[event_type]["schema"])
                
                # An subscribte Clients weiterleiten
                await self._broadcast_event_to_subscribers(event_type, event_data)
            
        except (json.JSONDecodeError, ValidationError) as e:
            logging.error(f"❌ Invalid event received: {e}")
        except Exception as e:
            logging.error(f"❌ Error processing Redis event: {e}")
    
    async def _broadcast_event_to_subscribers(self, event_type: str, event_data: dict):
        """Sendet Event an alle subscribten Clients"""
        
        subscribers = [
            client_id for client_id, subscriptions in self.client_subscriptions.items()
            if event_type in subscriptions
        ]
        
        if subscribers:
            # Parallel an alle Subscribers senden
            await asyncio.gather(*[
                self._send_to_client(client_id, event_data)
                for client_id in subscribers
            ], return_exceptions=True)
            
            logging.debug(f"📨 Broadcasted {event_type} to {len(subscribers)} clients")
    
    async def _send_to_client(self, client_id: str, data: dict):
        """Sendet Daten an spezifischen Client"""
        
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(data))
            except websockets.exceptions.ConnectionClosed:
                # Client disconnected
                if client_id in self.clients:
                    del self.clients[client_id]
                if client_id in self.client_subscriptions:
                    del self.client_subscriptions[client_id]
            except Exception as e:
                logging.error(f"❌ Error sending to client {client_id}: {e}")
    
    async def _send_error_to_client(self, client_id: str, error_code: str):
        """Sendet Fehlermeldung an Client"""
        
        await self._send_to_client(client_id, {
            "type": "error",
            "data": {
                "code": error_code,
                "message": self._get_error_message(error_code)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _get_error_message(self, error_code: str) -> str:
        """Gibt Fehlermeldung für Error-Code zurück"""
        
        error_messages = {
            "unknown_message_type": "Unknown message type",
            "invalid_json": "Invalid JSON format",
            "processing_error": "Error processing message",
            "subscription_failed": "Subscription failed",
            "unauthorized": "Unauthorized access"
        }
        
        return error_messages.get(error_code, "Unknown error")
    
    def _load_event_schemas(self) -> Dict:
        """Lädt Event-Schemas aus Konfigurationsdatei"""
        
        import yaml
        
        try:
            with open("/home/mdoehler/aktienanalyse-ökosystem/config/websocket-event-schemas.yaml", "r") as f:
                config = yaml.safe_load(f)
                return config.get("websocket_events", {})
        except Exception as e:
            logging.error(f"❌ Error loading event schemas: {e}")
            return {}

# WebSocket-Client-Integration (Frontend)
class WebSocketClient:
    """JavaScript WebSocket-Client-Beispiel für Frontend-Integration"""
    
    def get_client_code(self) -> str:
        return """
        class AktienAnalyseWebSocket {
            constructor(url = 'wss://localhost/websocket/connect') {
                this.url = url;
                this.ws = null;
                this.subscriptions = new Set();
                this.eventHandlers = new Map();
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
            }
            
            connect() {
                this.ws = new WebSocket(this.url);
                
                this.ws.onopen = () => {
                    console.log('🔌 WebSocket connected');
                    this.reconnectAttempts = 0;
                    
                    // Re-subscribe to previous subscriptions
                    if (this.subscriptions.size > 0) {
                        this.subscribe([...this.subscriptions]);
                    }
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    } catch (e) {
                        console.error('❌ Error parsing WebSocket message:', e);
                    }
                };
                
                this.ws.onclose = () => {
                    console.log('🔌 WebSocket disconnected');
                    this.attemptReconnect();
                };
                
                this.ws.onerror = (error) => {
                    console.error('❌ WebSocket error:', error);
                };
            }
            
            subscribe(eventTypes, filters = {}) {
                eventTypes.forEach(type => this.subscriptions.add(type));
                
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'subscribe',
                        event_types: eventTypes,
                        filters: filters
                    }));
                }
            }
            
            on(eventType, handler) {
                if (!this.eventHandlers.has(eventType)) {
                    this.eventHandlers.set(eventType, []);
                }
                this.eventHandlers.get(eventType).push(handler);
            }
            
            handleMessage(data) {
                const eventType = data.event_type || data.type;
                
                if (this.eventHandlers.has(eventType)) {
                    this.eventHandlers.get(eventType).forEach(handler => {
                        try {
                            handler(data);
                        } catch (e) {
                            console.error(`❌ Error in event handler for ${eventType}:`, e);
                        }
                    });
                }
            }
            
            attemptReconnect() {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = Math.pow(2, this.reconnectAttempts) * 1000;
                    
                    console.log(`🔄 Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);
                    
                    setTimeout(() => {
                        this.connect();
                    }, delay);
                }
            }
        }
        
        // Usage Example:
        const ws = new AktienAnalyseWebSocket();
        
        // Subscribe to portfolio updates
        ws.on('portfolio_updated', (data) => {
            console.log('📊 Portfolio updated:', data.data);
            updatePortfolioDashboard(data.data);
        });
        
        // Subscribe to price updates
        ws.on('price_update', (data) => {
            console.log('💰 Price update:', data.data);
            updatePriceDisplay(data.data);
        });
        
        // Subscribe to risk alerts
        ws.on('risk_alert', (data) => {
            console.log('⚠️ Risk alert:', data.data);
            showRiskAlert(data.data);
        });
        
        ws.connect();
        ws.subscribe(['portfolio_updated', 'price_update', 'risk_alert']);
        """

if __name__ == "__main__":
    import asyncio
    
    gateway = WebSocketGateway()
    asyncio.run(gateway.start_gateway())
```

---

## 📋 **4. EVENT-SCHEMA-VALIDIERUNG**

### 4.1 **JSON-Schema-Definitionen für alle Event-Types**
```yaml
# config/event-schemas.yaml

event_schemas:
  # Portfolio-Domain Events
  PortfolioCreated:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [portfolio_id, name, currency, initial_cash, risk_profile]
    properties:
      portfolio_id:
        type: string
        format: uuid
        description: "Eindeutige Portfolio-ID"
      name:
        type: string
        minLength: 1
        maxLength: 100
        description: "Portfolio-Name"
      description:
        type: string
        maxLength: 500
      currency:
        type: string
        enum: ["EUR", "USD"]
      initial_cash:
        type: number
        minimum: 0
        description: "Initiales Cash-Guthaben"
      risk_profile:
        type: string
        enum: ["conservative", "moderate", "aggressive"]
      target_allocation:
        type: object
        additionalProperties:
          type: number
          minimum: 0
          maximum: 100
      created_by:
        type: string
        description: "User-ID des Erstellers"
    additionalProperties: false

  PortfolioUpdated:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [portfolio_id, updated_fields]
    properties:
      portfolio_id:
        type: string
        format: uuid
      updated_fields:
        type: object
        minProperties: 1
        properties:
          name:
            type: string
            minLength: 1
            maxLength: 100
          description:
            type: string
            maxLength: 500
          risk_profile:
            type: string
            enum: ["conservative", "moderate", "aggressive"]
          target_allocation:
            type: object
            additionalProperties:
              type: number
              minimum: 0
              maximum: 100
      previous_values:
        type: object
        description: "Vorherige Werte für Audit-Trail"
      updated_by:
        type: string
    additionalProperties: false

  # Trading-Domain Events
  OrderCreated:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [order_id, portfolio_id, asset_symbol, side, order_type, quantity]
    properties:
      order_id:
        type: string
        format: uuid
      portfolio_id:
        type: string
        format: uuid
      asset_symbol:
        type: string
        pattern: "^[A-Z0-9]{1,12}$"
      side:
        type: string
        enum: ["buy", "sell"]
      order_type:
        type: string
        enum: ["market", "limit", "stop", "stop_limit"]
      quantity:
        type: number
        minimum: 0.000001
      price:
        type: number
        minimum: 0
        description: "Preis für Limit/Stop-Orders"
      stop_price:
        type: number
        minimum: 0
        description: "Stop-Preis für Stop-Limit-Orders"
      time_in_force:
        type: string
        enum: ["GTC", "IOC", "FOK", "DAY"]
        default: "GTC"
      broker:
        type: string
        description: "Ziel-Broker für Ausführung"
      created_by:
        type: string
    additionalProperties: false

  OrderStatusChanged:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [order_id, old_status, new_status]
    properties:
      order_id:
        type: string
        format: uuid
      old_status:
        type: string
        enum: ["pending", "partially_filled", "filled", "cancelled", "rejected"]
      new_status:
        type: string
        enum: ["pending", "partially_filled", "filled", "cancelled", "rejected"]
      filled_quantity:
        type: number
        minimum: 0
        description: "Bisher ausgeführte Menge"
      average_fill_price:
        type: number
        minimum: 0
        description: "Durchschnittlicher Ausführungspreis"
      remaining_quantity:
        type: number
        minimum: 0
      broker_order_id:
        type: string
        description: "Order-ID beim Broker"
      rejection_reason:
        type: string
        description: "Grund für Rejection (falls new_status = rejected)"
      execution_fees:
        type: number
        minimum: 0
    additionalProperties: false

  # Risk-Management Events
  RiskLimitExceeded:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [portfolio_id, limit_type, threshold_value, current_value, severity]
    properties:
      portfolio_id:
        type: string
        format: uuid
      limit_type:
        type: string
        enum: ["position_size", "daily_loss", "total_exposure", "concentration", "drawdown"]
      threshold_value:
        type: number
        description: "Konfigurierter Grenzwert"
      current_value:
        type: number
        description: "Aktueller Wert"
      severity:
        type: string
        enum: ["warning", "critical", "emergency"]
      affected_positions:
        type: array
        items:
          type: string
        description: "Liste der betroffenen Asset-Symbole"
      recommended_actions:
        type: array
        items:
          type: string
        description: "Empfohlene Maßnahmen"
      auto_actions_taken:
        type: array
        items:
          type: object
          properties:
            action_type:
              type: string
              enum: ["order_cancelled", "position_reduced", "trading_stopped"]
            details:
              type: object
    additionalProperties: false

  # Market-Data Events
  PriceUpdate:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [asset_symbol, price, timestamp]
    properties:
      asset_symbol:
        type: string
        pattern: "^[A-Z0-9]{1,12}$"
      price:
        type: number
        minimum: 0
      currency:
        type: string
        enum: ["EUR", "USD", "BTC"]
      bid:
        type: number
        minimum: 0
      ask:
        type: number
        minimum: 0
      volume_24h:
        type: number
        minimum: 0
      change_24h:
        type: number
      change_percent:
        type: number
      market_cap:
        type: number
        minimum: 0
      data_source:
        type: string
        description: "Datenquelle (bitpanda_pro, yahoo_finance, etc.)"
      timestamp:
        type: string
        format: date-time
    additionalProperties: false

  # System Events
  ServiceHealthChanged:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    type: object
    required: [service_name, old_status, new_status]
    properties:
      service_name:
        type: string
        enum: ["intelligent-core", "broker-gateway", "event-bus", "monitoring", "frontend"]
      old_status:
        type: string
        enum: ["healthy", "degraded", "unhealthy", "unknown"]
      new_status:
        type: string
        enum: ["healthy", "degraded", "unhealthy", "unknown"]
      health_metrics:
        type: object
        properties:
          response_time_ms:
            type: number
            minimum: 0
          error_rate_percent:
            type: number
            minimum: 0
            maximum: 100
          cpu_usage_percent:
            type: number
            minimum: 0
            maximum: 100
          memory_usage_mb:
            type: number
            minimum: 0
      incident_details:
        type: object
        properties:
          error_message:
            type: string
          stack_trace:
            type: string
          affected_endpoints:
            type: array
            items:
              type: string
    additionalProperties: false

# Event-Metadata-Schema (für alle Events)
event_metadata_schema:
  $schema: "https://json-schema.org/draft/2020-12/schema"
  type: object
  required: [event_id, stream_name, event_type, event_data, timestamp]
  properties:
    event_id:
      type: string
      format: uuid
      description: "Eindeutige Event-ID"
    stream_name:
      type: string
      pattern: "^[a-zA-Z0-9_-]+$"
      description: "Event-Stream-Name"
    event_type:
      type: string
      pattern: "^[A-Z][a-zA-Z0-9]+$"
      description: "Event-Type (PascalCase)"
    event_data:
      type: object
      description: "Event-spezifische Payload"
    metadata:
      type: object
      properties:
        correlation_id:
          type: string
          format: uuid
          description: "Korrelations-ID für Request-Tracking"
        causation_id:
          type: string
          format: uuid
          description: "ID des auslösenden Events"
        user_id:
          type: string
          description: "User-ID für Audit-Trail"
        version:
          type: integer
          minimum: 1
          description: "Event-Schema-Version"
        source_service:
          type: string
          description: "Service der das Event erstellt hat"
    timestamp:
      type: string
      format: date-time
      description: "Event-Zeitstempel (ISO 8601)"
    sequence_number:
      type: integer
      minimum: 1
      description: "Sequenznummer im Stream"
  additionalProperties: false
```

### 4.2 **Event-Schema-Validator-Implementation**
```python
# shared/validation/event_validator.py
import json
import yaml
from typing import Dict, Optional, Tuple, Any
from jsonschema import validate, ValidationError, Draft202012Validator
from datetime import datetime
import uuid

class EventSchemaValidator:
    def __init__(self, schema_file_path: str = None):
        self.schemas = {}
        self.metadata_schema = None
        
        if schema_file_path:
            self.load_schemas(schema_file_path)
        else:
            self.load_schemas("/home/mdoehler/aktienanalyse-ökosystem/config/event-schemas.yaml")
    
    def load_schemas(self, file_path: str) -> None:
        """Lädt Event-Schemas aus YAML-Datei"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                schema_config = yaml.safe_load(f)
            
            self.schemas = schema_config.get('event_schemas', {})
            self.metadata_schema = schema_config.get('event_metadata_schema', {})
            
            print(f"✅ Loaded {len(self.schemas)} event schemas from {file_path}")
            
        except Exception as e:
            print(f"❌ Error loading event schemas: {e}")
            raise
    
    def validate_event(self, event_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validiert komplettes Event gegen Metadata- und Event-Schema"""
        
        try:
            # 1. Metadata-Schema validieren
            if self.metadata_schema:
                validate(event_data, self.metadata_schema)
            
            # 2. Event-Type extrahieren
            event_type = event_data.get('event_type')
            if not event_type:
                return False, "Missing event_type in event data"
            
            # 3. Event-Data-Schema validieren
            if event_type in self.schemas:
                event_payload = event_data.get('event_data', {})
                validate(event_payload, self.schemas[event_type])
            else:
                return False, f"Unknown event type: {event_type}"
            
            return True, None
            
        except ValidationError as e:
            return False, f"Schema validation failed: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def validate_event_payload(self, event_type: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validiert nur Event-Payload ohne Metadata"""
        
        try:
            if event_type not in self.schemas:
                return False, f"Unknown event type: {event_type}"
            
            validate(payload, self.schemas[event_type])
            return True, None
            
        except ValidationError as e:
            return False, f"Payload validation failed: {e.message}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_schema(self, event_type: str) -> Optional[Dict]:
        """Gibt Schema für Event-Type zurück"""
        return self.schemas.get(event_type)
    
    def get_all_event_types(self) -> list:
        """Gibt alle verfügbaren Event-Types zurück"""
        return list(self.schemas.keys())
    
    def create_event_envelope(self, 
                            event_type: str, 
                            event_data: Dict[str, Any], 
                            stream_name: str,
                            correlation_id: Optional[str] = None,
                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """Erstellt vollständiges Event mit Metadata"""
        
        # Event-Payload validieren
        is_valid, error_msg = self.validate_event_payload(event_type, event_data)
        if not is_valid:
            raise ValueError(f"Invalid event payload: {error_msg}")
        
        # Event-Envelope erstellen
        event_envelope = {
            "event_id": str(uuid.uuid4()),
            "stream_name": stream_name,
            "event_type": event_type,
            "event_data": event_data,
            "metadata": {
                "version": 1,
                "source_service": "aktienanalyse-core"
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sequence_number": 1  # TODO: Aus Event-Store ermitteln
        }
        
        # Optional: Correlation-ID
        if correlation_id:
            event_envelope["metadata"]["correlation_id"] = correlation_id
        
        # Optional: User-ID
        if user_id:
            event_envelope["metadata"]["user_id"] = user_id
        
        # Vollständiges Event validieren
        is_valid, error_msg = self.validate_event(event_envelope)
        if not is_valid:
            raise ValueError(f"Invalid event envelope: {error_msg}")
        
        return event_envelope
    
    def get_schema_documentation(self, event_type: str) -> Optional[str]:
        """Generiert Dokumentation für Event-Schema"""
        
        schema = self.get_schema(event_type)
        if not schema:
            return None
        
        doc = f"# Event-Type: {event_type}\n\n"
        
        # Required Fields
        if 'required' in schema:
            doc += "## Required Fields:\n"
            for field in schema['required']:
                field_schema = schema['properties'].get(field, {})
                field_type = field_schema.get('type', 'unknown')
                field_desc = field_schema.get('description', 'No description')
                doc += f"- **{field}** ({field_type}): {field_desc}\n"
            doc += "\n"
        
        # Optional Fields
        optional_fields = [
            field for field in schema.get('properties', {}).keys()
            if field not in schema.get('required', [])
        ]
        
        if optional_fields:
            doc += "## Optional Fields:\n"
            for field in optional_fields:
                field_schema = schema['properties'][field]
                field_type = field_schema.get('type', 'unknown')
                field_desc = field_schema.get('description', 'No description')
                doc += f"- **{field}** ({field_type}): {field_desc}\n"
            doc += "\n"
        
        # Example
        doc += "## Example:\n"
        doc += "```json\n"
        doc += json.dumps(self._generate_example(schema), indent=2)
        doc += "\n```\n"
        
        return doc
    
    def _generate_example(self, schema: Dict) -> Dict:
        """Generiert Beispiel-Event basierend auf Schema"""
        
        example = {}
        properties = schema.get('properties', {})
        
        for field_name, field_schema in properties.items():
            field_type = field_schema.get('type')
            
            if field_type == 'string':
                if 'enum' in field_schema:
                    example[field_name] = field_schema['enum'][0]
                elif field_schema.get('format') == 'uuid':
                    example[field_name] = "12345678-1234-5678-9012-123456789012"
                elif field_schema.get('format') == 'date-time':
                    example[field_name] = "2024-01-15T10:30:00Z"
                else:
                    example[field_name] = field_schema.get('description', 'example_string')
            
            elif field_type == 'number':
                example[field_name] = field_schema.get('minimum', 0) + 100
            
            elif field_type == 'integer':
                example[field_name] = field_schema.get('minimum', 0) + 1
            
            elif field_type == 'boolean':
                example[field_name] = True
            
            elif field_type == 'array':
                example[field_name] = []
            
            elif field_type == 'object':
                example[field_name] = {}
        
        return example

# Event-Schema-Middleware für Flask/FastAPI
class EventValidationMiddleware:
    def __init__(self, validator: EventSchemaValidator):
        self.validator = validator
    
    def validate_request_event(self, request_data: Dict) -> Tuple[bool, Optional[str]]:
        """Validiert Event in HTTP-Request"""
        
        # Event-Type aus Request extrahieren
        event_type = request_data.get('event_type')
        if not event_type:
            return False, "Missing event_type in request"
        
        # Event-Data validieren
        event_data = request_data.get('event_data', {})
        return self.validator.validate_event_payload(event_type, event_data)
    
    def flask_decorator(self, f):
        """Flask-Decorator für Event-Validation"""
        from functools import wraps
        from flask import request, jsonify
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                is_valid, error_msg = self.validate_request_event(request.json)
                if not is_valid:
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': error_msg
                        }
                    }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function

# Testing-Utilities
class EventSchemaTestHelper:
    def __init__(self, validator: EventSchemaValidator):
        self.validator = validator
    
    def generate_test_events(self, event_type: str, count: int = 5) -> list:
        """Generiert Test-Events für Event-Type"""
        
        schema = self.validator.get_schema(event_type)
        if not schema:
            return []
        
        test_events = []
        for i in range(count):
            example_data = self.validator._generate_example(schema)
            
            # Variationen für Tests
            if i > 0:
                example_data = self._create_variation(example_data, i)
            
            test_event = self.validator.create_event_envelope(
                event_type=event_type,
                event_data=example_data,
                stream_name=f"test-stream-{i}"
            )
            
            test_events.append(test_event)
        
        return test_events
    
    def _create_variation(self, base_data: Dict, variation: int) -> Dict:
        """Erstellt Variation von Basis-Daten"""
        
        import copy
        data = copy.deepcopy(base_data)
        
        # Zufällige Variationen basierend auf Variation-Index
        if variation == 1 and 'name' in data:
            data['name'] = f"{data['name']}_variant"
        elif variation == 2 and 'quantity' in data:
            data['quantity'] = data['quantity'] * 2
        elif variation == 3 and 'price' in data:
            data['price'] = data['price'] * 1.1
        
        return data

if __name__ == "__main__":
    # Test Event-Schema-Validator
    validator = EventSchemaValidator()
    
    # Test Portfolio-Event
    portfolio_event = {
        "portfolio_id": "12345678-1234-5678-9012-123456789012",
        "name": "Test Portfolio",
        "currency": "EUR", 
        "initial_cash": 10000.0,
        "risk_profile": "moderate",
        "created_by": "test_user"
    }
    
    is_valid, error = validator.validate_event_payload("PortfolioCreated", portfolio_event)
    print(f"Portfolio Event Valid: {is_valid}, Error: {error}")
    
    # Vollständiges Event erstellen
    full_event = validator.create_event_envelope(
        event_type="PortfolioCreated",
        event_data=portfolio_event,
        stream_name="portfolio-test",
        user_id="test_user"
    )
    
    print(f"Full Event: {json.dumps(full_event, indent=2)}")
```

---

## 🔗 **5. SERVICE-ZU-SERVICE-APIs**

### 5.1 **Inter-Service-Communication-Matrix**
```yaml
# config/inter-service-apis.yaml

service_communication:
  # Intelligent Core Service -> Andere Services
  intelligent_core_service:
    outbound_calls:
      broker_gateway_service:
        base_url: "http://127.0.0.1:8002/api/v1"
        endpoints:
          create_order: "POST /orders"
          get_positions: "GET /positions"
          get_market_data: "GET /market-data/{asset_symbol}/price"
        authentication:
          type: "api_key"
          header: "X-API-Key"
        timeout_seconds: 30
        retry_config:
          max_retries: 3
          backoff_factor: 2
        
      event_bus_service:
        base_url: "http://127.0.0.1:8003/api/v1"
        endpoints:
          publish_event: "POST /events"
          get_projections: "GET /projections"
        authentication:
          type: "api_key"
          header: "X-API-Key"
        timeout_seconds: 10
        retry_config:
          max_retries: 5
          backoff_factor: 1.5
      
      monitoring_service:
        base_url: "http://127.0.0.1:8004/api/v1"
        endpoints:
          send_metrics: "POST /metrics"
          health_check: "GET /health"
        authentication:
          type: "api_key"
          header: "X-API-Key"
        timeout_seconds: 5
        retry_config:
          max_retries: 2
          backoff_factor: 1
    
    inbound_webhooks:
      broker_execution_webhook:
        path: "/webhooks/broker/execution"
        method: "POST"
        authentication:
          type: "signature"
          secret_header: "X-Broker-Signature"
        rate_limit:
          requests_per_minute: 1000
      
      event_subscription_webhook:
        path: "/webhooks/events"
        method: "POST"
        authentication:
          type: "api_key"
          header: "X-Event-Key"
        rate_limit:
          requests_per_minute: 5000

  # Broker Gateway Service
  broker_gateway_service:
    outbound_calls:
      event_bus_service:
        base_url: "http://127.0.0.1:8003/api/v1"
        endpoints:
          publish_event: "POST /events"
        authentication:
          type: "api_key"
          header: "X-API-Key"
        timeout_seconds: 10
        
      monitoring_service:
        base_url: "http://127.0.0.1:8004/api/v1"
        endpoints:
          send_metrics: "POST /metrics"
        timeout_seconds: 5
    
    external_apis:
      bitpanda_pro_api:
        base_url: "https://api.exchange.bitpanda.com"
        endpoints:
          create_order: "POST /public/v1/orders"
          get_orders: "GET /public/v1/orders"
          get_account: "GET /public/v1/account"
          get_ticker: "GET /public/v1/market-ticker/{instrument_code}"
        authentication:
          type: "bearer"
          token_env_var: "BITPANDA_API_TOKEN"
        rate_limits:
          requests_per_second: 10
          burst_limit: 50
        retry_config:
          max_retries: 3
          backoff_factor: 2

  # Frontend Service
  frontend_service:
    outbound_calls:
      intelligent_core_service:
        base_url: "http://127.0.0.1:8001/api/v1"
        endpoints:
          get_portfolios: "GET /portfolios"
          get_portfolio_details: "GET /portfolios/{portfolio_id}"
          create_portfolio: "POST /portfolios"
          rebalance_portfolio: "POST /portfolios/{portfolio_id}/rebalance"
          get_assets: "GET /assets"
          get_asset_analysis: "GET /assets/{asset_symbol}/analysis"
          get_risk_assessment: "GET /risk/portfolio/{portfolio_id}/assessment"
        proxy_mode: true
        
      broker_gateway_service:
        base_url: "http://127.0.0.1:8002/api/v1"
        endpoints:
          get_orders: "GET /orders"
          create_order: "POST /orders"
          cancel_order: "DELETE /orders/{order_id}"
          get_positions: "GET /positions"
          get_market_data: "GET /market-data/{asset_symbol}/price"
        proxy_mode: true
        
      monitoring_service:
        base_url: "http://127.0.0.1:8004/api/v1"
        endpoints:
          get_system_health: "GET /health"
          get_metrics: "GET /metrics"
          get_alerts: "GET /alerts"
        proxy_mode: true

# Service-Discovery-Konfiguration
service_discovery:
  mode: "static"  # static, consul, kubernetes
  health_check_interval_seconds: 30
  
  services:
    intelligent_core_service:
      host: "127.0.0.1"
      port: 8001
      health_endpoint: "/health"
      
    broker_gateway_service:
      host: "127.0.0.1"
      port: 8002
      health_endpoint: "/health"
      
    event_bus_service:
      host: "127.0.0.1"
      port: 8003
      health_endpoint: "/health"
      
    monitoring_service:
      host: "127.0.0.1"
      port: 8004
      health_endpoint: "/health"
      
    frontend_service:
      host: "127.0.0.1"
      port: 8443
      health_endpoint: "/health"
      protocol: "https"
```

### 5.2 **Service-Client-Implementation**
```python
# shared/clients/service_client.py
import httpx
import asyncio
import yaml
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from enum import Enum
import hashlib
import hmac

class AuthenticationType(Enum):
    API_KEY = "api_key"
    BEARER = "bearer"
    SIGNATURE = "signature"
    NONE = "none"

class ServiceClient:
    def __init__(self, service_name: str, config_file: str = None):
        self.service_name = service_name
        self.config = self._load_config(config_file)
        self.service_config = self.config['service_communication'].get(service_name, {})
        self.client = httpx.AsyncClient(timeout=30.0)
        
    def _load_config(self, config_file: str = None) -> Dict:
        """Lädt Service-Konfiguration"""
        
        if not config_file:
            config_file = "/home/mdoehler/aktienanalyse-ökosystem/config/inter-service-apis.yaml"
        
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading service config: {e}")
            return {}
    
    async def call_service(self, 
                          target_service: str, 
                          endpoint_name: str, 
                          method: str = "GET",
                          data: Optional[Dict] = None,
                          path_params: Optional[Dict] = None,
                          query_params: Optional[Dict] = None) -> Tuple[bool, Any]:
        """Ruft anderen Service auf"""
        
        try:
            # Service-Konfiguration laden
            target_config = self.service_config['outbound_calls'].get(target_service)
            if not target_config:
                return False, f"No configuration for target service: {target_service}"
            
            # Endpoint-URL zusammenbauen
            base_url = target_config['base_url']
            endpoint_template = target_config['endpoints'].get(endpoint_name)
            
            if not endpoint_template:
                return False, f"Unknown endpoint: {endpoint_name}"
            
            # Path-Parameter ersetzen
            method_and_path = endpoint_template
            if path_params:
                for param, value in path_params.items():
                    method_and_path = method_and_path.replace(f"{{{param}}}", str(value))
            
            # HTTP-Method und Path extrahieren
            parts = method_and_path.split(' ', 1)
            if len(parts) == 2:
                http_method, path = parts
            else:
                http_method = method
                path = parts[0]
            
            url = f"{base_url}{path}"
            
            # Headers für Authentication
            headers = await self._get_auth_headers(target_config)
            
            # Request-Parameter
            request_params = {
                'method': http_method,
                'url': url,
                'headers': headers,
                'timeout': target_config.get('timeout_seconds', 30)
            }
            
            if data:
                if http_method in ['POST', 'PUT', 'PATCH']:
                    request_params['json'] = data
                else:
                    request_params['params'] = data
            
            if query_params:
                request_params['params'] = query_params
            
            # Request mit Retry-Logic
            retry_config = target_config.get('retry_config', {})
            max_retries = retry_config.get('max_retries', 3)
            backoff_factor = retry_config.get('backoff_factor', 2)
            
            for attempt in range(max_retries + 1):
                try:
                    response = await self.client.request(**request_params)
                    
                    if response.status_code < 400:
                        return True, response.json() if response.content else None
                    elif response.status_code < 500 and attempt == max_retries:
                        # Client-Error - nicht retryable
                        return False, {
                            'error': 'client_error',
                            'status_code': response.status_code,
                            'response': response.text
                        }
                    
                except httpx.TimeoutException:
                    if attempt == max_retries:
                        return False, {'error': 'timeout', 'service': target_service}
                
                except httpx.ConnectError:
                    if attempt == max_retries:
                        return False, {'error': 'connection_failed', 'service': target_service}
                
                # Exponential Backoff vor Retry
                if attempt < max_retries:
                    wait_time = backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
            
            return False, {'error': 'max_retries_exceeded', 'service': target_service}
            
        except Exception as e:
            logging.error(f"Error calling {target_service}.{endpoint_name}: {e}")
            return False, {'error': 'client_exception', 'message': str(e)}
    
    async def _get_auth_headers(self, target_config: Dict) -> Dict[str, str]:
        """Generiert Authentication-Headers"""
        
        headers = {'Content-Type': 'application/json'}
        
        auth_config = target_config.get('authentication', {})
        auth_type = auth_config.get('type')
        
        if auth_type == AuthenticationType.API_KEY.value:
            # API-Key aus Environment oder Config
            api_key = await self._get_api_key(target_config)
            if api_key:
                header_name = auth_config.get('header', 'X-API-Key')
                headers[header_name] = api_key
        
        elif auth_type == AuthenticationType.BEARER.value:
            # Bearer-Token aus Environment
            token_env_var = auth_config.get('token_env_var')
            if token_env_var:
                import os
                token = os.getenv(token_env_var)
                if token:
                    headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    async def _get_api_key(self, target_config: Dict) -> Optional[str]:
        """Lädt API-Key für Service"""
        
        # TODO: Implementierung für sichere API-Key-Verwaltung
        # Für Demo: Statischer Key
        service_keys = {
            'broker_gateway_service': 'broker-api-key-123',
            'event_bus_service': 'event-bus-api-key-456',
            'monitoring_service': 'monitoring-api-key-789'
        }
        
        target_service = target_config['base_url'].split('/')[-1]  # Vereinfacht
        return service_keys.get(target_service, 'default-api-key')
    
    async def health_check(self, target_service: str) -> Tuple[bool, Dict]:
        """Führt Health-Check für Service durch"""
        
        return await self.call_service(
            target_service=target_service,
            endpoint_name='health_check',
            method='GET'
        )
    
    async def close(self):
        """Schließt HTTP-Client"""
        await self.client.aclose()

# Service-Registry für Service-Discovery
class ServiceRegistry:
    def __init__(self):
        self.services = {}
        self.health_status = {}
        
    async def register_service(self, service_name: str, host: str, port: int, health_endpoint: str = "/health"):
        """Registriert Service"""
        
        self.services[service_name] = {
            'host': host,
            'port': port,
            'health_endpoint': health_endpoint,
            'registered_at': datetime.utcnow()
        }
        
        logging.info(f"🏷️ Registered service: {service_name} at {host}:{port}")
    
    async def get_service_url(self, service_name: str) -> Optional[str]:
        """Gibt Service-URL zurück"""
        
        service = self.services.get(service_name)
        if not service:
            return None
        
        protocol = "https" if service.get('protocol') == 'https' else "http"
        return f"{protocol}://{service['host']}:{service['port']}"
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Führt Health-Check für alle Services durch"""
        
        results = {}
        
        for service_name, service_info in self.services.items():
            try:
                url = await self.get_service_url(service_name)
                health_url = f"{url}{service_info['health_endpoint']}"
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(health_url)
                    results[service_name] = response.status_code == 200
                    
            except Exception as e:
                logging.error(f"Health check failed for {service_name}: {e}")
                results[service_name] = False
        
        self.health_status = results
        return results

# Service-Client-Factory
class ServiceClientFactory:
    _clients = {}
    
    @classmethod
    def get_client(cls, service_name: str) -> ServiceClient:
        """Gibt Service-Client zurück (Singleton-Pattern)"""
        
        if service_name not in cls._clients:
            cls._clients[service_name] = ServiceClient(service_name)
        
        return cls._clients[service_name]
    
    @classmethod
    async def close_all(cls):
        """Schließt alle Clients"""
        
        for client in cls._clients.values():
            await client.close()
        
        cls._clients.clear()

# Decorator für Service-Calls
def service_call(target_service: str, endpoint_name: str):
    """Decorator für einfache Service-Calls"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Service-Client holen
            client = ServiceClientFactory.get_client(func.__qualname__.split('.')[0])
            
            # Funktions-Parameter als Request-Data verwenden
            data = kwargs.copy()
            
            # Service-Call durchführen
            success, result = await client.call_service(
                target_service=target_service,
                endpoint_name=endpoint_name,
                method='POST',
                data=data
            )
            
            if not success:
                raise Exception(f"Service call failed: {result}")
            
            return result
        
        return wrapper
    return decorator

# Usage-Beispiel
class PortfolioService:
    def __init__(self):
        self.client = ServiceClientFactory.get_client('intelligent_core_service')
    
    @service_call('broker_gateway_service', 'create_order')
    async def create_trading_order(self, portfolio_id: str, asset_symbol: str, side: str, quantity: float):
        """Erstellt Trading-Order über Broker-Gateway"""
        pass  # Implementation wird durch Decorator ersetzt
    
    async def get_portfolio_positions(self, portfolio_id: str):
        """Ruft Portfolio-Positionen ab"""
        
        success, result = await self.client.call_service(
            target_service='broker_gateway_service',
            endpoint_name='get_positions',
            query_params={'portfolio_id': portfolio_id}
        )
        
        if not success:
            raise Exception(f"Failed to get positions: {result}")
        
        return result['data']

if __name__ == "__main__":
    # Test Service-Client
    async def test_service_communication():
        portfolio_service = PortfolioService()
        
        try:
            # Test Order-Erstellung
            order_result = await portfolio_service.create_trading_order(
                portfolio_id="12345",
                asset_symbol="AAPL",
                side="buy",
                quantity=10.0
            )
            
            print(f"Order created: {order_result}")
            
            # Test Positions-Abruf
            positions = await portfolio_service.get_portfolio_positions("12345")
            print(f"Positions: {positions}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await ServiceClientFactory.close_all()
    
    asyncio.run(test_service_communication())
```

---

## 🔄 **6. API-VERSIONIERUNG-STRATEGY**

### 6.1 **Versionierungs-Richtlinien und -Standards**
```yaml
# config/api-versioning-strategy.yaml

versioning_strategy:
  # Versionierungs-Schema
  scheme: "semantic"  # semantic, date-based, sequential
  format: "v{major}.{minor}.{patch}"  # v1.2.3
  
  # Versionierungs-Methoden
  versioning_methods:
    primary: "url_path"     # URL: /api/v1/portfolios
    secondary: "header"     # Header: Accept: application/vnd.aktienanalyse.v1+json
    fallback: "query_param" # Query: ?api_version=v1
  
  # Kompatibilitäts-Richtlinien
  compatibility:
    backward_compatibility_period_months: 12
    deprecation_notice_period_months: 6
    breaking_changes_only_in_major: true
    
  # Standard-API-Versionen
  supported_versions:
    v1:
      status: "current"
      release_date: "2024-01-01"
      deprecation_date: null
      end_of_life_date: null
      breaking_changes: []
      
    v2:
      status: "development"
      release_date: "2024-06-01"
      deprecation_date: null
      end_of_life_date: null
      breaking_changes:
        - "Portfolio response structure changed"
        - "Order creation requires additional validation"
        - "Risk assessment response format updated"

# Service-spezifische Versionierung
service_versioning:
  intelligent_core_service:
    current_version: "v1.0.0"
    supported_versions:
      - version: "v1.0.0"
        endpoints:
          portfolios: "/api/v1/portfolios"
          assets: "/api/v1/assets"
          risk: "/api/v1/risk"
        schema_changes: []
        
      - version: "v1.1.0"  # Minor-Version mit neuen Features
        endpoints:
          portfolios: "/api/v1/portfolios"
          assets: "/api/v1/assets"
          risk: "/api/v1/risk"
          analytics: "/api/v1/analytics"  # Neue Funktionalität
        schema_changes:
          - "Added analytics endpoints"
          - "Extended portfolio response with performance metrics"
          
      - version: "v2.0.0"  # Major-Version mit Breaking Changes
        endpoints:
          portfolios: "/api/v2/portfolios"
          assets: "/api/v2/assets"
          risk: "/api/v2/risk"
          analytics: "/api/v2/analytics"
        schema_changes:
          - "BREAKING: Portfolio ID format changed to UUID v4"
          - "BREAKING: Risk assessment response restructured"
          - "BREAKING: Asset allocation percentages as decimals (0.6 instead of 60)"

  broker_gateway_service:
    current_version: "v1.0.0"
    supported_versions:
      - version: "v1.0.0"
        endpoints:
          orders: "/api/v1/orders"
          positions: "/api/v1/positions"
          market_data: "/api/v1/market-data"
        
      - version: "v1.2.0"
        endpoints:
          orders: "/api/v1/orders"
          positions: "/api/v1/positions"
          market_data: "/api/v1/market-data"
          analytics: "/api/v1/analytics"
        schema_changes:
          - "Added order analytics endpoints"
          - "Extended market data with additional indicators"

# Version-Routing-Konfiguration
version_routing:
  default_version: "v1"
  
  # URL-Pattern für Versionierung
  url_patterns:
    - pattern: "/api/v{version}/"
      valid_versions: ["1", "2"]
      
  # Header-basierte Versionierung
  version_headers:
    accept_header_pattern: "application/vnd.aktienanalyse.v{version}+json"
    custom_header: "X-API-Version"
    
  # Version-Fallback-Logik
  fallback_strategy:
    - "url_path"      # 1. Priorität: URL-Path
    - "accept_header" # 2. Priorität: Accept-Header
    - "custom_header" # 3. Priorität: Custom-Header
    - "query_param"   # 4. Priorität: Query-Parameter
    - "default"       # 5. Fallback: Default-Version

# Deprecation-Management
deprecation_management:
  # Deprecation-Warnings
  warning_headers:
    sunset_header: "Sunset"      # RFC 8594
    deprecation_header: "Deprecation"
    warning_header: "Warning"
    
  # Deprecation-Response-Format
  deprecation_response:
    include_in_response: true
    response_field: "deprecation_notice"
    format:
      deprecated: true
      current_version: "v1.0.0"
      deprecated_in_version: "v2.0.0"
      sunset_date: "2025-01-01T00:00:00Z"
      migration_guide_url: "https://docs.aktienanalyse.local/migration/v1-to-v2"
      alternative_endpoints:
        - endpoint: "/api/v2/portfolios"
          description: "Use v2 portfolios endpoint with updated schema"
```

### 6.2 **API-Versionierungs-Middleware**
```python
# shared/middleware/api_versioning.py
import re
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from flask import Flask, request, g, jsonify
from dataclasses import dataclass
from enum import Enum

class VersionStatus(Enum):
    CURRENT = "current"
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"

@dataclass
class APIVersion:
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    breaking_changes: list = None
    migration_guide_url: Optional[str] = None
    
    def __post_init__(self):
        if self.breaking_changes is None:
            self.breaking_changes = []

class APIVersionManager:
    def __init__(self, config_file: str = None):
        self.versions = {}
        self.default_version = "v1"
        self.supported_versions = set()
        
        if config_file:
            self.load_config(config_file)
        else:
            self._setup_default_versions()
    
    def load_config(self, config_file: str):
        """Lädt Versionierungs-Konfiguration"""
        
        import yaml
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            versioning_config = config.get('versioning_strategy', {})
            self.default_version = versioning_config.get('default_version', 'v1')
            
            # Unterstützte Versionen laden
            supported_versions = versioning_config.get('supported_versions', {})
            
            for version_str, version_info in supported_versions.items():
                self.add_version(
                    version=version_str,
                    status=VersionStatus(version_info.get('status', 'current')),
                    release_date=datetime.fromisoformat(version_info['release_date']),
                    deprecation_date=(
                        datetime.fromisoformat(version_info['deprecation_date']) 
                        if version_info.get('deprecation_date') 
                        else None
                    ),
                    breaking_changes=version_info.get('breaking_changes', [])
                )
                
        except Exception as e:
            print(f"Error loading versioning config: {e}")
            self._setup_default_versions()
    
    def _setup_default_versions(self):
        """Setup Standard-Versionen"""
        
        self.add_version(
            version="v1",
            status=VersionStatus.CURRENT,
            release_date=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
    
    def add_version(self, 
                   version: str, 
                   status: VersionStatus,
                   release_date: datetime,
                   deprecation_date: Optional[datetime] = None,
                   sunset_date: Optional[datetime] = None,
                   breaking_changes: list = None,
                   migration_guide_url: Optional[str] = None):
        """Fügt neue API-Version hinzu"""
        
        api_version = APIVersion(
            version=version,
            status=status,
            release_date=release_date,
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
            breaking_changes=breaking_changes or [],
            migration_guide_url=migration_guide_url
        )
        
        self.versions[version] = api_version
        
        if status in [VersionStatus.CURRENT, VersionStatus.SUPPORTED]:
            self.supported_versions.add(version)
    
    def extract_version_from_request(self, request_obj) -> Tuple[Optional[str], str]:
        """Extrahiert API-Version aus Request"""
        
        # 1. URL-Path prüfen
        url_version = self._extract_version_from_url(request_obj.path)
        if url_version:
            return url_version, "url_path"
        
        # 2. Accept-Header prüfen
        accept_header = request_obj.headers.get('Accept', '')
        header_version = self._extract_version_from_accept_header(accept_header)
        if header_version:
            return header_version, "accept_header"
        
        # 3. Custom-Header prüfen
        custom_version = request_obj.headers.get('X-API-Version')
        if custom_version:
            normalized_version = self._normalize_version(custom_version)
            if normalized_version in self.supported_versions:
                return normalized_version, "custom_header"
        
        # 4. Query-Parameter prüfen
        query_version = request_obj.args.get('api_version')
        if query_version:
            normalized_version = self._normalize_version(query_version)
            if normalized_version in self.supported_versions:
                return normalized_version, "query_param"
        
        # 5. Default-Version zurückgeben
        return self.default_version, "default"
    
    def _extract_version_from_url(self, path: str) -> Optional[str]:
        """Extrahiert Version aus URL-Path"""
        
        # Pattern: /api/v1/endpoint oder /api/v1.2/endpoint
        pattern = r'/api/v(\d+(?:\.\d+)?)(?:/|$)'
        match = re.search(pattern, path)
        
        if match:
            version_number = match.group(1)
            return f"v{version_number}"
        
        return None
    
    def _extract_version_from_accept_header(self, accept_header: str) -> Optional[str]:
        """Extrahiert Version aus Accept-Header"""
        
        # Pattern: application/vnd.aktienanalyse.v1+json
        pattern = r'application/vnd\.aktienanalyse\.v(\d+(?:\.\d+)?)\+json'
        match = re.search(pattern, accept_header)
        
        if match:
            version_number = match.group(1)
            return f"v{version_number}"
        
        return None
    
    def _normalize_version(self, version: str) -> str:
        """Normalisiert Versions-String"""
        
        # Entfernt 'v' prefix falls vorhanden
        if version.startswith('v'):
            return version
        else:
            return f"v{version}"
    
    def validate_version(self, version: str) -> Tuple[bool, Optional[str]]:
        """Validiert ob Version unterstützt wird"""
        
        if not version:
            return False, "No version specified"
        
        normalized_version = self._normalize_version(version)
        
        if normalized_version not in self.versions:
            return False, f"Unknown API version: {normalized_version}"
        
        api_version = self.versions[normalized_version]
        
        # Prüfe ob Version noch gültig ist
        now = datetime.now(timezone.utc)
        
        if api_version.sunset_date and now > api_version.sunset_date:
            return False, f"API version {normalized_version} has been sunset"
        
        return True, None
    
    def get_version_info(self, version: str) -> Optional[APIVersion]:
        """Gibt Versions-Informationen zurück"""
        
        normalized_version = self._normalize_version(version)
        return self.versions.get(normalized_version)
    
    def get_deprecation_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Gibt Deprecation-Informationen zurück"""
        
        api_version = self.get_version_info(version)
        if not api_version:
            return None
        
        if api_version.status in [VersionStatus.DEPRECATED, VersionStatus.SUNSET]:
            return {
                "deprecated": True,
                "current_version": version,
                "status": api_version.status.value,
                "deprecation_date": api_version.deprecation_date.isoformat() if api_version.deprecation_date else None,
                "sunset_date": api_version.sunset_date.isoformat() if api_version.sunset_date else None,
                "migration_guide_url": api_version.migration_guide_url,
                "breaking_changes": api_version.breaking_changes
            }
        
        return None

class APIVersioningMiddleware:
    def __init__(self, app: Flask, version_manager: APIVersionManager):
        self.app = app
        self.version_manager = version_manager
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup Flask-Middleware für API-Versionierung"""
        
        @self.app.before_request
        def before_request():
            # Version aus Request extrahieren
            version, source = self.version_manager.extract_version_from_request(request)
            
            # Version validieren
            is_valid, error_message = self.version_manager.validate_version(version)
            
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'UNSUPPORTED_API_VERSION',
                        'message': error_message,
                        'supported_versions': list(self.version_manager.supported_versions)
                    }
                }), 400
            
            # Version in Request-Context speichern
            g.api_version = version
            g.version_source = source
            g.version_info = self.version_manager.get_version_info(version)
        
        @self.app.after_request
        def after_request(response):
            # API-Version zu Response-Headers hinzufügen
            if hasattr(g, 'api_version'):
                response.headers['X-API-Version'] = g.api_version
                response.headers['X-API-Version-Source'] = g.version_source
            
            # Deprecation-Warnings hinzufügen
            if hasattr(g, 'api_version'):
                deprecation_info = self.version_manager.get_deprecation_info(g.api_version)
                
                if deprecation_info:
                    # RFC 8594 Sunset Header
                    if deprecation_info.get('sunset_date'):
                        response.headers['Sunset'] = deprecation_info['sunset_date']
                    
                    # Warning Header
                    if deprecation_info['status'] == 'deprecated':
                        response.headers['Warning'] = '299 - "This API version is deprecated"'
                    
                    # Deprecation-Info in Response-Body (optional)
                    if response.is_json and hasattr(response, 'json'):
                        try:
                            response_data = response.get_json()
                            if isinstance(response_data, dict):
                                response_data['deprecation_notice'] = deprecation_info
                                response.data = response.json.dumps(response_data)
                        except:
                            pass  # Ignoriere Fehler beim JSON-Parsing
            
            return response

# Version-spezifische Request-Handler
def version_handler(supported_versions: list):
    """Decorator für versions-spezifische Endpoints"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_version = getattr(g, 'api_version', 'v1')
            
            if current_version not in supported_versions:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'VERSION_NOT_SUPPORTED',
                        'message': f'This endpoint does not support version {current_version}',
                        'supported_versions': supported_versions
                    }
                }), 400
            
            # Version-spezifische Parameter hinzufügen
            kwargs['api_version'] = current_version
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    
    return decorator

# Schema-Transformation für verschiedene Versionen
class SchemaTransformer:
    def __init__(self):
        self.transformers = {}
    
    def register_transformer(self, from_version: str, to_version: str, transformer_func):
        """Registriert Schema-Transformer"""
        
        key = f"{from_version}->{to_version}"
        self.transformers[key] = transformer_func
    
    def transform(self, data: Dict, from_version: str, to_version: str) -> Dict:
        """Transformiert Daten zwischen Versionen"""
        
        if from_version == to_version:
            return data
        
        key = f"{from_version}->{to_version}"
        
        if key in self.transformers:
            return self.transformers[key](data)
        
        # Fallback: Keine Transformation
        return data

# Beispiel: Portfolio-Schema-Transformationen
def portfolio_v1_to_v2(data: Dict) -> Dict:
    """Transformiert Portfolio von v1 zu v2"""
    
    # v2: Allocation als Dezimalzahlen statt Prozent
    if 'target_allocation' in data:
        new_allocation = {}
        for asset_class, percentage in data['target_allocation'].items():
            new_allocation[asset_class] = percentage / 100.0
        
        data['target_allocation'] = new_allocation
    
    return data

def portfolio_v2_to_v1(data: Dict) -> Dict:
    """Transformiert Portfolio von v2 zu v1"""
    
    # v1: Allocation als Prozent statt Dezimalzahlen
    if 'target_allocation' in data:
        new_allocation = {}
        for asset_class, decimal in data['target_allocation'].items():
            new_allocation[asset_class] = decimal * 100.0
        
        data['target_allocation'] = new_allocation
    
    return data

# Setup
schema_transformer = SchemaTransformer()
schema_transformer.register_transformer('v1', 'v2', portfolio_v1_to_v2)
schema_transformer.register_transformer('v2', 'v1', portfolio_v2_to_v1)

if __name__ == "__main__":
    # Test API-Versionierung
    version_manager = APIVersionManager()
    
    # Test Version-Extraktion
    class MockRequest:
        def __init__(self, path, headers=None, args=None):
            self.path = path
            self.headers = headers or {}
            self.args = args or {}
    
    # Test verschiedene Versionierungs-Methoden
    test_requests = [
        MockRequest('/api/v1/portfolios'),
        MockRequest('/api/portfolios', {'Accept': 'application/vnd.aktienanalyse.v2+json'}),
        MockRequest('/api/portfolios', {'X-API-Version': 'v1.1'}),
        MockRequest('/api/portfolios', args={'api_version': '2'})
    ]
    
    for req in test_requests:
        version, source = version_manager.extract_version_from_request(req)
        print(f"Path: {req.path}, Version: {version}, Source: {source}")
```

---

## ⚡ **7. RATE-LIMITING-DEFINITIONEN**

### 7.1 **Service-spezifische Rate-Limits**
```yaml
# config/rate-limiting.yaml

rate_limiting:
  # Global Defaults
  default_limits:
    requests_per_minute: 1000
    burst_limit: 200
    concurrent_connections: 50
    
  # Service-spezifische Limits
  services:
    intelligent_core_service:
      port: 8001
      global_limit:
        requests_per_minute: 2000
        burst_limit: 400
        
      endpoint_limits:
        # Portfolio-Management
        "GET /api/v1/portfolios":
          requests_per_minute: 500
          burst_limit: 100
          description: "Portfolio-Listing"
          
        "POST /api/v1/portfolios":
          requests_per_minute: 60
          burst_limit: 10
          description: "Portfolio-Erstellung (limitiert)"
          
        "PUT /api/v1/portfolios/{portfolio_id}":
          requests_per_minute: 120
          burst_limit: 20
          description: "Portfolio-Updates"
          
        "POST /api/v1/portfolios/{portfolio_id}/rebalance":
          requests_per_minute: 10
          burst_limit: 2
          description: "Portfolio-Rebalancing (stark limitiert)"
          
        # Asset-Analysis (rechenintensiv)
        "GET /api/v1/assets/{asset_symbol}/analysis":
          requests_per_minute: 100
          burst_limit: 20
          description: "Asset-Analyse (rechenintensiv)"
          
        # Risk-Assessment
        "GET /api/v1/risk/portfolio/{portfolio_id}/assessment":
          requests_per_minute: 200
          burst_limit: 40
          description: "Risk-Assessment"
          
        "PUT /api/v1/risk/limits":
          requests_per_minute: 30
          burst_limit: 5
          description: "Risk-Limits-Änderung (kritisch)"

    broker_gateway_service:
      port: 8002
      global_limit:
        requests_per_minute: 1500
        burst_limit: 300
        
      endpoint_limits:
        # Order-Management (kritisch)
        "POST /api/v1/orders":
          requests_per_minute: 100
          burst_limit: 20
          description: "Order-Erstellung (trading-kritisch)"
          per_user_limit:
            requests_per_minute: 50
            burst_limit: 10
            
        "DELETE /api/v1/orders/{order_id}":
          requests_per_minute: 200
          burst_limit: 40
          description: "Order-Stornierung"
          
        "GET /api/v1/orders":
          requests_per_minute: 300
          burst_limit: 60
          description: "Order-Listing"
          
        # Market-Data (häufig abgerufen)
        "GET /api/v1/market-data/{asset_symbol}/price":
          requests_per_minute: 600
          burst_limit: 120
          description: "Real-time-Preise"
          
        "GET /api/v1/market-data/{asset_symbol}/historical":
          requests_per_minute: 100
          burst_limit: 20
          description: "Historische Daten (datenlastig)"
          
        # Positions
        "GET /api/v1/positions":
          requests_per_minute: 400
          burst_limit: 80
          description: "Position-Übersicht"

    event_bus_service:
      port: 8003
      global_limit:
        requests_per_minute: 5000
        burst_limit: 1000
        
      endpoint_limits:
        "POST /api/v1/events":
          requests_per_minute: 2000
          burst_limit: 400
          description: "Event-Publishing"
          
        "GET /api/v1/events":
          requests_per_minute: 1000
          burst_limit: 200
          description: "Event-Streaming"
          
        "POST /api/v1/subscriptions":
          requests_per_minute: 100
          burst_limit: 20
          description: "Subscription-Management"
          
        "POST /api/v1/projections/{projection_name}/rebuild":
          requests_per_minute: 5
          burst_limit: 2
          description: "Projection-Rebuild (ressourcenintensiv)"
          
        "POST /api/v1/replay":
          requests_per_minute: 10
          burst_limit: 3
          description: "Event-Replay (ressourcenintensiv)"

    monitoring_service:
      port: 8004
      global_limit:
        requests_per_minute: 3000
        burst_limit: 600
        
      endpoint_limits:
        "GET /api/v1/metrics":
          requests_per_minute: 1000
          burst_limit: 200
          description: "Metrics-Abruf"
          
        "GET /api/v1/metrics/prometheus":
          requests_per_minute: 500
          burst_limit: 100
          description: "Prometheus-Metrics (Scraping)"
          
        "GET /api/v1/health":
          requests_per_minute: 2000
          burst_limit: 400
          description: "Health-Checks (häufig)"
          
        "GET /api/v1/alerts":
          requests_per_minute: 300
          burst_limit: 60
          description: "Alert-Listing"
          
        "POST /api/v1/alerts/{alert_id}/acknowledge":
          requests_per_minute: 100
          burst_limit: 20
          description: "Alert-Acknowledgment"

    frontend_service:
      port: 8443
      global_limit:
        requests_per_minute: 2000
        burst_limit: 400
        
      endpoint_limits:
        # Authentication
        "POST /api/v1/auth/login":
          requests_per_minute: 60
          burst_limit: 10
          description: "Login-Versuche (Brute-Force-Schutz)"
          per_ip_limit:
            requests_per_minute: 20
            burst_limit: 5
            
        "POST /api/v1/auth/logout":
          requests_per_minute: 100
          burst_limit: 20
          description: "Logout-Requests"
          
        # API-Proxy
        "GET /api/v1/proxy/{service}/{path}":
          requests_per_minute: 1500
          burst_limit: 300
          description: "API-Proxy-Calls"
          
        "POST /api/v1/proxy/{service}/{path}":
          requests_per_minute: 800
          burst_limit: 160
          description: "API-Proxy-Posts"
          
        # Configuration
        "PUT /api/v1/configuration/{section}":
          requests_per_minute: 30
          burst_limit: 6
          description: "Konfigurationssänderungen (limitiert)"

  # Client-spezifische Limits
  client_limits:
    # Nach Client-Type
    web_browser:
      requests_per_minute: 1000
      burst_limit: 200
      description: "Web-Browser-Clients"
      
    mobile_app:
      requests_per_minute: 500
      burst_limit: 100
      description: "Mobile-App-Clients"
      
    api_client:
      requests_per_minute: 2000
      burst_limit: 400
      description: "API-Integration-Clients"
      
    monitoring_client:
      requests_per_minute: 5000
      burst_limit: 1000
      description: "Monitoring-System-Clients"
    
    # Nach User-Role
    admin_user:
      requests_per_minute: 3000
      burst_limit: 600
      description: "Administrator-Benutzer"
      
    regular_user:
      requests_per_minute: 1000
      burst_limit: 200
      description: "Reguläre Benutzer"
      
    readonly_user:
      requests_per_minute: 500
      burst_limit: 100
      description: "Nur-Lese-Benutzer"

  # Spezielle Rate-Limiting-Regeln
  special_rules:
    # Trading-Hours (höhere Limits während Handelszeiten)
    trading_hours:
      enabled: true
      timezone: "Europe/Berlin"
      weekdays:
        start_time: "09:00"
        end_time: "17:30"
        multiplier: 1.5  # 50% höhere Limits
      
    # Wartungszeiten (reduzierte Limits)
    maintenance_hours:
      enabled: true
      schedule:
        - day: "sunday"
          start_time: "02:00"
          end_time: "04:00"
          multiplier: 0.3  # 70% reduzierte Limits
    
    # Notfall-Modus (drastisch reduzierte Limits)
    emergency_mode:
      enabled: false
      global_multiplier: 0.1  # 90% reduzierte Limits
      critical_endpoints_only: true
      
  # Rate-Limiting-Algorithmen
  algorithms:
    default: "token_bucket"  # token_bucket, sliding_window, fixed_window
    
    token_bucket:
      refill_rate: "per_minute"  # Rate der Token-Nachfüllung
      bucket_size_multiplier: 2  # Bucket-Größe = limit * multiplier
      
    sliding_window:
      window_size_minutes: 1
      precision_seconds: 10  # Fenster-Auflösung
      
  # Response-Handling
  rate_limit_responses:
    http_status_code: 429  # Too Many Requests
    
    headers:
      remaining: "X-RateLimit-Remaining"
      limit: "X-RateLimit-Limit"
      reset: "X-RateLimit-Reset"
      retry_after: "Retry-After"
      
    response_body:
      success: false
      error:
        code: "RATE_LIMIT_EXCEEDED"
        message: "Rate limit exceeded. Please try again later."
        details:
          limit: "${limit}"
          remaining: "${remaining}"
          reset_time: "${reset_time}"
          retry_after_seconds: "${retry_after}"
          
    # Custom-Messages für verschiedene Endpoints
    custom_messages:
      trading_endpoints:
        message: "Trading rate limit exceeded. This protects against erroneous mass orders."
        recommendation: "Please review your trading strategy and reduce request frequency."
        
      analysis_endpoints:
        message: "Analysis rate limit exceeded. Asset analysis is computationally intensive."
        recommendation: "Consider caching analysis results or reducing analysis frequency."
```

### 7.2 **Rate-Limiting-Middleware-Implementation**
```python
# shared/middleware/rate_limiting.py
import time
import redis
import json
import yaml
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g
from functools import wraps
import logging
from enum import Enum

class RateLimitAlgorithm(Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

class RateLimitResult:
    def __init__(self, 
                 allowed: bool, 
                 limit: int, 
                 remaining: int, 
                 reset_time: int,
                 retry_after: Optional[int] = None):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after

class RateLimiter:
    def __init__(self, redis_client, algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET):
        self.redis = redis_client
        self.algorithm = algorithm
        
    def check_rate_limit(self, 
                        key: str, 
                        limit: int, 
                        window_seconds: int = 60,
                        burst_limit: Optional[int] = None) -> RateLimitResult:
        """Prüft Rate-Limit für gegebenen Key"""
        
        if self.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return self._token_bucket_check(key, limit, window_seconds, burst_limit)
        elif self.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return self._sliding_window_check(key, limit, window_seconds)
        elif self.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return self._fixed_window_check(key, limit, window_seconds)
        else:
            raise ValueError(f"Unknown rate limiting algorithm: {self.algorithm}")
    
    def _token_bucket_check(self, 
                           key: str, 
                           limit: int, 
                           window_seconds: int,
                           burst_limit: Optional[int] = None) -> RateLimitResult:
        """Token-Bucket-Algorithmus"""
        
        if burst_limit is None:
            burst_limit = limit * 2  # Default: Doppelte Bucket-Größe
        
        now = time.time()
        bucket_key = f"rate_limit:token_bucket:{key}"
        
        # Lua-Script für atomare Token-Bucket-Operation
        lua_script = """
        local bucket_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local burst_limit = tonumber(ARGV[2])
        local window_seconds = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        -- Aktuelle Bucket-Daten holen
        local bucket_data = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket_data[1]) or burst_limit
        local last_refill = tonumber(bucket_data[2]) or now
        
        -- Token nachfüllen basierend auf verstrichener Zeit
        local time_passed = now - last_refill
        local tokens_to_add = math.floor(time_passed * limit / window_seconds)
        tokens = math.min(burst_limit, tokens + tokens_to_add)
        
        -- Request erlaubt?
        local allowed = 0
        if tokens > 0 then
            tokens = tokens - 1
            allowed = 1
        end
        
        -- Bucket-State aktualisieren
        redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_refill', now)
        redis.call('EXPIRE', bucket_key, window_seconds * 2)
        
        -- Reset-Zeit berechnen (wann nächster Token verfügbar)
        local reset_time = now + (window_seconds / limit)
        
        return {allowed, limit, tokens, reset_time}
        """
        
        try:
            result = self.redis.eval(
                lua_script, 
                1, 
                bucket_key, 
                limit, 
                burst_limit, 
                window_seconds, 
                now
            )
            
            allowed, rate_limit, remaining, reset_time = result
            retry_after = None if allowed else int(reset_time - now)
            
            return RateLimitResult(
                allowed=bool(allowed),
                limit=rate_limit,
                remaining=int(remaining),
                reset_time=int(reset_time),
                retry_after=retry_after
            )
            
        except Exception as e:
            logging.error(f"Rate limiting error: {e}")
            # Fallback: Request erlauben bei Redis-Fehlern
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_time=int(now + window_seconds)
            )
    
    def _sliding_window_check(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        """Sliding-Window-Algorithmus"""
        
        now = time.time()
        window_key = f"rate_limit:sliding_window:{key}"
        
        # Lua-Script für Sliding-Window
        lua_script = """
        local window_key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local window_seconds = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local precision = tonumber(ARGV[4]) or 10
        
        -- Alte Einträge entfernen
        local cutoff = now - window_seconds
        redis.call('ZREMRANGEBYSCORE', window_key, '-inf', cutoff)
        
        -- Aktuelle Request-Anzahl zählen
        local current_requests = redis.call('ZCARD', window_key)
        
        local allowed = 0
        if current_requests < limit then
            -- Request hinzufügen
            redis.call('ZADD', window_key, now, now .. ':' .. math.random())
            redis.call('EXPIRE', window_key, window_seconds + 1)
            allowed = 1
            current_requests = current_requests + 1
        end
        
        local remaining = math.max(0, limit - current_requests)
        local reset_time = now + window_seconds
        
        return {allowed, limit, remaining, reset_time}
        """
        
        try:
            result = self.redis.eval(
                lua_script,
                1,
                window_key,
                limit,
                window_seconds,
                now,
                10  # Precision in seconds
            )
            
            allowed, rate_limit, remaining, reset_time = result
            retry_after = None if allowed else window_seconds
            
            return RateLimitResult(
                allowed=bool(allowed),
                limit=rate_limit,
                remaining=int(remaining),
                reset_time=int(reset_time),
                retry_after=retry_after
            )
            
        except Exception as e:
            logging.error(f"Sliding window rate limiting error: {e}")
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_time=int(now + window_seconds)
            )

class RateLimitManager:
    def __init__(self, config_file: str = None):
        self.config = {}
        self.redis_client = None
        self.rate_limiter = None
        
        if config_file:
            self.load_config(config_file)
        
        # Redis-Verbindung
        self.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )
        
        # Rate-Limiter initialisieren
        algorithm = RateLimitAlgorithm.TOKEN_BUCKET
        if self.config.get('rate_limiting', {}).get('algorithms', {}).get('default') == 'sliding_window':
            algorithm = RateLimitAlgorithm.SLIDING_WINDOW
        
        self.rate_limiter = RateLimiter(self.redis_client, algorithm)
    
    def load_config(self, config_file: str):
        """Lädt Rate-Limiting-Konfiguration"""
        
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading rate limiting config: {e}")
            self.config = {}
    
    def get_rate_limit_for_endpoint(self, service: str, endpoint: str, method: str) -> Tuple[int, int, int]:
        """Gibt Rate-Limit für Endpoint zurück (limit, burst_limit, window_seconds)"""
        
        rate_limiting_config = self.config.get('rate_limiting', {})
        services_config = rate_limiting_config.get('services', {})
        service_config = services_config.get(service, {})
        
        # Endpoint-spezifische Limits
        endpoint_key = f"{method} {endpoint}"
        endpoint_limits = service_config.get('endpoint_limits', {})
        
        if endpoint_key in endpoint_limits:
            endpoint_config = endpoint_limits[endpoint_key]
            limit = endpoint_config.get('requests_per_minute', 1000)
            burst_limit = endpoint_config.get('burst_limit', limit // 5)
            return limit, burst_limit, 60
        
        # Service-globale Limits
        global_limit_config = service_config.get('global_limit', {})
        if global_limit_config:
            limit = global_limit_config.get('requests_per_minute', 1000)
            burst_limit = global_limit_config.get('burst_limit', limit // 5)
            return limit, burst_limit, 60
        
        # Default-Limits
        default_limits = rate_limiting_config.get('default_limits', {})
        limit = default_limits.get('requests_per_minute', 1000)
        burst_limit = default_limits.get('burst_limit', 200)
        
        return limit, burst_limit, 60
    
    def check_rate_limit(self, 
                        client_id: str,
                        service: str, 
                        endpoint: str, 
                        method: str,
                        user_type: Optional[str] = None) -> RateLimitResult:
        """Prüft Rate-Limit für Request"""
        
        # Rate-Limit-Parameter ermitteln
        limit, burst_limit, window_seconds = self.get_rate_limit_for_endpoint(service, endpoint, method)
        
        # User-spezifische Anpassungen
        if user_type:
            limit, burst_limit = self._apply_user_type_multiplier(limit, burst_limit, user_type)
        
        # Zeit-spezifische Anpassungen (Trading Hours, etc.)
        limit, burst_limit = self._apply_time_based_multipliers(limit, burst_limit)
        
        # Rate-Limit-Key erstellen
        rate_limit_key = f"{service}:{endpoint}:{method}:{client_id}"
        
        # Rate-Limit prüfen
        return self.rate_limiter.check_rate_limit(rate_limit_key, limit, window_seconds, burst_limit)
    
    def _apply_user_type_multiplier(self, limit: int, burst_limit: int, user_type: str) -> Tuple[int, int]:
        """Wendet User-Type-spezifische Multiplier an"""
        
        user_limits = self.config.get('rate_limiting', {}).get('client_limits', {})
        
        if user_type in user_limits:
            user_config = user_limits[user_type]
            user_limit = user_config.get('requests_per_minute', limit)
            user_burst = user_config.get('burst_limit', burst_limit)
            
            # Nehme das Minimum aus Endpoint- und User-Limits
            return min(limit, user_limit), min(burst_limit, user_burst)
        
        return limit, burst_limit
    
    def _apply_time_based_multipliers(self, limit: int, burst_limit: int) -> Tuple[int, int]:
        """Wendet zeit-basierte Multiplier an"""
        
        special_rules = self.config.get('rate_limiting', {}).get('special_rules', {})
        now = datetime.now(timezone.utc)
        
        # Trading Hours
        trading_hours = special_rules.get('trading_hours', {})
        if trading_hours.get('enabled', False):
            if self._is_trading_hours(now, trading_hours):
                multiplier = trading_hours.get('multiplier', 1.5)
                limit = int(limit * multiplier)
                burst_limit = int(burst_limit * multiplier)
        
        # Maintenance Hours
        maintenance_hours = special_rules.get('maintenance_hours', {})
        if maintenance_hours.get('enabled', False):
            if self._is_maintenance_hours(now, maintenance_hours):
                multiplier = maintenance_hours.get('multiplier', 0.3)
                limit = int(limit * multiplier)
                burst_limit = int(burst_limit * multiplier)
        
        # Emergency Mode
        emergency_mode = special_rules.get('emergency_mode', {})
        if emergency_mode.get('enabled', False):
            multiplier = emergency_mode.get('global_multiplier', 0.1)
            limit = int(limit * multiplier)
            burst_limit = int(burst_limit * multiplier)
        
        return limit, burst_limit
    
    def _is_trading_hours(self, now: datetime, trading_config: Dict) -> bool:
        """Prüft ob aktuelle Zeit in Trading-Hours liegt"""
        
        # Vereinfachte Implementierung - nur Wochentage
        if now.weekday() >= 5:  # Samstag/Sonntag
            return False
        
        weekday_config = trading_config.get('weekdays', {})
        start_time = weekday_config.get('start_time', '09:00')
        end_time = weekday_config.get('end_time', '17:30')
        
        current_time = now.strftime('%H:%M')
        return start_time <= current_time <= end_time
    
    def _is_maintenance_hours(self, now: datetime, maintenance_config: Dict) -> bool:
        """Prüft ob aktuelle Zeit in Maintenance-Hours liegt"""
        
        schedule = maintenance_config.get('schedule', [])
        
        for maintenance_window in schedule:
            if maintenance_window.get('day') == now.strftime('%A').lower():
                start_time = maintenance_window.get('start_time')
                end_time = maintenance_window.get('end_time')
                current_time = now.strftime('%H:%M')
                
                if start_time <= current_time <= end_time:
                    return True
        
        return False

# Flask-Middleware für Rate-Limiting
class RateLimitingMiddleware:
    def __init__(self, app: Flask, rate_limit_manager: RateLimitManager):
        self.app = app
        self.rate_limit_manager = rate_limit_manager
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup Rate-Limiting-Middleware"""
        
        @self.app.before_request
        def check_rate_limit():
            # Client-ID ermitteln (IP + User-Agent Hash)
            client_id = self._get_client_id(request)
            
            # Service und Endpoint ermitteln
            service = self._get_service_name(request)
            endpoint = self._normalize_endpoint(request.path)
            method = request.method
            
            # User-Type ermitteln (falls verfügbar)
            user_type = getattr(g, 'user_type', None)
            
            # Rate-Limit prüfen
            result = self.rate_limit_manager.check_rate_limit(
                client_id=client_id,
                service=service,
                endpoint=endpoint,
                method=method,
                user_type=user_type
            )
            
            # Rate-Limit-Headers setzen
            g.rate_limit_result = result
            
            # Request blockieren falls Limit überschritten
            if not result.allowed:
                response_config = self.rate_limit_manager.config.get(
                    'rate_limiting', {}
                ).get('rate_limit_responses', {})
                
                error_response = {
                    'success': False,
                    'error': {
                        'code': 'RATE_LIMIT_EXCEEDED',
                        'message': 'Rate limit exceeded. Please try again later.',
                        'details': {
                            'limit': result.limit,
                            'remaining': result.remaining,
                            'reset_time': result.reset_time,
                            'retry_after_seconds': result.retry_after
                        }
                    }
                }
                
                response = jsonify(error_response)
                response.status_code = 429
                
                # Rate-Limit-Headers hinzufügen
                self._add_rate_limit_headers(response, result)
                
                return response
        
        @self.app.after_request
        def add_rate_limit_headers(response):
            """Fügt Rate-Limit-Headers zu Response hinzu"""
            
            if hasattr(g, 'rate_limit_result'):
                self._add_rate_limit_headers(response, g.rate_limit_result)
            
            return response
    
    def _get_client_id(self, request_obj) -> str:
        """Generiert Client-ID aus Request"""
        
        # Basis: IP-Adresse
        client_ip = request_obj.environ.get(
            'HTTP_X_FORWARDED_FOR', 
            request_obj.environ.get('HTTP_X_REAL_IP', request_obj.remote_addr)
        )
        
        # Falls User authentifiziert: User-ID verwenden
        if hasattr(g, 'user_id') and g.user_id:
            return f"user:{g.user_id}"
        
        # Falls API-Key: API-Key-Hash verwenden
        api_key = request_obj.headers.get('X-API-Key')
        if api_key:
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"api_key:{key_hash}"
        
        # Fallback: IP + User-Agent Hash
        user_agent = request_obj.headers.get('User-Agent', '')
        import hashlib
        client_hash = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
        
        return f"client:{client_hash}"
    
    def _get_service_name(self, request_obj) -> str:
        """Ermittelt Service-Name aus Request"""
        
        # Aus Environment-Variable oder Default
        import os
        return os.getenv('SERVICE_NAME', 'unknown_service')
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalisiert Endpoint-Path für Rate-Limiting"""
        
        # Entferne API-Version aus Path
        import re
        path = re.sub(r'/api/v\d+', '/api/v{version}', path)
        
        # Ersetze UUIDs und IDs mit Platzhaltern
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path
    
    def _add_rate_limit_headers(self, response, result: RateLimitResult):
        """Fügt Rate-Limit-Headers zu Response hinzu"""
        
        response.headers['X-RateLimit-Limit'] = str(result.limit)
        response.headers['X-RateLimit-Remaining'] = str(result.remaining)
        response.headers['X-RateLimit-Reset'] = str(result.reset_time)
        
        if result.retry_after:
            response.headers['Retry-After'] = str(result.retry_after)

# Rate-Limiting-Decorator
def rate_limit(limit: int, burst_limit: Optional[int] = None, window_seconds: int = 60):
    """Decorator für endpoint-spezifisches Rate-Limiting"""
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Rate-Limit prüfen (vereinfachte Implementierung)
            # In echter Implementierung würde hier RateLimitManager verwendet
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test Rate-Limiting
    rate_limit_manager = RateLimitManager(
        "/home/mdoehler/aktienanalyse-ökosystem/config/rate-limiting.yaml"
    )
    
    # Test verschiedene Endpoints
    test_cases = [
        ('intelligent_core_service', '/api/v1/portfolios', 'GET'),
        ('broker_gateway_service', '/api/v1/orders', 'POST'),
        ('monitoring_service', '/api/v1/health', 'GET')
    ]
    
    for service, endpoint, method in test_cases:
        limit, burst_limit, window = rate_limit_manager.get_rate_limit_for_endpoint(
            service, endpoint, method
        )
        print(f"{service} {method} {endpoint}: {limit}/min, burst: {burst_limit}")
        
        # Simuliere Rate-Limit-Check
        result = rate_limit_manager.check_rate_limit(
            client_id="test_client",
            service=service,
            endpoint=endpoint,
            method=method
        )
        
        print(f"  Allowed: {result.allowed}, Remaining: {result.remaining}/{result.limit}")

---

## 🚨 **8. ERROR-RESPONSE-STANDARDS**

### 8.1 **Standardisierte HTTP-Status-Codes und Error-Objekte**
```yaml
# config/error-response-standards.yaml

error_response_standards:
  # HTTP-Status-Code-Mapping
  status_codes:
    # 2xx Success
    200:  # OK
      description: "Request erfolgreich verarbeitet"
      use_cases: ["GET requests", "Successful operations"]
      
    201:  # Created
      description: "Ressource erfolgreich erstellt"
      use_cases: ["POST requests", "Resource creation"]
      
    202:  # Accepted
      description: "Request akzeptiert, Verarbeitung läuft"
      use_cases: ["Asynchronous operations", "Long-running tasks"]
      
    204:  # No Content
      description: "Request erfolgreich, keine Daten zurück"
      use_cases: ["DELETE requests", "Update operations without response"]
    
    # 4xx Client Errors
    400:  # Bad Request
      description: "Ungültige Anfrage - Syntax oder Validierungsfehler"
      error_codes: ["VALIDATION_ERROR", "INVALID_JSON", "MISSING_PARAMETER"]
      use_cases: ["Invalid input", "Schema validation errors"]
      
    401:  # Unauthorized
      description: "Authentifizierung erforderlich oder fehlgeschlagen"
      error_codes: ["AUTHENTICATION_REQUIRED", "INVALID_CREDENTIALS", "TOKEN_EXPIRED"]
      use_cases: ["Missing auth", "Invalid credentials"]
      
    403:  # Forbidden
      description: "Zugriff verweigert - unzureichende Berechtigung"
      error_codes: ["INSUFFICIENT_PERMISSIONS", "ACCESS_DENIED", "RATE_LIMIT_EXCEEDED"]
      use_cases: ["Authorization failures", "Rate limiting"]
      
    404:  # Not Found
      description: "Ressource nicht gefunden"
      error_codes: ["RESOURCE_NOT_FOUND", "ENDPOINT_NOT_FOUND"]
      use_cases: ["Missing resources", "Invalid URLs"]
      
    409:  # Conflict
      description: "Konflikt mit aktuellem Ressourcen-Zustand"
      error_codes: ["RESOURCE_ALREADY_EXISTS", "CONCURRENT_MODIFICATION", "BUSINESS_RULE_VIOLATION"]
      use_cases: ["Duplicate creation", "Optimistic locking failures"]
      
    422:  # Unprocessable Entity
      description: "Request syntaktisch korrekt, aber semantisch ungültig"
      error_codes: ["BUSINESS_VALIDATION_ERROR", "INSUFFICIENT_FUNDS", "INVALID_TRADING_HOURS"]
      use_cases: ["Business rule violations", "Domain-specific errors"]
      
    429:  # Too Many Requests
      description: "Rate-Limit überschritten"
      error_codes: ["RATE_LIMIT_EXCEEDED"]
      use_cases: ["Rate limiting", "DDoS protection"]
    
    # 5xx Server Errors
    500:  # Internal Server Error
      description: "Unerwarteter Server-Fehler"
      error_codes: ["INTERNAL_SERVER_ERROR", "UNHANDLED_EXCEPTION"]
      use_cases: ["Unexpected errors", "System failures"]
      
    502:  # Bad Gateway
      description: "Fehler beim Upstream-Service"
      error_codes: ["UPSTREAM_SERVICE_ERROR", "BROKER_API_ERROR"]
      use_cases: ["External API failures", "Service dependencies down"]
      
    503:  # Service Unavailable
      description: "Service temporär nicht verfügbar"
      error_codes: ["SERVICE_UNAVAILABLE", "MAINTENANCE_MODE", "OVERLOADED"]
      use_cases: ["Maintenance", "System overload"]
      
    504:  # Gateway Timeout
      description: "Timeout bei Upstream-Service"
      error_codes: ["UPSTREAM_TIMEOUT", "BROKER_TIMEOUT"]
      use_cases: ["External API timeouts", "Slow dependencies"]

  # Standard-Error-Response-Format
  response_format:
    success:
      type: "boolean"
      value: false
      description: "Immer false bei Fehlern"
      
    error:
      type: "object"
      required: ["code", "message"]
      properties:
        code:
          type: "string"
          description: "Maschinenlesbarer Error-Code"
          pattern: "^[A-Z_]+$"
          examples: ["VALIDATION_ERROR", "RESOURCE_NOT_FOUND"]
          
        message:
          type: "string"
          description: "Benutzerfreundliche Fehlermeldung"
          max_length: 500
          
        details:
          type: "object"
          description: "Zusätzliche Fehler-Details"
          optional: true
          
        field_errors:
          type: "object"
          description: "Feld-spezifische Validierungsfehler"
          optional: true
          pattern: "field_name -> error_message"
          
        trace_id:
          type: "string"
          format: "uuid"
          description: "Eindeutige Trace-ID für Debugging"
          optional: true
          
        suggestion:
          type: "string"
          description: "Vorschlag zur Fehlerbehebung"
          optional: true
          
        documentation_url:
          type: "string"
          format: "uri"
          description: "Link zur relevanten Dokumentation"
          optional: true
    
    meta:
      type: "object"
      description: "Metadata über Response"
      optional: true
      properties:
        timestamp:
          type: "string"
          format: "date-time"
          description: "Zeitstempel der Fehler-Antwort"
          
        api_version:
          type: "string"
          description: "Verwendete API-Version"
          
        service:
          type: "string"
          description: "Service der den Fehler zurückgab"
          
        request_id:
          type: "string"
          format: "uuid"
          description: "Eindeutige Request-ID"

  # Service-spezifische Error-Codes
  service_error_codes:
    intelligent_core_service:
      # Portfolio-Errors
      PORTFOLIO_NOT_FOUND:
        http_status: 404
        message: "Portfolio nicht gefunden"
        suggestion: "Prüfen Sie die Portfolio-ID und versuchen Sie es erneut"
        
      PORTFOLIO_ALREADY_EXISTS:
        http_status: 409
        message: "Portfolio mit diesem Namen existiert bereits"
        suggestion: "Wählen Sie einen anderen Portfolio-Namen"
        
      INVALID_ALLOCATION:
        http_status: 422
        message: "Ungültige Asset-Allokation"
        suggestion: "Allokationen müssen in Summe 100% ergeben"
        
      # Risk-Errors
      RISK_LIMIT_EXCEEDED:
        http_status: 422
        message: "Risiko-Limit überschritten"
        suggestion: "Reduzieren Sie die Positionsgröße oder passen Sie Risk-Limits an"
        
      INSUFFICIENT_FUNDS:
        http_status: 422
        message: "Unzureichende Geldmittel"
        suggestion: "Fügen Sie Geld hinzu oder reduzieren Sie die Order-Größe"
        
      # Analysis-Errors
      ANALYSIS_NOT_AVAILABLE:
        http_status: 503
        message: "Asset-Analyse temporär nicht verfügbar"
        suggestion: "Versuchen Sie es in wenigen Minuten erneut"

    broker_gateway_service:
      # Order-Errors
      INVALID_ORDER_TYPE:
        http_status: 400
        message: "Ungültiger Order-Typ"
        suggestion: "Verwenden Sie: market, limit, stop oder stop_limit"
        
      ORDER_NOT_FOUND:
        http_status: 404
        message: "Order nicht gefunden"
        suggestion: "Prüfen Sie die Order-ID"
        
      ORDER_ALREADY_FILLED:
        http_status: 409
        message: "Order bereits vollständig ausgeführt"
        suggestion: "Ausgeführte Orders können nicht storniert werden"
        
      # Market-Data-Errors
      ASSET_NOT_TRADEABLE:
        http_status: 422
        message: "Asset ist nicht handelbar"
        suggestion: "Wählen Sie ein anderes Asset oder prüfen Sie die Handelszeiten"
        
      MARKET_CLOSED:
        http_status: 422
        message: "Markt ist geschlossen"
        suggestion: "Trading ist nur während der Handelszeiten möglich"
        
      # Broker-Integration-Errors
      BROKER_API_ERROR:
        http_status: 502
        message: "Broker-API-Fehler"
        suggestion: "Broker-Service ist temporär nicht verfügbar"
        
      BROKER_TIMEOUT:
        http_status: 504
        message: "Broker-API-Timeout"
        suggestion: "Versuchen Sie es erneut oder kontaktieren Sie den Support"

    event_bus_service:
      # Event-Errors
      INVALID_EVENT_SCHEMA:
        http_status: 400
        message: "Event entspricht nicht dem erwarteten Schema"
        suggestion: "Prüfen Sie die Event-Struktur gegen das Schema"
        
      EVENT_STREAM_NOT_FOUND:
        http_status: 404
        message: "Event-Stream nicht gefunden"
        suggestion: "Erstellen Sie den Stream oder prüfen Sie den Stream-Namen"
        
      PROJECTION_REBUILD_FAILED:
        http_status: 500
        message: "Projection-Rebuild fehlgeschlagen"
        suggestion: "Prüfen Sie die Logs und versuchen Sie es erneut"

    monitoring_service:
      # Monitoring-Errors
      METRIC_NOT_FOUND:
        http_status: 404
        message: "Metrik nicht gefunden"
        suggestion: "Prüfen Sie den Metrik-Namen und Zeitbereich"
        
      ALERT_RULE_INVALID:
        http_status: 400
        message: "Ungültige Alert-Rule"
        suggestion: "Prüfen Sie die Rule-Syntax"

    frontend_service:
      # Authentication-Errors
      INVALID_CREDENTIALS:
        http_status: 401
        message: "Ungültige Anmeldedaten"
        suggestion: "Prüfen Sie Benutzername und Passwort"
        
      SESSION_EXPIRED:
        http_status: 401
        message: "Sitzung abgelaufen"
        suggestion: "Melden Sie sich erneut an"
        
      # Configuration-Errors
      INVALID_CONFIGURATION:
        http_status: 400
        message: "Ungültige Konfiguration"
        suggestion: "Prüfen Sie die Konfigurationswerte"

  # Error-Response-Templates
  response_templates:
    validation_error:
      template:
        success: false
        error:
          code: "VALIDATION_ERROR"
          message: "Request validation failed"
          details:
            validation_errors: []
          suggestion: "Please check the request format and required fields"
      
    resource_not_found:
      template:
        success: false
        error:
          code: "RESOURCE_NOT_FOUND"
          message: "Requested resource was not found"
          suggestion: "Please verify the resource ID and try again"
      
    internal_server_error:
      template:
        success: false
        error:
          code: "INTERNAL_SERVER_ERROR"
          message: "An unexpected error occurred"
          suggestion: "Please try again later or contact support if the problem persists"
          
    rate_limit_exceeded:
      template:
        success: false
        error:
          code: "RATE_LIMIT_EXCEEDED"
          message: "Rate limit exceeded"
          details:
            limit: "${limit}"
            remaining: "${remaining}"
            reset_time: "${reset_time}"
          suggestion: "Please reduce request frequency and try again after the reset time"
```

Damit sind alle kritischen API-Interface-Spezifikationen komplett definiert. Das aktienanalyse-ökosystem hat jetzt vollständige OpenAPI-Spezifikationen für alle 5 Services, WebSocket-Event-Protokolle, Event-Schema-Validierung, Service-zu-Service-APIs, API-Versionierung-Strategy, Rate-Limiting-Definitionen und Error-Response-Standards.