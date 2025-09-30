# PostgreSQL HA Module

This module provisions a highly available PostgreSQL cluster with automated backups, PITR configuration, and secrets integration.  The module defaults to managed offerings (Aurora PostgreSQL, Cloud SQL, Azure Database for PostgreSQL Flexible Server) but can also be pointed at self-managed operators inside Kubernetes.

Outputs expose connection strings, replica endpoints, and backup bucket names so application manifests can request credentials from the centralized secrets manager.
