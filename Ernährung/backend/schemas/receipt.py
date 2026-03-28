from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal

class ReceiptScanBase(BaseModel):
    image_path: str = Field(..., min_length=1, max_length=500, description="Pfad zum Bild")
    scan_status: str = Field("pending", description="Scan Status (pending, processing, completed, failed)")
    ocr_service: Optional[str] = Field(None, max_length=50, description="Verwendeter OCR Service")
    raw_ocr_result: Optional[Dict[str, Any]] = Field(None, description="Rohe OCR Ergebnisse")
    processed_items: Optional[List[Dict[str, Any]]] = Field(None, description="Verarbeitete Artikel")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Vertrauensgrad")
    manual_corrections: Optional[Dict[str, Any]] = Field(None, description="Manuelle Korrekturen")

class ReceiptScanCreate(BaseModel):
    image_path: str = Field(..., min_length=1, max_length=500)

class ReceiptScanUpdate(BaseModel):
    scan_status: Optional[str] = None
    ocr_service: Optional[str] = Field(None, max_length=50)
    raw_ocr_result: Optional[Dict[str, Any]] = None
    processed_items: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    manual_corrections: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None

class ReceiptScan(ReceiptScanBase):
    id: int
    created_at: datetime
    processed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ProcessedReceiptItem(BaseModel):
    product_name: str
    quantity: str
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    confidence: Optional[float] = None
    matched_product_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class ReceiptProcessingResult(BaseModel):
    scan_id: int
    status: str
    confidence: Optional[Decimal]
    items: List[ProcessedReceiptItem]
    service_used: Optional[str]
    
    class Config:
        from_attributes = True