#!/usr/bin/env python3
"""
Database Field Standardization Migration Script

This script standardizes all field names in the database to use consistent snake_case naming.
It handles the migration from mixed camelCase/snake_case to pure snake_case format.

CRITICAL: This script modifies production data. Always backup before running.

Usage:
    python3 standardize_database_fields.py --dry-run    # Preview changes
    python3 standardize_database_fields.py --execute   # Execute migration
"""

import boto3
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseFieldStandardizer:
    """Handles standardization of database field names to snake_case"""

    def __init__(self, dry_run: bool = True):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        self.people_table_name = "PeopleTable"
        self.dry_run = dry_run

        # Field mapping from camelCase to snake_case
        self.field_mappings = {
            # Core fields
            "firstName": "first_name",
            "lastName": "last_name",
            "dateOfBirth": "date_of_birth",
            "isAdmin": "is_admin",
            "isActive": "is_active",
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            # Authentication fields - CRITICAL
            "passwordHash": "password_hash",
            "passwordSalt": "password_salt",
            "lastPasswordChange": "last_password_change",
            "requirePasswordChange": "require_password_change",
            "failedLoginAttempts": "failed_login_attempts",
            "accountLockedUntil": "account_locked_until",
            "lastLoginAt": "last_login_at",
            "emailVerified": "email_verified",
        }

        # Fields to remove (duplicates that should be consolidated)
        self.fields_to_remove = [
            "passwordHash",  # Remove camelCase version, keep password_hash
            "passwordSalt",  # Remove camelCase version, keep password_salt
        ]

        self.migration_stats = {
            "records_processed": 0,
            "records_updated": 0,
            "fields_migrated": 0,
            "errors": 0,
            "warnings": 0,
        }

    def backup_table_data(self) -> str:
        """Create a backup of the table data before migration"""
        logger.info("Creating backup of table data...")

        try:
            table = self.dynamodb.Table(self.people_table_name)
            response = table.scan()

            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "table_name": self.people_table_name,
                "items": response.get("Items", []),
            }

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                backup_data["items"].extend(response.get("Items", []))

            backup_filename = f"people_table_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

            with open(backup_filename, "w") as f:
                json.dump(backup_data, f, indent=2, default=str)

            logger.info(
                f"Backup created: {backup_filename} ({len(backup_data['items'])} records)"
            )
            return backup_filename

        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            raise

    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current database state to understand field usage"""
        logger.info("Analyzing current database state...")

        try:
            table = self.dynamodb.Table(self.people_table_name)
            response = table.scan()

            field_usage = {}
            duplicate_fields = {}
            records_analyzed = 0

            for item in response.get("Items", []):
                records_analyzed += 1

                # Track field usage
                for field_name in item.keys():
                    if field_name not in field_usage:
                        field_usage[field_name] = 0
                    field_usage[field_name] += 1

                # Check for duplicate field patterns
                for camel_field, snake_field in self.field_mappings.items():
                    if camel_field in item and snake_field in item:
                        key = f"{camel_field}+{snake_field}"
                        if key not in duplicate_fields:
                            duplicate_fields[key] = 0
                        duplicate_fields[key] += 1

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                for item in response.get("Items", []):
                    records_analyzed += 1

                    for field_name in item.keys():
                        if field_name not in field_usage:
                            field_usage[field_name] = 0
                        field_usage[field_name] += 1

                    for camel_field, snake_field in self.field_mappings.items():
                        if camel_field in item and snake_field in item:
                            key = f"{camel_field}+{snake_field}"
                            if key not in duplicate_fields:
                                duplicate_fields[key] = 0
                            duplicate_fields[key] += 1

            analysis = {
                "records_analyzed": records_analyzed,
                "field_usage": field_usage,
                "duplicate_fields": duplicate_fields,
                "fields_needing_migration": [],
            }

            # Identify fields that need migration
            for camel_field, snake_field in self.field_mappings.items():
                camel_count = field_usage.get(camel_field, 0)
                snake_count = field_usage.get(snake_field, 0)

                if camel_count > 0:
                    analysis["fields_needing_migration"].append(
                        {
                            "camel_field": camel_field,
                            "snake_field": snake_field,
                            "camel_count": camel_count,
                            "snake_count": snake_count,
                            "has_duplicates": snake_count > 0,
                        }
                    )

            logger.info(
                f"Analysis complete: {records_analyzed} records, {len(field_usage)} unique fields"
            )
            logger.info(
                f"Fields needing migration: {len(analysis['fields_needing_migration'])}"
            )

            if duplicate_fields:
                logger.warning(f"Duplicate field patterns found: {duplicate_fields}")
                self.migration_stats["warnings"] += len(duplicate_fields)

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze current state: {str(e)}")
            raise

    def migrate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a single record to standardized field names"""
        migrated_record = record.copy()
        fields_changed = []

        # Migrate camelCase fields to snake_case
        for camel_field, snake_field in self.field_mappings.items():
            if camel_field in migrated_record:
                # If snake_case version doesn't exist, migrate
                if snake_field not in migrated_record:
                    migrated_record[snake_field] = migrated_record[camel_field]
                    fields_changed.append(f"{camel_field} -> {snake_field}")
                else:
                    # Both exist - need to decide which to keep
                    logger.warning(
                        f"Both {camel_field} and {snake_field} exist in record {record.get('id', 'unknown')}"
                    )
                    # Keep snake_case version, log the conflict
                    fields_changed.append(
                        f"{camel_field} (conflict with {snake_field})"
                    )

                # Remove camelCase version if it's in the removal list
                if camel_field in self.fields_to_remove:
                    del migrated_record[camel_field]
                    fields_changed.append(f"removed {camel_field}")

        # Update the updatedAt timestamp
        migrated_record["updated_at"] = datetime.utcnow().isoformat()

        if fields_changed:
            logger.debug(
                f"Record {record.get('id', 'unknown')}: {', '.join(fields_changed)}"
            )
            self.migration_stats["fields_migrated"] += len(fields_changed)

        return migrated_record

    def execute_migration(self, analysis: Dict[str, Any]) -> None:
        """Execute the field standardization migration"""
        logger.info(
            f"{'DRY RUN: ' if self.dry_run else ''}Starting field standardization migration..."
        )

        try:
            table = self.dynamodb.Table(self.people_table_name)
            response = table.scan()

            # Process all records
            all_items = response.get("Items", [])

            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                all_items.extend(response.get("Items", []))

            logger.info(f"Processing {len(all_items)} records...")

            for item in all_items:
                try:
                    self.migration_stats["records_processed"] += 1

                    # Migrate the record
                    migrated_item = self.migrate_record(item)

                    # Check if any changes were made
                    if migrated_item != item:
                        if not self.dry_run:
                            # Update the record in DynamoDB
                            table.put_item(Item=migrated_item)

                        self.migration_stats["records_updated"] += 1

                        if self.migration_stats["records_updated"] % 10 == 0:
                            logger.info(
                                f"Processed {self.migration_stats['records_updated']} records..."
                            )

                except Exception as e:
                    logger.error(
                        f"Error processing record {item.get('id', 'unknown')}: {str(e)}"
                    )
                    self.migration_stats["errors"] += 1

            logger.info(f"{'DRY RUN: ' if self.dry_run else ''}Migration completed!")

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise

    def generate_migration_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a detailed migration report"""
        report = {
            "migration_timestamp": datetime.utcnow().isoformat(),
            "dry_run": self.dry_run,
            "pre_migration_analysis": analysis,
            "migration_statistics": self.migration_stats,
            "field_mappings_applied": self.field_mappings,
            "fields_removed": self.fields_to_remove,
        }

        report_filename = f"field_standardization_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_filename, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Migration report saved: {report_filename}")
        return report_filename

    def run_standardization(self) -> None:
        """Run the complete field standardization process"""
        logger.info("=" * 60)
        logger.info("DATABASE FIELD STANDARDIZATION")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}")
        logger.info(f"Table: {self.people_table_name}")

        try:
            # Step 1: Create backup (only in execution mode)
            backup_file = None
            if not self.dry_run:
                backup_file = self.backup_table_data()

            # Step 2: Analyze current state
            analysis = self.analyze_current_state()

            # Step 3: Execute migration
            self.execute_migration(analysis)

            # Step 4: Generate report
            report_file = self.generate_migration_report(analysis)

            # Step 5: Summary
            logger.info("=" * 60)
            logger.info("MIGRATION SUMMARY")
            logger.info("=" * 60)
            logger.info(
                f"Records processed: {self.migration_stats['records_processed']}"
            )
            logger.info(f"Records updated: {self.migration_stats['records_updated']}")
            logger.info(f"Fields migrated: {self.migration_stats['fields_migrated']}")
            logger.info(f"Errors: {self.migration_stats['errors']}")
            logger.info(f"Warnings: {self.migration_stats['warnings']}")

            if backup_file:
                logger.info(f"Backup file: {backup_file}")
            logger.info(f"Report file: {report_file}")

            if self.migration_stats["errors"] > 0:
                logger.warning(
                    "Migration completed with errors. Please review the report."
                )
            else:
                logger.info("Migration completed successfully!")

        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Standardize database field names to snake_case"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without executing them"
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute the migration (modifies data)"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Error: Must specify either --dry-run or --execute")
        parser.print_help()
        return 1

    if args.execute:
        response = input(
            "WARNING: This will modify production data. Are you sure? (yes/no): "
        )
        if response.lower() != "yes":
            print("Migration cancelled.")
            return 0

    try:
        standardizer = DatabaseFieldStandardizer(dry_run=args.dry_run)
        standardizer.run_standardization()
        return 0

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
