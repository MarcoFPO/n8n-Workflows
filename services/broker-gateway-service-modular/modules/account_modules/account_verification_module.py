from typing import Dict, Any, List, Optional
import sys
from shared.common_imports import (
import asyncio
from ..single_function_module_base import SingleFunctionModule
"""
Account Verification Module - Single Function Module
Verantwortlich ausschließlich für Account Verification Logic
"""

sys.path.append('/home/mdoehler/aktienanalyse-ökosystem')

    datetime, timedelta, BaseModel, structlog
)


class VerificationRequest(BaseModel):
    verification_type: str  # 'kyc', 'aml', 'document', 'identity', 'address', 'source_of_funds'
    document_data: Optional[Dict[str, Any]] = None
    personal_data: Optional[Dict[str, Any]] = None
    verification_level: str = 'basic'  # 'basic', 'enhanced', 'premium'
    force_reverification: bool = False


class VerificationDocument(BaseModel):
    document_type: str  # 'passport', 'id_card', 'drivers_license', 'utility_bill', 'bank_statement'
    document_status: str  # 'pending', 'verified', 'rejected', 'expired'
    upload_timestamp: datetime
    verification_timestamp: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    validity_period_days: Optional[int] = None


class VerificationResult(BaseModel):
    verification_successful: bool
    verification_status: str  # 'pending', 'approved', 'rejected', 'incomplete', 'expired'
    verification_level_achieved: str
    verification_score: float  # 0-100
    required_documents: List[str]
    verified_documents: List[str]
    pending_documents: List[str]
    rejected_documents: List[str]
    verification_warnings: List[str]
    next_verification_due: Optional[datetime] = None
    compliance_notes: List[str]
    verification_timestamp: datetime


class AccountVerificationModule(SingleFunctionModule):
    """
    Single Function Module: Account Verification
    Verantwortlichkeit: Ausschließlich Account-Verification-Logic
    """
    
    def __init__(self, event_bus=None):
        super().__init__("account_verification", event_bus)
        
        # Verification Requirements Configuration
        self.verification_requirements = {
            'basic': {
                'required_documents': ['id_card', 'address_proof'],
                'min_verification_score': 70,
                'validity_period_days': 365,
                'max_transaction_amount': 10000.0,
                'max_monthly_volume': 50000.0
            },
            'enhanced': {
                'required_documents': ['passport', 'utility_bill', 'bank_statement'],
                'min_verification_score': 85,
                'validity_period_days': 730,
                'max_transaction_amount': 50000.0,
                'max_monthly_volume': 500000.0
            },
            'premium': {
                'required_documents': ['passport', 'utility_bill', 'bank_statement', 'source_of_funds'],
                'min_verification_score': 95,
                'validity_period_days': 365,
                'max_transaction_amount': 1000000.0,
                'max_monthly_volume': 10000000.0
            }
        }
        
        # Document Type Configuration
        self.document_types = {
            'passport': {
                'category': 'identity',
                'verification_weight': 40,
                'validity_period_days': 1825,  # 5 years
                'required_fields': ['full_name', 'date_of_birth', 'nationality', 'document_number']
            },
            'id_card': {
                'category': 'identity', 
                'verification_weight': 35,
                'validity_period_days': 1825,
                'required_fields': ['full_name', 'date_of_birth', 'document_number']
            },
            'drivers_license': {
                'category': 'identity',
                'verification_weight': 30,
                'validity_period_days': 1825,
                'required_fields': ['full_name', 'date_of_birth', 'address']
            },
            'utility_bill': {
                'category': 'address',
                'verification_weight': 25,
                'validity_period_days': 90,  # 3 months for address proof
                'required_fields': ['full_name', 'address', 'issue_date']
            },
            'bank_statement': {
                'category': 'financial',
                'verification_weight': 30,
                'validity_period_days': 90,
                'required_fields': ['account_holder_name', 'bank_name', 'statement_date']
            },
            'source_of_funds': {
                'category': 'financial',
                'verification_weight': 35,
                'validity_period_days': 365,
                'required_fields': ['source_type', 'amount', 'documentation']
            }
        }
        
        # Mock Verification Database
        self.account_verifications = {
            'current_status': 'basic_verified',
            'verification_level': 'basic',
            'verification_score': 82.5,
            'last_verification_date': datetime.now() - timedelta(days=45),
            'next_due_date': datetime.now() + timedelta(days=320),
            'verified_documents': ['id_card', 'utility_bill'],
            'pending_documents': [],
            'rejected_documents': [],
            'verification_history': []
        }
        
        # Mock Document Storage
        self.uploaded_documents = {
            'id_card': VerificationDocument(
                document_type='id_card',
                document_status='verified',
                upload_timestamp=datetime.now() - timedelta(days=50),
                verification_timestamp=datetime.now() - timedelta(days=45),
                validity_period_days=1825
            ),
            'utility_bill': VerificationDocument(
                document_type='utility_bill',
                document_status='verified',
                upload_timestamp=datetime.now() - timedelta(days=48),
                verification_timestamp=datetime.now() - timedelta(days=45),
                validity_period_days=90
            )
        }
        
        # Verification Processing History
        self.verification_history = []
        self.verification_counter = 0
        
        # AML/KYC Configuration
        self.compliance_config = {
            'pep_screening_required': True,
            'sanctions_screening_required': True,
            'adverse_media_screening': True,
            'enhanced_dd_threshold': 25000.0,  # Enhanced DD for amounts >25k
            'source_of_funds_threshold': 50000.0,  # SOF required for >50k
            'ongoing_monitoring_enabled': True,
            'risk_based_approach': True
        }
        
        # Verification Scoring Weights
        self.scoring_weights = {
            'document_authenticity': 0.3,
            'data_consistency': 0.25,
            'completeness': 0.2,
            'recency': 0.15,
            'third_party_verification': 0.1
        }
        
    async def execute_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hauptfunktion: Account Verification
        
        Args:
            input_data: {
                'verification_type': required string,
                'document_data': optional dict with document information,
                'personal_data': optional dict with personal information,
                'verification_level': optional string (default: 'basic'),
                'force_reverification': optional bool (default: false),
                'include_compliance_check': optional bool (default: true)
            }
            
        Returns:
            Dict mit Account-Verification-Result
        """
        start_time = datetime.now()
        
        try:
            # Verification Request erstellen
            verification_request = VerificationRequest(
                verification_type=input_data.get('verification_type'),
                document_data=input_data.get('document_data'),
                personal_data=input_data.get('personal_data'),
                verification_level=input_data.get('verification_level', 'basic'),
                force_reverification=input_data.get('force_reverification', False)
            )
        except Exception as e:
            return {
                'success': False,
                'error': f'Invalid verification request: {str(e)}'
            }
        
        include_compliance = input_data.get('include_compliance_check', True)
        
        # Verification Processing
        verification_result = await self._process_verification_request(
            verification_request, include_compliance
        )
        
        # Statistics Update
        self.verification_counter += 1
        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Verification History
        self.verification_history.append({
            'timestamp': datetime.now(),
            'verification_type': verification_request.verification_type,
            'verification_level': verification_request.verification_level,
            'verification_successful': verification_result.verification_successful,
            'verification_score': verification_result.verification_score,
            'verification_status': verification_result.verification_status,
            'documents_processed': len(verification_result.verified_documents + verification_result.rejected_documents),
            'processing_time_ms': processing_time_ms,
            'verification_id': self.verification_counter
        })
        
        # Limit History
        if len(self.verification_history) > 200:
            self.verification_history.pop(0)
        
        # Event Publishing für Verification Status Changes
        await self._publish_verification_event(verification_result, verification_request)
        
        self.logger.info(f"Account verification processed",
                       verification_type=verification_request.verification_type,
                       verification_successful=verification_result.verification_successful,
                       verification_score=verification_result.verification_score,
                       verification_status=verification_result.verification_status,
                       processing_time_ms=round(processing_time_ms, 2),
                       verification_id=self.verification_counter)
        
        return {
            'success': True,
            'verification_successful': verification_result.verification_successful,
            'verification_status': verification_result.verification_status,
            'verification_level_achieved': verification_result.verification_level_achieved,
            'verification_score': verification_result.verification_score,
            'required_documents': verification_result.required_documents,
            'verified_documents': verification_result.verified_documents,
            'pending_documents': verification_result.pending_documents,
            'rejected_documents': verification_result.rejected_documents,
            'verification_warnings': verification_result.verification_warnings,
            'next_verification_due': verification_result.next_verification_due.isoformat() if verification_result.next_verification_due else None,
            'compliance_notes': verification_result.compliance_notes,
            'verification_timestamp': verification_result.verification_timestamp.isoformat()
        }
    
    async def _process_verification_request(self, request: VerificationRequest,
                                          include_compliance: bool) -> VerificationResult:
        """Verarbeitet Verification Request komplett"""
        
        verification_warnings = []
        compliance_notes = []
        
        # Aktuelle Verification Status prüfen
        current_status = await self._get_current_verification_status()
        
        # Force Reverification Check
        if not request.force_reverification and current_status['verification_level'] == request.verification_level:
            if current_status['status'] == 'approved' and not await self._is_verification_expired():
                return await self._build_current_verification_result()
        
        # Document Verification
        document_results = await self._verify_documents(request)
        
        # Data Consistency Check
        consistency_score = await self._check_data_consistency(request)
        
        # Completeness Check
        completeness_score = await self._check_completeness(request)
        
        # Compliance Checks
        compliance_results = {}
        if include_compliance:
            compliance_results = await self._perform_compliance_checks(request)
            compliance_notes = compliance_results.get('notes', [])
        
        # Calculate Overall Verification Score
        verification_score = await self._calculate_verification_score(
            document_results, consistency_score, completeness_score, compliance_results
        )
        
        # Determine Verification Status
        verification_status = await self._determine_verification_status(
            request.verification_level, verification_score, document_results, compliance_results
        )
        
        # Bestimme achieved level
        achieved_level = await self._determine_achieved_level(verification_score, document_results)
        
        # Update internal state
        if verification_status == 'approved':
            await self._update_verification_state(request, verification_score, achieved_level)
        
        # Warnings generieren
        verification_warnings = await self._generate_verification_warnings(
            document_results, compliance_results, verification_score
        )
        
        # Next verification due date
        next_due = await self._calculate_next_verification_due(achieved_level)
        
        return VerificationResult(
            verification_successful=verification_status == 'approved',
            verification_status=verification_status,
            verification_level_achieved=achieved_level,
            verification_score=verification_score,
            required_documents=self.verification_requirements[request.verification_level]['required_documents'],
            verified_documents=document_results.get('verified', []),
            pending_documents=document_results.get('pending', []),
            rejected_documents=document_results.get('rejected', []),
            verification_warnings=verification_warnings,
            next_verification_due=next_due,
            compliance_notes=compliance_notes,
            verification_timestamp=datetime.now()
        )
    
    async def _get_current_verification_status(self) -> Dict[str, Any]:
        """Gibt aktuellen Verification Status zurück"""
        
        return {
            'status': self.account_verifications['current_status'],
            'verification_level': self.account_verifications['verification_level'],
            'verification_score': self.account_verifications['verification_score'],
            'last_verification': self.account_verifications['last_verification_date'],
            'verified_documents': self.account_verifications['verified_documents']
        }
    
    async def _is_verification_expired(self) -> bool:
        """Prüft ob Verification abgelaufen ist"""
        
        next_due = self.account_verifications.get('next_due_date')
        if not next_due:
            return True
        
        return datetime.now() > next_due
    
    async def _verify_documents(self, request: VerificationRequest) -> Dict[str, List[str]]:
        """Verifiziert Dokumente basierend auf Request"""
        
        results = {
            'verified': [],
            'pending': [],
            'rejected': []
        }
        
        required_docs = self.verification_requirements[request.verification_level]['required_documents']
        
        # Check each required document
        for doc_type in required_docs:
            if doc_type in self.uploaded_documents:
                doc = self.uploaded_documents[doc_type]
                
                # Check document status
                if doc.document_status == 'verified':
                    # Check if document is still valid
                    if await self._is_document_valid(doc):
                        results['verified'].append(doc_type)
                    else:
                        results['rejected'].append(doc_type)
                        # Update document status
                        doc.document_status = 'expired'
                elif doc.document_status == 'pending':
                    # Mock verification process
                    verification_result = await self._mock_document_verification(doc, request)
                    if verification_result['verified']:
                        results['verified'].append(doc_type)
                        doc.document_status = 'verified'
                        doc.verification_timestamp = datetime.now()
                    else:
                        results['rejected'].append(doc_type)
                        doc.document_status = 'rejected'
                        doc.rejection_reason = verification_result.get('reason', 'Verification failed')
                else:  # rejected or expired
                    results['rejected'].append(doc_type)
            else:
                # Document not uploaded
                results['pending'].append(doc_type)
        
        return results
    
    async def _is_document_valid(self, document: VerificationDocument) -> bool:
        """Prüft ob Dokument noch gültig ist"""
        
        if not document.verification_timestamp or not document.validity_period_days:
            return False
        
        expiry_date = document.verification_timestamp + timedelta(days=document.validity_period_days)
        return datetime.now() < expiry_date
    
    async def _mock_document_verification(self, document: VerificationDocument, 
                                        request: VerificationRequest) -> Dict[str, Any]:
        """Mock Document Verification Process"""
        
        # Mock verification logic - in production would use OCR, ML models, etc.
        doc_type = document.document_type
        doc_config = self.document_types.get(doc_type, {})
        
        # Simulate verification success rate based on document type
        verification_rates = {
            'passport': 0.95,
            'id_card': 0.90,
            'drivers_license': 0.85,
            'utility_bill': 0.80,
            'bank_statement': 0.85,
            'source_of_funds': 0.75
        }
        
        success_rate = verification_rates.get(doc_type, 0.8)
        
        # Mock verification (in reality would check document authenticity, data extraction, etc.)
        import random
        verification_successful = random.random() < success_rate
        
        if verification_successful:
            return {'verified': True}
        else:
            reasons = [
                'Document image quality too low',
                'Document appears to be tampered',
                'Required fields not clearly visible',
                'Document type not accepted',
                'Document has expired'
            ]
            return {
                'verified': False,
                'reason': random.choice(reasons)
            }
    
    async def _check_data_consistency(self, request: VerificationRequest) -> float:
        """Prüft Konsistenz der bereitgestellten Daten"""
        
        personal_data = request.personal_data or {}
        
        # Mock consistency check
        consistency_score = 0.85  # 85% consistency
        
        # Check if personal data matches document data
        if request.document_data:
            # Would compare names, dates, addresses across documents
            pass
        
        # Check against existing account data
        # Would verify email, phone, address consistency
        
        return consistency_score
    
    async def _check_completeness(self, request: VerificationRequest) -> float:
        """Prüft Vollständigkeit der bereitgestellten Informationen"""
        
        required_docs = self.verification_requirements[request.verification_level]['required_documents']
        uploaded_docs = list(self.uploaded_documents.keys())
        
        # Calculate completeness based on required vs available documents
        completeness = len([doc for doc in required_docs if doc in uploaded_docs]) / len(required_docs)
        
        # Adjust for data quality
        if request.personal_data:
            required_personal_fields = ['full_name', 'date_of_birth', 'address', 'nationality']
            provided_fields = len([field for field in required_personal_fields if field in request.personal_data])
            data_completeness = provided_fields / len(required_personal_fields)
            completeness = (completeness + data_completeness) / 2
        
        return completeness
    
    async def _perform_compliance_checks(self, request: VerificationRequest) -> Dict[str, Any]:
        """Führt Compliance Checks durch (AML/KYC)"""
        
        compliance_results = {
            'pep_check': 'clear',
            'sanctions_check': 'clear',
            'adverse_media_check': 'clear',
            'risk_score': 0.15,  # Low risk
            'notes': []
        }
        
        personal_data = request.personal_data or {}
        
        # PEP Screening
        if self.compliance_config['pep_screening_required']:
            pep_result = await self._perform_pep_screening(personal_data)
            compliance_results['pep_check'] = pep_result['status']
            if pep_result['status'] != 'clear':
                compliance_results['notes'].append(f"PEP screening: {pep_result['details']}")
        
        # Sanctions Screening
        if self.compliance_config['sanctions_screening_required']:
            sanctions_result = await self._perform_sanctions_screening(personal_data)
            compliance_results['sanctions_check'] = sanctions_result['status']
            if sanctions_result['status'] != 'clear':
                compliance_results['notes'].append(f"Sanctions screening: {sanctions_result['details']}")
        
        # Adverse Media Screening
        if self.compliance_config['adverse_media_screening']:
            media_result = await self._perform_adverse_media_screening(personal_data)
            compliance_results['adverse_media_check'] = media_result['status']
            if media_result['status'] != 'clear':
                compliance_results['notes'].append(f"Adverse media: {media_result['details']}")
        
        # Risk Score Calculation
        compliance_results['risk_score'] = await self._calculate_compliance_risk_score(compliance_results)
        
        return compliance_results
    
    async def _perform_pep_screening(self, personal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock PEP Screening"""
        # In production would check against PEP databases
        return {'status': 'clear', 'details': 'No PEP matches found'}
    
    async def _perform_sanctions_screening(self, personal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Sanctions Screening"""
        # In production would check against sanctions lists (OFAC, UN, EU, etc.)
        return {'status': 'clear', 'details': 'No sanctions matches found'}
    
    async def _perform_adverse_media_screening(self, personal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock Adverse Media Screening"""
        # In production would check news sources, legal databases, etc.
        return {'status': 'clear', 'details': 'No adverse media found'}
    
    async def _calculate_compliance_risk_score(self, compliance_results: Dict[str, Any]) -> float:
        """Berechnet Compliance Risk Score"""
        
        base_risk = 0.1  # Base risk
        
        # Adjust risk based on screening results
        if compliance_results['pep_check'] != 'clear':
            base_risk += 0.3
        
        if compliance_results['sanctions_check'] != 'clear':
            base_risk += 0.5
        
        if compliance_results['adverse_media_check'] != 'clear':
            base_risk += 0.2
        
        return min(1.0, base_risk)
    
    async def _calculate_verification_score(self, document_results: Dict[str, List],
                                          consistency_score: float, completeness_score: float,
                                          compliance_results: Dict[str, Any]) -> float:
        """Berechnet Overall Verification Score"""
        
        # Document Score
        total_docs = len(document_results['verified'] + document_results['rejected'] + document_results['pending'])
        verified_docs = len(document_results['verified'])
        document_score = verified_docs / total_docs if total_docs > 0 else 0
        
        # Compliance Score (inverse of risk)
        compliance_score = 1.0 - compliance_results.get('risk_score', 0.5)
        
        # Recency Score (how recent is the verification)
        recency_score = 1.0  # Full score for new verification
        
        # Third-party verification (mock - would be from external verification services)
        third_party_score = 0.8
        
        # Weighted Score
        weighted_score = (
            document_score * self.scoring_weights['document_authenticity'] +
            consistency_score * self.scoring_weights['data_consistency'] +
            completeness_score * self.scoring_weights['completeness'] +
            recency_score * self.scoring_weights['recency'] +
            third_party_score * self.scoring_weights['third_party_verification']
        ) * 100
        
        return round(min(100, max(0, weighted_score)), 1)
    
    async def _determine_verification_status(self, requested_level: str, verification_score: float,
                                           document_results: Dict[str, List],
                                           compliance_results: Dict[str, Any]) -> str:
        """Bestimmt Verification Status"""
        
        min_score = self.verification_requirements[requested_level]['min_verification_score']
        required_docs = set(self.verification_requirements[requested_level]['required_documents'])
        verified_docs = set(document_results['verified'])
        rejected_docs = document_results['rejected']
        
        # Check minimum score
        if verification_score < min_score:
            return 'rejected'
        
        # Check if all required documents are verified
        if not required_docs.issubset(verified_docs):
            if rejected_docs:
                return 'rejected'
            else:
                return 'pending'
        
        # Check compliance issues
        compliance_risk = compliance_results.get('risk_score', 0)
        if compliance_risk > 0.7:  # High compliance risk
            return 'rejected'
        elif compliance_risk > 0.4:  # Medium compliance risk
            return 'pending'
        
        return 'approved'
    
    async def _determine_achieved_level(self, verification_score: float, 
                                      document_results: Dict[str, List]) -> str:
        """Bestimmt achieved Verification Level"""
        
        verified_docs = set(document_results['verified'])
        
        # Check premium level
        premium_docs = set(self.verification_requirements['premium']['required_documents'])
        premium_score = self.verification_requirements['premium']['min_verification_score']
        
        if premium_docs.issubset(verified_docs) and verification_score >= premium_score:
            return 'premium'
        
        # Check enhanced level
        enhanced_docs = set(self.verification_requirements['enhanced']['required_documents'])
        enhanced_score = self.verification_requirements['enhanced']['min_verification_score']
        
        if enhanced_docs.issubset(verified_docs) and verification_score >= enhanced_score:
            return 'enhanced'
        
        # Check basic level
        basic_docs = set(self.verification_requirements['basic']['required_documents'])
        basic_score = self.verification_requirements['basic']['min_verification_score']
        
        if basic_docs.issubset(verified_docs) and verification_score >= basic_score:
            return 'basic'
        
        return 'none'
    
    async def _update_verification_state(self, request: VerificationRequest, 
                                       verification_score: float, achieved_level: str):
        """Aktualisiert interne Verification State"""
        
        self.account_verifications.update({
            'current_status': 'approved',
            'verification_level': achieved_level,
            'verification_score': verification_score,
            'last_verification_date': datetime.now(),
            'next_due_date': await self._calculate_next_verification_due(achieved_level)
        })
    
    async def _calculate_next_verification_due(self, verification_level: str) -> datetime:
        """Berechnet nächstes Verification Due Date"""
        
        validity_days = self.verification_requirements[verification_level]['validity_period_days']
        return datetime.now() + timedelta(days=validity_days)
    
    async def _generate_verification_warnings(self, document_results: Dict[str, List],
                                            compliance_results: Dict[str, Any],
                                            verification_score: float) -> List[str]:
        """Generiert Verification Warnings"""
        
        warnings = []
        
        # Low verification score warning
        if verification_score < 80:
            warnings.append(f"Low verification score ({verification_score:.1f}%) - consider providing additional documentation")
        
        # Document warnings
        if document_results['rejected']:
            warnings.append(f"Rejected documents: {', '.join(document_results['rejected'])} - re-submission required")
        
        if document_results['pending']:
            warnings.append(f"Pending documents: {', '.join(document_results['pending'])} - upload required")
        
        # Compliance warnings
        compliance_risk = compliance_results.get('risk_score', 0)
        if compliance_risk > 0.3:
            warnings.append(f"Elevated compliance risk ({compliance_risk:.1%}) - enhanced monitoring may apply")
        
        # Document expiry warnings
        for doc_type, doc in self.uploaded_documents.items():
            if await self._is_document_expiring_soon(doc):
                warnings.append(f"{doc_type} expires soon - renewal required")
        
        return warnings
    
    async def _is_document_expiring_soon(self, document: VerificationDocument, days_ahead: int = 30) -> bool:
        """Prüft ob Dokument bald abläuft"""
        
        if not document.verification_timestamp or not document.validity_period_days:
            return False
        
        expiry_date = document.verification_timestamp + timedelta(days=document.validity_period_days)
        warning_date = datetime.now() + timedelta(days=days_ahead)
        
        return expiry_date <= warning_date
    
    async def _build_current_verification_result(self) -> VerificationResult:
        """Erstellt VerificationResult basierend auf aktuellem Status"""
        
        current = self.account_verifications
        
        return VerificationResult(
            verification_successful=current['current_status'] == 'approved',
            verification_status=current['current_status'],
            verification_level_achieved=current['verification_level'],
            verification_score=current['verification_score'],
            required_documents=self.verification_requirements[current['verification_level']]['required_documents'],
            verified_documents=current['verified_documents'],
            pending_documents=[],
            rejected_documents=current.get('rejected_documents', []),
            verification_warnings=[],
            next_verification_due=current.get('next_due_date'),
            compliance_notes=[],
            verification_timestamp=current['last_verification_date']
        )
    
    async def _publish_verification_event(self, result: VerificationResult, 
                                        request: VerificationRequest):
        """Published Verification Event über Event-Bus"""
        
        if not self.event_bus or not self.event_bus.connected:
            return
        
        from event_bus import Event
        
        # Only publish for significant status changes
        if result.verification_status in ['approved', 'rejected']:
            event = Event(
                event_type="account_verification_completed",
                stream_id=f"verification-{self.verification_counter}",
                data={
                    'verification_type': request.verification_type,
                    'verification_successful': result.verification_successful,
                    'verification_status': result.verification_status,
                    'verification_level_achieved': result.verification_level_achieved,
                    'verification_score': result.verification_score,
                    'verified_documents_count': len(result.verified_documents),
                    'compliance_status': 'clean' if not result.compliance_notes else 'notes_present',
                    'verification_timestamp': result.verification_timestamp.isoformat()
                },
                source="account_verification"
            )
            
            await self.event_bus.publish(event)
    

        # Event-Bus Integration Setup
        if self.event_bus:
            asyncio.create_task(self._setup_event_subscriptions())

    def get_verification_status_summary(self) -> Dict[str, Any]:
        """Gibt Verification Status Summary zurück"""
        
        current = self.account_verifications
        
        # Document expiry warnings
        expiring_docs = []
        for doc_type, doc in self.uploaded_documents.items():
            if doc.verification_timestamp and doc.validity_period_days:
                expiry_date = doc.verification_timestamp + timedelta(days=doc.validity_period_days)
                days_until_expiry = (expiry_date - datetime.now()).days
                
                if days_until_expiry <= 30:  # Expires within 30 days
                    expiring_docs.append({
                        'document_type': doc_type,
                        'expiry_date': expiry_date.isoformat(),
                        'days_until_expiry': days_until_expiry
                    })
        
        # Available upgrade paths
        upgrade_paths = []
        current_level = current['verification_level']
        
        if current_level == 'basic':
            upgrade_paths.extend(['enhanced', 'premium'])
        elif current_level == 'enhanced':
            upgrade_paths.append('premium')
        
        return {
            'current_status': current['current_status'],
            'verification_level': current['verification_level'],
            'verification_score': current['verification_score'],
            'last_verification_date': current['last_verification_date'].isoformat(),
            'next_verification_due': current.get('next_due_date').isoformat() if current.get('next_due_date') else None,
            'verified_documents': current['verified_documents'],
            'expiring_documents': expiring_docs,
            'available_upgrades': upgrade_paths,
            'transaction_limits': {
                'max_transaction_amount': self.verification_requirements[current_level]['max_transaction_amount'],
                'max_monthly_volume': self.verification_requirements[current_level]['max_monthly_volume']
            }
        }
    
    def get_function_info(self) -> Dict[str, Any]:
        """Funktions-Metadaten"""
        return {
            'name': 'account_verification',
            'description': 'Complete account verification including KYC/AML compliance checks',
            'responsibility': 'Account verification logic only',
            'input_parameters': {
                'verification_type': 'Required verification type (kyc, aml, document, identity, address, source_of_funds)',
                'document_data': 'Optional document information for verification',
                'personal_data': 'Optional personal data for verification',
                'verification_level': 'Desired verification level (basic, enhanced, premium)',
                'force_reverification': 'Whether to force re-verification (default: false)',
                'include_compliance_check': 'Whether to include compliance checks (default: true)'
            },
            'output_format': {
                'verification_successful': 'Whether verification was successful',
                'verification_status': 'Verification status (pending, approved, rejected, incomplete, expired)',
                'verification_level_achieved': 'Verification level achieved',
                'verification_score': 'Verification score from 0-100',
                'required_documents': 'List of required documents for level',
                'verified_documents': 'List of successfully verified documents',
                'pending_documents': 'List of documents pending verification',
                'rejected_documents': 'List of rejected documents',
                'verification_warnings': 'List of verification warnings',
                'next_verification_due': 'Next verification due date',
                'compliance_notes': 'Compliance check notes',
                'verification_timestamp': 'Timestamp of verification'
            },
            'supported_verification_types': ['kyc', 'aml', 'document', 'identity', 'address', 'source_of_funds'],
            'supported_verification_levels': ['basic', 'enhanced', 'premium'],
            'supported_document_types': list(self.document_types.keys()),
            'verification_requirements': self.verification_requirements,
            'version': '1.0.0',
            'compliance': 'Single Function Module Pattern'
        }
    
    def get_verification_statistics(self) -> Dict[str, Any]:
        """Account Verification Module Statistiken"""
        total_verifications = len(self.verification_history)
        
        if total_verifications == 0:
            return {
                'total_verifications': 0,
                'supported_document_types': len(self.document_types),
                'current_verification_status': self.account_verifications['current_status']
            }
        
        # Success Rate
        successful_verifications = sum(1 for v in self.verification_history if v['verification_successful'])
        success_rate = round((successful_verifications / total_verifications) * 100, 1)
        
        # Verification Type Distribution
        type_distribution = {}
        for verification in self.verification_history:
            v_type = verification['verification_type']
            type_distribution[v_type] = type_distribution.get(v_type, 0) + 1
        
        # Level Distribution
        level_distribution = {}
        for verification in self.verification_history:
            level = verification['verification_level']
            level_distribution[level] = level_distribution.get(level, 0) + 1
        
        # Average Verification Score
        scores = [v['verification_score'] for v in self.verification_history]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Recent Activity
        recent_verifications = [
            v for v in self.verification_history
            if (datetime.now() - v['timestamp']).seconds < 86400  # Last 24 hours
        ]
        
        return {
            'total_verifications': total_verifications,
            'successful_verifications': successful_verifications,
            'success_rate_percent': success_rate,
            'recent_verifications_24h': len(recent_verifications),
            'verification_type_distribution': dict(sorted(
                type_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'verification_level_distribution': dict(sorted(
                level_distribution.items(), key=lambda x: x[1], reverse=True
            )),
            'average_verification_score': avg_score,
            'current_verification_level': self.account_verifications['verification_level'],
            'documents_on_file': len(self.uploaded_documents),
            'average_processing_time': self.average_execution_time
        }

    async def _setup_event_subscriptions(self):
        """Setup Event-Bus Subscriptions"""
        try:
            # Subscribe to relevant events for this module
            await self.event_bus.subscribe('system.health.request', self.process_event)
            await self.event_bus.subscribe(f'{self.module_name}.request', self.process_event)
            
            self.logger.info("Event subscriptions setup completed", 
                           module=self.module_name)
        except Exception as e:
            self.logger.error("Failed to setup event subscriptions",
                            error=str(e), module=self.module_name)
    
    async def process_event(self, event):
        """Process incoming events"""
        try:
            event_type = event.get('event_type', '')
            
            if event_type == 'system.health.request':
                # Health check response
                health_response = {
                    'event_type': 'system.health.response',
                    'stream_id': 'health-check',
                    'data': {
                        'module_name': self.module_name,
                        'status': 'healthy',
                        'execution_count': getattr(self, 'execution_history', []),
                        'average_execution_time_ms': self.average_execution_time,
                        'health_check_timestamp': datetime.now().isoformat()
                    },
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(health_response)
                
            elif event_type == f'{self.module_name}.request':
                # Module-specific request
                event_data = event.get('data', {})
                result = await self.execute_function(event_data)
                
                response_event = {
                    'event_type': f'{self.module_name}.response',
                    'stream_id': event.get('stream_id', f'{self.module_name}-request'),
                    'data': result,
                    'source': self.module_name,
                    'correlation_id': event.get('correlation_id')
                }
                await self.event_bus.publish(response_event)
            
            else:
                self.logger.debug("Unhandled event type", 
                                event_type=event_type, module=self.module_name)
                
        except Exception as e:
            self.logger.error("Failed to process event",
                            error=str(e), event=str(event), module=self.module_name)
