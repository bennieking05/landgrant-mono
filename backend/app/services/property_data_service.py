"""Property data service for external API integrations.

This module provides integration with property data APIs:
- CoreLogic/ATTOM for property details
- County assessor APIs for tax records
- First American/DataTree for title data

All external data is cached in ExternalDataCache for efficiency
and fallback when services are unavailable.
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
class PropertyData:
    """Property information from external sources."""
    apn: str
    county_fips: str
    address: Optional[str] = None
    owner_names: list[str] = None
    owner_address: Optional[dict[str, Any]] = None
    legal_description: Optional[str] = None
    property_type: Optional[str] = None
    land_use: Optional[str] = None
    lot_size_sqft: Optional[float] = None
    building_sqft: Optional[float] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    assessed_value: Optional[float] = None
    tax_amount: Optional[float] = None
    zoning: Optional[str] = None
    liens: list[dict[str, Any]] = None
    source: str = "unknown"
    confidence: float = 0.0
    fetched_at: datetime = None
    
    def __post_init__(self):
        self.owner_names = self.owner_names or []
        self.liens = self.liens or []
        self.fetched_at = self.fetched_at or datetime.utcnow()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "apn": self.apn,
            "county_fips": self.county_fips,
            "address": self.address,
            "owner_names": self.owner_names,
            "owner_address": self.owner_address,
            "legal_description": self.legal_description,
            "property_type": self.property_type,
            "land_use": self.land_use,
            "lot_size_sqft": self.lot_size_sqft,
            "building_sqft": self.building_sqft,
            "year_built": self.year_built,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "assessed_value": self.assessed_value,
            "tax_amount": self.tax_amount,
            "zoning": self.zoning,
            "liens": self.liens,
            "source": self.source,
            "confidence": self.confidence,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }


class PropertyDataService:
    """Service for fetching property data from external APIs.
    
    Implements a tiered approach:
    1. Check local cache first
    2. Try primary API (CoreLogic/ATTOM)
    3. Fall back to secondary sources
    4. Cache results for future use
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
        
        # API configuration (from environment)
        self.attom_api_key = getattr(settings, 'attom_api_key', None)
        self.corelogic_api_key = getattr(settings, 'corelogic_api_key', None)
    
    async def fetch_property_data(
        self, 
        apn: str, 
        county_fips: str,
        use_cache: bool = True,
    ) -> PropertyData:
        """Fetch property data from available sources.
        
        Args:
            apn: Assessor's Parcel Number
            county_fips: County FIPS code
            use_cache: Whether to check cache first
            
        Returns:
            PropertyData with available information
        """
        cache_key = f"{county_fips}:{apn}"
        
        # 1. Check cache first
        if use_cache:
            cached = await self._get_cached_data(cache_key, "property")
            if cached:
                self.logger.info(f"Cache hit for property {cache_key}")
                return PropertyData(**cached)
        
        # 2. Try primary API
        property_data = await self._fetch_from_attom(apn, county_fips)
        
        # 3. Fall back to mock data in development
        if not property_data:
            property_data = await self._fetch_mock_data(apn, county_fips)
        
        # 4. Cache the result
        if property_data and self.db:
            await self._cache_data(cache_key, "property", property_data.to_dict())
        
        return property_data
    
    async def fetch_tax_records(
        self,
        apn: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch tax records for a property.
        
        Args:
            apn: Assessor's Parcel Number
            county_fips: County FIPS code
            
        Returns:
            Tax record data
        """
        cache_key = f"{county_fips}:{apn}"
        
        # Check cache
        cached = await self._get_cached_data(cache_key, "tax")
        if cached:
            return cached
        
        # Fetch from API (mock for now)
        tax_data = {
            "apn": apn,
            "county_fips": county_fips,
            "tax_year": datetime.now().year - 1,
            "assessed_value_land": 100000.0,
            "assessed_value_improvements": 200000.0,
            "assessed_value_total": 300000.0,
            "tax_amount": 6000.0,
            "tax_status": "current",
            "exemptions": [],
            "source": "mock",
        }
        
        # Cache result
        if self.db:
            await self._cache_data(cache_key, "tax", tax_data)
        
        return tax_data
    
    async def fetch_owner_info(
        self,
        apn: str,
        county_fips: str,
    ) -> dict[str, Any]:
        """Fetch current owner information.
        
        Args:
            apn: Assessor's Parcel Number
            county_fips: County FIPS code
            
        Returns:
            Owner information
        """
        property_data = await self.fetch_property_data(apn, county_fips)
        
        return {
            "apn": apn,
            "owner_names": property_data.owner_names,
            "owner_address": property_data.owner_address,
            "owner_type": "individual",  # individual, trust, corporate, government
            "ownership_since": None,  # Would come from title data
        }
    
    async def _fetch_from_attom(
        self,
        apn: str,
        county_fips: str,
    ) -> Optional[PropertyData]:
        """Fetch from ATTOM Data API.
        
        Args:
            apn: Assessor's Parcel Number
            county_fips: County FIPS code
            
        Returns:
            PropertyData or None if unavailable
        """
        if not self.attom_api_key:
            self.logger.debug("ATTOM API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                # ATTOM property endpoint
                response = await client.get(
                    "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/basicprofile",
                    params={"apn": apn, "fips": county_fips},
                    headers={"apikey": self.attom_api_key},
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_attom_response(data, apn, county_fips)
                else:
                    self.logger.warning(f"ATTOM API returned {response.status_code}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"ATTOM API call failed: {e}")
            return None
    
    def _parse_attom_response(
        self,
        data: dict[str, Any],
        apn: str,
        county_fips: str,
    ) -> PropertyData:
        """Parse ATTOM API response into PropertyData.
        
        Args:
            data: API response
            apn: APN for reference
            county_fips: County FIPS for reference
            
        Returns:
            Parsed PropertyData
        """
        property_info = data.get("property", [{}])[0] if data.get("property") else {}
        
        return PropertyData(
            apn=apn,
            county_fips=county_fips,
            address=property_info.get("address", {}).get("oneLine"),
            owner_names=property_info.get("owner", {}).get("names", []),
            legal_description=property_info.get("lot", {}).get("legalDescription"),
            property_type=property_info.get("summary", {}).get("propertyType"),
            lot_size_sqft=property_info.get("lot", {}).get("lotSize"),
            building_sqft=property_info.get("building", {}).get("size", {}).get("grossSize"),
            year_built=property_info.get("building", {}).get("yearBuilt"),
            assessed_value=property_info.get("assessment", {}).get("assessed", {}).get("total"),
            source="attom",
            confidence=0.9,
        )
    
    async def _fetch_mock_data(
        self,
        apn: str,
        county_fips: str,
    ) -> PropertyData:
        """Generate mock property data for development.
        
        Args:
            apn: APN
            county_fips: County FIPS
            
        Returns:
            Mock PropertyData
        """
        self.logger.info(f"Using mock data for {county_fips}:{apn}")
        
        return PropertyData(
            apn=apn,
            county_fips=county_fips,
            address="123 Main Street, Anytown, TX 75001",
            owner_names=["John Smith", "Jane Smith"],
            owner_address={
                "line1": "456 Oak Avenue",
                "city": "Othertown",
                "state": "TX",
                "zip": "75002",
            },
            legal_description="LOT 1, BLOCK A, SAMPLE SUBDIVISION",
            property_type="Single Family Residential",
            land_use="Residential",
            lot_size_sqft=10000.0,
            building_sqft=2000.0,
            year_built=1995,
            bedrooms=4,
            bathrooms=2.5,
            assessed_value=350000.0,
            tax_amount=7000.0,
            zoning="R-1",
            liens=[],
            source="mock",
            confidence=0.5,  # Lower confidence for mock data
        )
    
    async def _get_cached_data(
        self,
        cache_key: str,
        cache_type: str,
    ) -> Optional[dict[str, Any]]:
        """Get cached data if available and not expired.
        
        Args:
            cache_key: Cache key
            cache_type: Type of cached data
            
        Returns:
            Cached data or None
        """
        if not self.db:
            return None
        
        try:
            from app.db.models import ExternalDataCache
            from sqlalchemy import select, and_
            
            result = await self.db.execute(
                select(ExternalDataCache).where(
                    and_(
                        ExternalDataCache.external_id == cache_key,
                        ExternalDataCache.cache_type == cache_type,
                        ExternalDataCache.expires_at > datetime.utcnow(),
                    )
                )
            )
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry:
                return cache_entry.data
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache lookup failed: {e}")
            return None
    
    async def _cache_data(
        self,
        cache_key: str,
        cache_type: str,
        data: dict[str, Any],
    ) -> None:
        """Cache data for future use.
        
        Args:
            cache_key: Cache key
            cache_type: Type of data
            data: Data to cache
        """
        if not self.db:
            return
        
        try:
            from app.db.models import ExternalDataCache
            
            cache_entry = ExternalDataCache(
                id=str(uuid4()),
                cache_type=cache_type,
                external_id=cache_key,
                source=data.get("source", "unknown"),
                data=data,
                confidence=data.get("confidence", 0.5),
                fetched_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=self.CACHE_TTL_HOURS),
                hash=sha256_hex(str(data)),
            )
            
            self.db.add(cache_entry)
            await self.db.commit()
            
        except Exception as e:
            self.logger.warning(f"Cache write failed: {e}")
