from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import base64
from fastapi import UploadFile
import json

from ..database.models import ReceiptScan, AldiProduct
from ..core.config import settings

class OCRService:
    """Service for OCR processing of receipts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.openai_client = None
        self.google_vision_client = None
        
        # Initialize OCR clients if API keys are available
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                pass
    
    async def process_receipt_upload(self, file: UploadFile) -> Dict[str, Any]:
        """Process uploaded receipt file"""
        
        # Save uploaded file
        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"receipt_{datetime.now().timestamp()}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create receipt scan record
        scan_record = ReceiptScan(
            image_path=file_path,
            scan_status="pending",
            created_at=datetime.now()
        )
        self.db.add(scan_record)
        self.db.commit()
        self.db.refresh(scan_record)
        
        # Process with OCR (async in production)
        if settings.ENABLE_OCR:
            try:
                await self._process_with_ocr(scan_record.id, file_path)
            except Exception as e:
                # Update scan status to failed
                scan_record.scan_status = "failed"
                scan_record.processed_at = datetime.now()
                self.db.commit()
                raise e
        
        return {
            "scan_id": scan_record.id,
            "status": scan_record.scan_status,
            "message": "Receipt uploaded successfully"
        }
    
    async def _process_with_ocr(self, scan_id: int, image_path: str):
        """Process receipt with OCR services"""
        
        scan_record = self.db.query(ReceiptScan).filter(ReceiptScan.id == scan_id).first()
        if not scan_record:
            return
        
        # Update status to processing
        scan_record.scan_status = "processing"
        self.db.commit()
        
        ocr_result = None
        service_used = None
        
        try:
            # Try OpenAI Vision first
            if self.openai_client:
                ocr_result = await self._process_with_openai(image_path)
                service_used = "openai"
            else:
                # Fallback to Google Vision (if available)
                ocr_result = await self._process_with_google_vision(image_path)
                service_used = "google_vision"
            
            # Match products with database
            matched_products = await self._match_products(ocr_result.get('items', []))
            
            # Update scan record
            scan_record.scan_status = "completed"
            scan_record.ocr_service = service_used
            scan_record.raw_ocr_result = ocr_result
            scan_record.processed_items = matched_products
            scan_record.confidence_score = ocr_result.get('confidence', 0.0)
            scan_record.processed_at = datetime.now()
            
        except Exception as e:
            scan_record.scan_status = "failed"
            scan_record.processed_at = datetime.now()
            
        self.db.commit()
    
    async def _process_with_openai(self, image_path: str) -> Dict[str, Any]:
        """Process receipt using OpenAI Vision API"""
        
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode()
        
        # Simplified OCR simulation (replace with actual OpenAI Vision API call)
        # In production, use: self.openai_client.chat.completions.create(...)
        
        # Mock response for development
        mock_result = {
            'items': [
                {'name': 'Milch 1L', 'quantity': '1', 'unit_price': '1.29', 'total_price': '1.29'},
                {'name': 'Brot Vollkorn', 'quantity': '1', 'unit_price': '2.49', 'total_price': '2.49'},
                {'name': 'Bananen', 'quantity': '1.2kg', 'unit_price': '1.99', 'total_price': '2.39'}
            ],
            'confidence': 0.85,
            'total_amount': '6.17'
        }
        
        return mock_result
    
    async def _process_with_google_vision(self, image_path: str) -> Dict[str, Any]:
        """Process receipt using Google Vision API"""
        
        # Mock response for development
        mock_result = {
            'items': [
                {'name': 'Äpfel', 'quantity': '2kg', 'unit_price': '2.99', 'total_price': '5.98'},
                {'name': 'Joghurt', 'quantity': '4', 'unit_price': '0.79', 'total_price': '3.16'}
            ],
            'confidence': 0.78,
            'total_amount': '9.14'
        }
        
        return mock_result
    
    async def _match_products(self, ocr_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match OCR results with Aldi product database"""
        
        matched_items = []
        
        for item in ocr_items:
            product_name = item.get('name', '')
            
            # Simple fuzzy matching with Aldi products
            matched_product = self.db.query(AldiProduct).filter(
                AldiProduct.name.ilike(f"%{product_name[:10]}%")
            ).first()
            
            matched_item = {
                'ocr_name': product_name,
                'matched_product_id': matched_product.id if matched_product else None,
                'matched_product_name': matched_product.name if matched_product else None,
                'quantity': item.get('quantity'),
                'unit_price': item.get('unit_price'),
                'total_price': item.get('total_price'),
                'confidence': 0.8 if matched_product else 0.3
            }
            
            matched_items.append(matched_item)
        
        return matched_items
    
    def get_scan_status(self, scan_id: int) -> Dict[str, Any]:
        """Get receipt scan status"""
        
        scan_record = self.db.query(ReceiptScan).filter(ReceiptScan.id == scan_id).first()
        
        if not scan_record:
            return {"error": "Scan not found"}
        
        return {
            "scan_id": scan_id,
            "status": scan_record.scan_status,
            "confidence": float(scan_record.confidence_score) if scan_record.confidence_score else None,
            "items_count": len(scan_record.processed_items) if scan_record.processed_items else 0,
            "processed_at": scan_record.processed_at,
            "ocr_service": scan_record.ocr_service
        }
    
    def confirm_scan_results(self, scan_id: int, confirmed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Confirm and save corrected OCR results"""
        
        scan_record = self.db.query(ReceiptScan).filter(ReceiptScan.id == scan_id).first()
        
        if not scan_record:
            return {"error": "Scan not found"}
        
        # Save manual corrections
        scan_record.manual_corrections = {
            "confirmed_items": confirmed_items,
            "confirmed_at": datetime.now().isoformat()
        }
        
        self.db.commit()
        
        # Optionally add confirmed items to inventory
        from .inventory_service import InventoryService
        added_to_inventory = []
        
        for item in confirmed_items:
            if item.get('add_to_inventory', False) and item.get('matched_product_id'):
                # Add to inventory
                try:
                    from ..models.schemas import InventoryCreate
                    inventory_item = InventoryCreate(
                        product_id=item['matched_product_id'],
                        quantity=float(item.get('quantity', 1)),
                        purchase_date=datetime.now().date(),
                        location="Neu eingekauft"
                    )
                    
                    InventoryService.create_inventory_item(self.db, inventory_item)
                    added_to_inventory.append(item['matched_product_name'])
                except:
                    pass
        
        return {
            "scan_id": scan_id,
            "confirmed_items": len(confirmed_items),
            "added_to_inventory": added_to_inventory,
            "message": "Receipt confirmation completed"
        }