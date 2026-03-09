# Backup & Restore Drill

1. Trigger Cloud SQL PITR restore into temporary instance.
2. Run migration scripts to ensure schema integrity.
3. Restore GCS evidence objects using version numbers recorded in binder metadata.
4. Verify ability to rebuild binder from restored data.
5. Document duration, blockers, and update RPO/RTO metrics.
