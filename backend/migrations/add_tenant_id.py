"""
Multi-tenant Migration: Add tenant_id to all tables

This script adds tenant_id columns to existing tables and sets up indexes
for multi-tenant data isolation.

Default tenant_id = 0 for development environment.
Production tenants use tenant_id > 0.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import Column, Integer, Index, text
from backend.database import get_database
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def migrate_add_tenant_id():
    """Add tenant_id column to all tables"""
    db = get_database()
    
    logger.info("Starting multi-tenant migration...")
    
    with db.engine.begin() as conn:
        # Tables to migrate
        tables = [
            'database_configs',    # Data sources
            'saved_reports',       # Generated reports
            'sessions',            # User sessions
            'session_interactions', # Chat history
            'report_snapshots',    # Report versions
            'mcp_server_configs',  # MCP server configs
            'sensitive_rules',     # Sensitive data rules
        ]
        
        for table in tables:
            try:
                # Check if table exists
                result = conn.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ))
                if not result.fetchone():
                    logger.warning(f"Table {table} does not exist, skipping")
                    continue
                
                # Check if tenant_id column already exists
                result = conn.execute(text(f"PRAGMA table_info({table})"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'tenant_id' in columns:
                    logger.info(f"✓ {table}: tenant_id already exists")
                else:
                    # Add tenant_id column with default value 0
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER DEFAULT 0 NOT NULL"
                    ))
                    logger.info(f"✓ {table}: Added tenant_id column")
                
                # Create index on tenant_id for performance
                index_name = f"idx_{table}_tenant_id"
                try:
                    conn.execute(text(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}(tenant_id)"
                    ))
                    logger.info(f"✓ {table}: Created index on tenant_id")
                except Exception as e:
                    logger.warning(f"Index creation warning for {table}: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to migrate {table}: {e}")
                raise
    
    logger.info("✅ Multi-tenant migration completed successfully!")
    logger.info("All existing data has been assigned tenant_id = 0 (development)")
    

def verify_migration():
    """Verify that migration was successful"""
    db = get_database()
    
    logger.info("\nVerifying migration...")
    
    with db.engine.begin() as conn:
        tables = [
            'database_configs',
            'saved_reports',
            'sessions',
        ]
        
        for table in tables:
            try:
                result = conn.execute(text(f"PRAGMA table_info({table})"))
                columns = {row[1]: row[2] for row in result.fetchall()}
                
                if 'tenant_id' in columns:
                    # Count records by tenant_id
                    result = conn.execute(text(
                        f"SELECT tenant_id, COUNT(*) as count FROM {table} GROUP BY tenant_id"
                    ))
                    counts = result.fetchall()
                    
                    if counts:
                        logger.info(f"✓ {table}:")
                        for tenant_id, count in counts:
                            logger.info(f"    tenant_id={tenant_id}: {count} records")
                    else:
                        logger.info(f"✓ {table}: No records (empty table)")
                else:
                    logger.error(f"❌ {table}: tenant_id column missing!")
                    
            except Exception as e:
                logger.error(f"❌ Verification failed for {table}: {e}")
    
    logger.info("\n✅ Verification complete!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Add tenant_id to tables')
    parser.add_argument('--no-interactive', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    print("=" * 60)
    print("Multi-tenant Database Migration")
    print("=" * 60)
    print("\nThis will add tenant_id columns to all tables.")
    print("Existing data will be assigned tenant_id = 0 (development)")
    
    if not args.no_interactive:
        print("\nPress Enter to continue, Ctrl+C to cancel...")
        try:
            input()
        except KeyboardInterrupt:
            print("\n❌ Migration cancelled")
            sys.exit(0)
    
    try:
        migrate_add_tenant_id()
        verify_migration()
        print("\n🎉 Migration successful!")
        print("You can now run Text2Dash in multi-tenant mode.")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)
