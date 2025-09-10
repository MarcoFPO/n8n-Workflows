from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from ..database.connection import get_database
from ..models.schemas import (
    ReceiptScan as ReceiptScanSchema,
    APIResponse
)
from ..services.ocr_service import OCRService

router = APIRouter()

@router.post("/receipts/scan")
async def scan_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    """Upload and process receipt with OCR"""
    try:
        ocr_service = OCRService(db)
        result = await ocr_service.process_receipt_upload(file)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing receipt: {str(e)}"
        )

@router.get("/receipts/{scan_id}/status")
async def get_scan_status(
    scan_id: int,
    db: Session = Depends(get_database)
):
    """Get receipt processing status"""
    try:
        ocr_service = OCRService(db)
        status = ocr_service.get_scan_status(scan_id)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting scan status: {str(e)}"
        )

@router.post("/receipts/{scan_id}/confirm")
async def confirm_receipt_items(
    scan_id: int,
    confirmed_items: List[dict],
    db: Session = Depends(get_database)
):
    """Confirm and correct OCR results"""
    try:
        ocr_service = OCRService(db)
        result = ocr_service.confirm_scan_results(scan_id, confirmed_items)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error confirming receipt items: {str(e)}"
        )