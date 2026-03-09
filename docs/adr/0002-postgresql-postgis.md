# ADR 0002: PostgreSQL 16 with PostGIS for Primary Database

**Status:** Accepted  
**Date:** January 2026  
**Deciders:** Engineering Team

## Context

LandRight requires a database that can:
1. Handle complex relational data (projects, parcels, parties, documents)
2. Support geospatial queries for parcel boundaries and alignments
3. Provide ACID compliance for legal document integrity
4. Scale to enterprise workloads
5. Integrate with modern ORMs (SQLAlchemy 2.0)

## Decision

Use **PostgreSQL 16** with the **PostGIS 3.4** extension as the primary database.

## Rationale

### Why PostgreSQL?

| Requirement | PostgreSQL Capability |
|-------------|----------------------|
| Relational data | Full SQL compliance, complex joins |
| Geospatial | PostGIS extension (industry standard) |
| ACID compliance | Full transactional support |
| Scalability | Proven at enterprise scale |
| ORM support | Excellent SQLAlchemy 2.0 integration |
| Cloud support | Cloud SQL (GCP) managed service |
| JSON support | JSONB for flexible schema fields |
| Full-text search | Built-in tsvector search |

### Why PostGIS?

- Industry standard for geospatial data
- Supports complex geometry operations (intersection, buffer, distance)
- GeoJSON import/export
- Compatible with Mapbox and ESRI tools
- Enables queries like "find all parcels within alignment corridor"

### Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **PostgreSQL + PostGIS** | Full SQL, geospatial, ACID, mature | More complex than NoSQL | **Selected** |
| MongoDB | Flexible schema, GeoJSON native | No ACID, weak joins | Rejected |
| MySQL | Widespread, simple | Weaker geospatial, less features | Rejected |
| SQL Server | Enterprise features | Cost, vendor lock-in | Rejected |
| CockroachDB | Distributed, PostgreSQL wire | Immature, cost | Rejected |

## Consequences

### Positive

- Robust geospatial support for parcel and alignment management
- Strong data integrity for legal documents
- Mature ecosystem with excellent tooling
- Cost-effective managed service on GCP
- Team familiarity with PostgreSQL

### Negative

- Requires PostGIS expertise for spatial queries
- More operational complexity than managed NoSQL
- Schema migrations required for model changes

### Mitigations

- Use Alembic for migration management
- Document spatial query patterns
- Cloud SQL handles operational complexity

## Implementation Notes

```python
# SQLAlchemy model with geometry
from geoalchemy2 import Geometry

class Parcel(Base):
    __tablename__ = "parcels"
    
    id = Column(UUID, primary_key=True)
    geometry = Column(Geometry("POLYGON", srid=4326))
    
# Spatial query example
from geoalchemy2.functions import ST_Contains

parcels_in_alignment = session.query(Parcel).filter(
    ST_Contains(alignment.geometry, Parcel.geometry)
).all()
```

## References

- [PostgreSQL 16 Release Notes](https://www.postgresql.org/docs/16/release-16.html)
- [PostGIS Documentation](https://postgis.net/docs/)
- [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)
