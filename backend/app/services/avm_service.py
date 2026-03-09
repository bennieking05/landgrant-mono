"""Automated Valuation Model (AVM) service for property valuations.

This module provides integration with AVM APIs:
- Zillow Zestimate API
- HouseCanary AVM
- CoreLogic AVM

Used by ValuationAgent to cross-check appraisals and estimate values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4
import httpx

from app.core.config import get_settings
from app.services.hashing import sha256_hex

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AVMResult:
    """Result from an AVM provider."""
    provider: str
    value: float
    low_estimate: float
    high_estimate: float
    confidence: float  # 0.0-1.0
    as_of_date: datetime
    value_change_30d: Optional[float] = None
    value_change_1y: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "value": self.value,
            "low_estimate": self.low_estimate,
            "high_estimate": self.high_estimate,
            "confidence": self.confidence,
            "as_of_date": self.as_of_date.isoformat(),
            "value_change_30d": self.value_change_30d,
            "value_change_1y": self.value_change_1y,
        }


@dataclass 
class CombinedAVMResult:
    """Combined results from multiple AVM providers."""
    estimates: list[AVMResult]
    consensus_value: float
    consensus_low: float
    consensus_high: float
    overall_confidence: float
    discrepancy_percent: float  # Max spread between estimates
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "estimates": [e.to_dict() for e in self.estimates],
            "consensus_value": self.consensus_value,
            "consensus_low": self.consensus_low,
            "consensus_high": self.consensus_high,
            "overall_confidence": self.overall_confidence,
            "discrepancy_percent": self.discrepancy_percent,
        }


class AVMService:
    """Service for fetching automated property valuations.
    
    Aggregates estimates from multiple providers and calculates
    consensus values with confidence scoring.
    """
    
    # Cache TTL in hours
    CACHE_TTL_HOURS = 168  # 7 days
    
    def __init__(self, db_session=None):
        """Initialize service.
        
        Args:
            db_session: Database session for caching
        """
        self.db = db_session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # API keys (from environment)
        self.zillow_api_key = getattr(settings, 'zillow_api_key', None)
        self.housecanary_api_key = getattr(settings, 'housecanary_api_key', None)
    
    async def get_combined_estimates(
        self,
        address: str,
        parcel_id: str = None,
        use_cache: bool = True,
    ) -> CombinedAVMResult:
        """Get combined AVM estimates from multiple providers.
        
        Args:
            address: Property address
            parcel_id: Optional parcel ID for caching
            use_cache: Whether to check cache first
            
        Returns:
            CombinedAVMResult with aggregated estimates
        """
        cache_key = f"avm:{sha256_hex(address)[:16]}"
        
        # Check cache
        if use_cache and parcel_id:
            cached = await self._get_cached_data(cache_key)
            if cached:
                self.logger.info(f"AVM cache hit for {cache_key}")
                return self._parse_cached_result(cached)
        
        # Fetch from providers in parallel
        estimates = []
        
        # Try each provider
        zillow_result = await self._fetch_zillow(address)
        if zillow_result:
            estimates.append(zillow_result)
        
        housecanary_result = await self._fetch_housecanary(address)
        if housecanary_result:
            estimates.append(housecanary_result)
        
        # Fall back to mock data if no real providers
        if not estimates:
            estimates = [await self._get_mock_estimate(address)]
        
        # Calculate consensus
        result = self._calculate_consensus(estimates)
        
        # Cache result
        if self.db and parcel_id:
            await self._cache_data(cache_key, parcel_id, result.to_dict())
        
        return result
    
    async def get_single_estimate(
        self,
        address: str,
        provider: str = "zillow",
    ) -> Optional[AVMResult]:
        """Get estimate from a single provider.
        
        Args:
            address: Property address
            provider: Provider name (zillow, housecanary)
            
        Returns:
            AVMResult or None
        """
        if provider == "zillow":
            return await self._fetch_zillow(address)
        elif provider == "housecanary":
            return await self._fetch_housecanary(address)
        else:
            return None
    
    async def _fetch_zillow(self, address: str) -> Optional[AVMResult]:
        """Fetch Zillow Zestimate.
        
        Args:
            address: Property address
            
        Returns:
            AVMResult or None
        """
        if not self.zillow_api_key:
            self.logger.debug("Zillow API not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                # This is a simplified example - actual API differs
                response = await client.get(
                    "https://api.zillow.com/v1/zestimate",
                    params={"address": address},
                    headers={"Authorization": f"Bearer {self.zillow_api_key}"},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return AVMResult(
                        provider="zillow",
                        value=float(data.get("zestimate", 0)),
                        low_estimate=float(data.get("low", 0)),
                        high_estimate=float(data.get("high", 0)),
                        confidence=0.85,  # Zillow doesn't provide this
                        as_of_date=datetime.utcnow(),
                    )
                    
        except Exception as e:
            self.logger.error(f"Zillow API call failed: {e}")
        
        return None
    
    async def _fetch_housecanary(self, address: str) -> Optional[AVMResult]:
        """Fetch HouseCanary AVM.
        
        Args:
            address: Property address
            
        Returns:
            AVMResult or None
        """
        if not self.housecanary_api_key:
            self.logger.debug("HouseCanary API not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.housecanary.com/v2/property/value",
                    params={"address": address},
                    headers={"Authorization": f"Bearer {self.housecanary_api_key}"},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    value_data = data.get("property/value", {})
                    return AVMResult(
                        provider="housecanary",
                        value=float(value_data.get("value", 0)),
                        low_estimate=float(value_data.get("value_low", 0)),
                        high_estimate=float(value_data.get("value_high", 0)),
                        confidence=float(value_data.get("fsd", 0.8)),
                        as_of_date=datetime.utcnow(),
                    )
                    
        except Exception as e:
            self.logger.error(f"HouseCanary API call failed: {e}")
        
        return None
    
    async def _get_mock_estimate(self, address: str) -> AVMResult:
        """Generate mock AVM estimate for development.
        
        Args:
            address: Property address
            
        Returns:
            Mock AVMResult
        """
        import hashlib
        
        # Generate consistent mock value based on address
        address_hash = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
        base_value = 200000 + (address_hash % 800000)  # $200k-$1M range
        
        return AVMResult(
            provider="mock",
            value=float(base_value),
            low_estimate=float(base_value * 0.9),
            high_estimate=float(base_value * 1.1),
            confidence=0.6,  # Lower confidence for mock
            as_of_date=datetime.utcnow(),
        )
    
    def _calculate_consensus(self, estimates: list[AVMResult]) -> CombinedAVMResult:
        """Calculate consensus from multiple estimates.
        
        Args:
            estimates: List of AVM estimates
            
        Returns:
            CombinedAVMResult with consensus values
        """
        if not estimates:
            return CombinedAVMResult(
                estimates=[],
                consensus_value=0,
                consensus_low=0,
                consensus_high=0,
                overall_confidence=0,
                discrepancy_percent=0,
            )
        
        # Weight by confidence
        total_weight = sum(e.confidence for e in estimates)
        
        if total_weight == 0:
            # Fallback to simple average
            consensus_value = sum(e.value for e in estimates) / len(estimates)
            consensus_low = sum(e.low_estimate for e in estimates) / len(estimates)
            consensus_high = sum(e.high_estimate for e in estimates) / len(estimates)
            overall_confidence = 0.5
        else:
            consensus_value = sum(e.value * e.confidence for e in estimates) / total_weight
            consensus_low = sum(e.low_estimate * e.confidence for e in estimates) / total_weight
            consensus_high = sum(e.high_estimate * e.confidence for e in estimates) / total_weight
            overall_confidence = sum(e.confidence for e in estimates) / len(estimates)
        
        # Calculate discrepancy (max spread)
        if len(estimates) > 1:
            values = [e.value for e in estimates]
            discrepancy = (max(values) - min(values)) / consensus_value * 100 if consensus_value else 0
        else:
            discrepancy = (consensus_high - consensus_low) / consensus_value * 100 if consensus_value else 0
        
        return CombinedAVMResult(
            estimates=estimates,
            consensus_value=consensus_value,
            consensus_low=consensus_low,
            consensus_high=consensus_high,
            overall_confidence=overall_confidence,
            discrepancy_percent=discrepancy,
        )
    
    async def _get_cached_data(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Get cached AVM data if available."""
        if not self.db:
            return None
        
        try:
            from app.db.models import ExternalDataCache
            from sqlalchemy import select, and_
            
            result = await self.db.execute(
                select(ExternalDataCache).where(
                    and_(
                        ExternalDataCache.external_id == cache_key,
                        ExternalDataCache.cache_type == "avm",
                        ExternalDataCache.expires_at > datetime.utcnow(),
                    )
                )
            )
            cache_entry = result.scalar_one_or_none()
            
            return cache_entry.data if cache_entry else None
            
        except Exception as e:
            self.logger.warning(f"Cache lookup failed: {e}")
            return None
    
    async def _cache_data(
        self,
        cache_key: str,
        parcel_id: str,
        data: dict[str, Any],
    ) -> None:
        """Cache AVM data."""
        if not self.db:
            return
        
        try:
            from app.db.models import ExternalDataCache
            
            cache_entry = ExternalDataCache(
                id=str(uuid4()),
                cache_type="avm",
                parcel_id=parcel_id,
                external_id=cache_key,
                source="combined",
                data=data,
                confidence=data.get("overall_confidence", 0.5),
                fetched_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=self.CACHE_TTL_HOURS),
                hash=sha256_hex(str(data)),
            )
            
            self.db.add(cache_entry)
            await self.db.commit()
            
        except Exception as e:
            self.logger.warning(f"Cache write failed: {e}")
    
    def _parse_cached_result(self, cached: dict[str, Any]) -> CombinedAVMResult:
        """Parse cached data back into CombinedAVMResult."""
        estimates = []
        for e in cached.get("estimates", []):
            estimates.append(AVMResult(
                provider=e["provider"],
                value=e["value"],
                low_estimate=e["low_estimate"],
                high_estimate=e["high_estimate"],
                confidence=e["confidence"],
                as_of_date=datetime.fromisoformat(e["as_of_date"]),
            ))
        
        return CombinedAVMResult(
            estimates=estimates,
            consensus_value=cached["consensus_value"],
            consensus_low=cached["consensus_low"],
            consensus_high=cached["consensus_high"],
            overall_confidence=cached["overall_confidence"],
            discrepancy_percent=cached["discrepancy_percent"],
        )
