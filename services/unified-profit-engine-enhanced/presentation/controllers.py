#!/usr/bin/env python3
"""
Presentation Layer - FastAPI Controllers  
Unified Profit Engine Enhanced v6.0 - Clean Architecture

PRESENTATION LAYER RESPONSIBILITIES:
- HTTP Request/Response Handling
- Input Validation
- Authentication/Authorization
- Response Formatting
- Error Handling

Code-Qualität: HÖCHSTE PRIORITÄT - Clean Architecture Principles
Autor: Claude Code - Architecture Refactoring Specialist
Datum: 24. August 2025
"""

import asyncio
import time
from datetime import date, datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging

from fastapi import HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse

from .models import (
    MultiHorizonPredictionRequest,
    MultiHorizonPredictionResponse,
    ISTCalculationRequest,
    ISTCalculationResponse,
    PerformanceAnalysisRequest,
    PerformanceAnalysisResponse,
    HealthCheckResponse,
    ServiceMetricsResponse
)
from ..application.use_cases import (
    GenerateMultiHorizonPredictionsUseCase,
    CalculateISTPerformanceUseCase,
    GetPerformanceAnalysisUseCase
)
from ..domain.entities import PredictionHorizon


logger = logging.getLogger(__name__)


class UnifiedProfitEngineController:
    """
    REST API Controller für Unified Profit Engine Enhanced
    
    SOLID Principles:
    - Single Responsibility: Nur HTTP Request/Response Handling
    - Dependency Inversion: Abhängig von Use Case Interfaces
    - Open/Closed: Erweiterbar durch neue Endpoints ohne Änderung bestehender
    """
    
    def __init__(self,
                 prediction_use_case: GenerateMultiHorizonPredictionsUseCase,
                 ist_calculation_use_case: CalculateISTPerformanceUseCase,
                 performance_analysis_use_case: GetPerformanceAnalysisUseCase):
        self.prediction_use_case = prediction_use_case
        self.ist_calculation_use_case = ist_calculation_use_case
        self.performance_analysis_use_case = performance_analysis_use_case
        
        # Controller Metrics
        self.request_count = 0
        self.error_count = 0
        self.startup_time = datetime.now()
    
    async def generate_multi_horizon_predictions(
        self, 
        request: MultiHorizonPredictionRequest
    ) -> MultiHorizonPredictionResponse:
        """
        POST /api/v1/profit-engine/predictions/multi-horizon
        
        Generiert SOLL-Gewinn Vorhersagen für alle Horizonte
        Entspricht LLD v6.0 Multi-Horizon Prediction Requirements
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            logger.info(f"Processing multi-horizon prediction request for {len(request.symbols)} symbols")
            
            # Input Validation
            if not request.symbols:
                raise HTTPException(
                    status_code=400, 
                    detail="At least one symbol is required"
                )
            
            if len(request.symbols) > 50:  # Rate Limiting
                raise HTTPException(
                    status_code=400,
                    detail="Maximum 50 symbols per request allowed"
                )
            
            # Use Case Ausführung
            tracking_results = await self.prediction_use_case.execute(
                request.symbols
            )
            
            processing_time = time.time() - start_time
            
            # Response Mapping
            predictions_data = []
            for tracking in tracking_results:
                predictions_data.append({
                    "symbol": tracking.symbol.symbol,
                    "company_name": tracking.symbol.company_name,
                    "market_region": tracking.symbol.market_region,
                    "datum": tracking.datum.isoformat(),
                    "soll_gewinn_1w": float(tracking.get_soll_gewinn(PredictionHorizon.ONE_WEEK)) if tracking.get_soll_gewinn(PredictionHorizon.ONE_WEEK) else None,
                    "soll_gewinn_1m": float(tracking.get_soll_gewinn(PredictionHorizon.ONE_MONTH)) if tracking.get_soll_gewinn(PredictionHorizon.ONE_MONTH) else None,
                    "soll_gewinn_3m": float(tracking.get_soll_gewinn(PredictionHorizon.THREE_MONTHS)) if tracking.get_soll_gewinn(PredictionHorizon.THREE_MONTHS) else None,
                    "soll_gewinn_12m": float(tracking.get_soll_gewinn(PredictionHorizon.TWELVE_MONTHS)) if tracking.get_soll_gewinn(PredictionHorizon.TWELVE_MONTHS) else None,
                    "created_at": tracking.created_at.isoformat()
                })
            
            response = MultiHorizonPredictionResponse(
                success=True,
                predictions=predictions_data,
                processed_count=len(tracking_results),
                processing_time=processing_time,
                metadata={
                    "service": "unified-profit-engine-enhanced",
                    "version": "6.0",
                    "processed_symbols": request.symbols,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Multi-horizon predictions generated successfully: {len(tracking_results)} results in {processing_time:.2f}s")
            return response
            
        except HTTPException:
            self.error_count += 1
            raise
        except Exception as e:
            self.error_count += 1
            logger.error(f"Multi-horizon prediction generation failed: {e}")
            
            return MultiHorizonPredictionResponse(
                success=False,
                error=str(e),
                processed_count=0,
                processing_time=time.time() - start_time,
                predictions=[]
            )
    
    async def calculate_ist_performance(
        self,
        request: ISTCalculationRequest  
    ) -> ISTCalculationResponse:
        """
        POST /api/v1/profit-engine/ist/calculate
        
        Berechnet aktuelle IST-Performance für Symbole
        Entspricht LLD v6.0 IST Performance Calculation Requirements
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            logger.info(f"Processing IST calculation request for {len(request.symbols)} symbols")
            
            # Input Validation
            if not request.symbols:
                raise HTTPException(
                    status_code=400,
                    detail="At least one symbol is required"
                )
            
            # Use Case Ausführung
            ist_results = await self.ist_calculation_use_case.execute(
                request.symbols
            )
            
            processing_time = time.time() - start_time
            
            # Response Mapping
            ist_profits_data = {}
            for symbol, ist_gewinn in ist_results.items():
                ist_profits_data[symbol] = float(ist_gewinn)
            
            response = ISTCalculationResponse(
                success=True,
                ist_profits=ist_profits_data,
                calculated_count=len(ist_results),
                processing_time=processing_time,
                metadata={
                    "service": "unified-profit-engine-enhanced", 
                    "version": "6.0",
                    "calculated_symbols": list(ist_results.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"IST performance calculated successfully: {len(ist_results)} results in {processing_time:.2f}s")
            return response
            
        except HTTPException:
            self.error_count += 1
            raise
        except Exception as e:
            self.error_count += 1
            logger.error(f"IST performance calculation failed: {e}")
            
            return ISTCalculationResponse(
                success=False,
                error=str(e),
                calculated_count=0,
                processing_time=time.time() - start_time,
                ist_profits={}
            )
    
    async def get_performance_analysis(
        self,
        request: PerformanceAnalysisRequest
    ) -> PerformanceAnalysisResponse:
        """
        POST /api/v1/profit-engine/performance/analysis
        
        Lädt Performance-Analyse basierend auf Filtern
        Entspricht LLD v6.0 Performance Analysis Requirements
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            logger.info(f"Processing performance analysis request: symbol={request.symbol}, horizon={request.horizon}")
            
            # Horizon String zu Enum konvertieren (wenn angegeben)
            horizon_filter = None
            if request.horizon:
                try:
                    horizon_filter = PredictionHorizon(request.horizon)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid horizon: {request.horizon}. Valid values: 1W, 1M, 3M, 12M"
                    )
            
            # Use Case Ausführung
            performance_metrics = await self.performance_analysis_use_case.execute(
                symbol=request.symbol,
                horizon=horizon_filter,
                start_date=request.start_date,
                end_date=request.end_date
            )
            
            processing_time = time.time() - start_time
            
            # Response Mapping
            analysis_data = []
            for metric in performance_metrics:
                analysis_data.append({
                    "symbol": metric.symbol,
                    "tracking_date": metric.tracking_date.isoformat(),
                    "ist_gewinn": float(metric.ist_gewinn) if metric.ist_gewinn else None,
                    "soll_1w": float(metric.soll_1w) if metric.soll_1w else None,
                    "soll_1m": float(metric.soll_1m) if metric.soll_1m else None,
                    "soll_3m": float(metric.soll_3m) if metric.soll_3m else None,
                    "soll_12m": float(metric.soll_12m) if metric.soll_12m else None,
                    "diff_1w": float(metric.diff_1w) if metric.diff_1w else None,
                    "diff_1m": float(metric.diff_1m) if metric.diff_1m else None,
                    "diff_3m": float(metric.diff_3m) if metric.diff_3m else None,
                    "diff_12m": float(metric.diff_12m) if metric.diff_12m else None,
                    "accuracy_1w": metric.accuracy_1w,
                    "accuracy_1m": metric.accuracy_1m,
                    "accuracy_3m": metric.accuracy_3m,
                    "accuracy_12m": metric.accuracy_12m,
                    "best_horizon": metric.best_horizon,
                    "worst_horizon": metric.worst_horizon,
                    "overall_accuracy": metric.overall_accuracy
                })
            
            response = PerformanceAnalysisResponse(
                success=True,
                analysis_data=analysis_data,
                record_count=len(performance_metrics),
                processing_time=processing_time,
                filters={
                    "symbol": request.symbol,
                    "horizon": request.horizon,
                    "start_date": request.start_date.isoformat() if request.start_date else None,
                    "end_date": request.end_date.isoformat() if request.end_date else None
                },
                metadata={
                    "service": "unified-profit-engine-enhanced",
                    "version": "6.0",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Performance analysis completed successfully: {len(performance_metrics)} records in {processing_time:.2f}s")
            return response
            
        except HTTPException:
            self.error_count += 1
            raise
        except Exception as e:
            self.error_count += 1
            logger.error(f"Performance analysis failed: {e}")
            
            return PerformanceAnalysisResponse(
                success=False,
                error=str(e),
                record_count=0,
                processing_time=time.time() - start_time,
                analysis_data=[]
            )
    
    async def health_check(self) -> HealthCheckResponse:
        """
        GET /api/v1/profit-engine/health
        
        Service Health Check
        """
        try:
            # Service Health Check Logic
            current_time = datetime.now()
            uptime_seconds = (current_time - self.startup_time).total_seconds()
            
            # Dependency Health Checks können hier hinzugefügt werden
            # z.B. Database, Redis, External APIs
            
            response = HealthCheckResponse(
                healthy=True,
                service="unified-profit-engine-enhanced",
                version="6.0",
                uptime_seconds=int(uptime_seconds),
                timestamp=current_time.isoformat(),
                dependencies={
                    "database": {"status": "unknown", "description": "Health check not implemented"},
                    "redis": {"status": "unknown", "description": "Health check not implemented"},
                    "yahoo_finance": {"status": "unknown", "description": "Health check not implemented"}
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                healthy=False,
                service="unified-profit-engine-enhanced",
                version="6.0",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
    
    async def get_service_metrics(self) -> ServiceMetricsResponse:
        """
        GET /api/v1/profit-engine/metrics
        
        Service Metriken für Monitoring
        """
        try:
            current_time = datetime.now()
            uptime_seconds = (current_time - self.startup_time).total_seconds()
            
            metrics = ServiceMetricsResponse(
                service="unified-profit-engine-enhanced",
                version="6.0",
                uptime_seconds=int(uptime_seconds),
                request_count=self.request_count,
                error_count=self.error_count,
                success_rate=((self.request_count - self.error_count) / max(self.request_count, 1)) * 100,
                timestamp=current_time.isoformat(),
                additional_metrics={
                    "startup_time": self.startup_time.isoformat(),
                    "error_rate_percent": (self.error_count / max(self.request_count, 1)) * 100
                }
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            raise HTTPException(status_code=500, detail=f"Metrics collection failed: {e}")