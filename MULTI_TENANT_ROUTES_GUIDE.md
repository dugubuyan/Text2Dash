# Text2Dash Multi-tenant Routes Update Guide

## Overview
This guide explains how to update text2dash routes to support multi-tenant data isolation.

## Pattern to Follow

### 1. Import tenant helpers
```python
from fastapi import APIRouter, Request  # Add Request
from backend.utils.tenant_helpers import get_tenant_id
```

### 2. Add tenant_id on CREATE operations

**Before**:
```python
@router.post("", response_model=DatabaseResponse)
async def create_database_config(request: CreateDatabaseRequest):
    db_config = DatabaseConfig(
        id=config_id,
        name=request.name,
        type=request.type,
        # ... other fields
    )
```

**After**:
```python
@router.post("", response_model=DatabaseResponse)
async def create_database_config(req: Request, request: CreateDatabaseRequest):
    tenant_id = get_tenant_id(req)
    
    db_config = DatabaseConfig(
        id=config_id,
        tenant_id=tenant_id,  # Add this
        name=request.name,
        type=request.type,
        # ... other fields
    )
```

### 3. Add tenant_id filter on READ operations

**Before**:
```python
@router.get("", response_model=List[DatabaseResponse])
async def get_database_configs():
    with db.get_session() as session:
        configs = session.query(DatabaseConfig).all()
```

**After**:
```python
@router.get("", response_model=List[DatabaseResponse])
async def get_database_configs(req: Request):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        configs = session.query(DatabaseConfig).filter(
            DatabaseConfig.tenant_id == tenant_id  # Add filter
        ).all()
```

### 4. Add tenant_id filter on UPDATE/DELETE operations

**Before**:
```python
@router.delete("/{config_id}")
async def delete_database_config(config_id: str):
    with db.get_session() as session:
        config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id
        ).first()
```

**After**:
```python
@router.delete("/{config_id}")
async def delete_database_config(req: Request, config_id: str):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.tenant_id == tenant_id  # Add filter
        ).first()
```

## Files to Update

### High Priority (Data Isolation Critical)
1. **`routes/databases.py`** - Database configurations
   - List databases: Add tenant filter
   - Create database: Add tenant_id
   - Get/Update/Delete database: Add tenant filter

2. **`routes/reports.py`** - Generated reports
   - Create report: Add tenant_id
   - List reports: Add tenant filter
   - Get/Delete report: Add tenant filter

3. **`routes/sessions.py`** - User sessions
   - Create session: Add tenant_id
   - List sessions: Add tenant filter
   - Get/Update/Delete session: Add tenant filter

### Medium Priority
4. **`routes/mcp_servers.py`** - MCP server configurations
5. **`routes/sensitive_rules.py`** - Sensitive data rules

### Low Priority (System-wide, no tenant isolation needed)
- `routes/models.py` - LLM model list (system-wide)
- `routes/export.py` - Export operations (uses existing tenant-filtered data)
- `routes/cache.py` - Cache operations (system-wide)

## Testing Checklist

After updating each route file:

1. **Development Mode Test** (tenant_id=0):
   ```bash
   # Direct access without gateway
   curl http://localhost:8000/api/databases
   # Should work, returns data with tenant_id=0
   ```

2. **Production Mode Test** (with gateway):
   ```bash
   # Via gateway with JWT token
   curl -H "Authorization: Bearer <TOKEN>" http://localhost:3001/api/databases
   # Should return only tenant's data
   ```

3. **Multi-tenant Isolation Test**:
   - Create data as tenant A
   - Login as tenant B
   - Verify tenant B cannot see tenant A's data

## Example: Complete databases.py Update

Key changes for `routes/databases.py`:

```python
# At top of file
from fastapi import APIRouter, Request
from backend.utils.tenant_helpers import get_tenant_id

# CREATE - Line ~67
@router.post("", response_model=DatabaseResponse)
async def create_database_config(req: Request, request: CreateDatabaseRequest):
    tenant_id = get_tenant_id(req)
    
    db_config = DatabaseConfig(
        id=config_id,
        tenant_id=tenant_id,  # NEW
        name=request.name,
        # ...
    )

# LIST - Line ~128
@router.get("", response_model=List[DatabaseResponse])
async def get_database_configs(req: Request):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        configs = session.query(DatabaseConfig).filter(
            DatabaseConfig.tenant_id == tenant_id  # NEW
        ).order_by(DatabaseConfig.created_at.desc()).all()

# GET ONE - Line ~167
@router.get("/{config_id}", response_model=DatabaseResponse)
async def get_database_config(req: Request, config_id: str):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.tenant_id == tenant_id  # NEW
        ).first()

# UPDATE - Line ~211
@router.put("/{config_id}", response_model=DatabaseResponse)
async def update_database_config(req: Request, config_id: str, request: UpdateDatabaseRequest):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.tenant_id == tenant_id  # NEW
        ).first()

# DELETE - Line ~280
@router.delete("/{config_id}")
async def delete_database_config(req: Request, config_id: str):
    tenant_id = get_tenant_id(req)
    
    with db.get_session() as session:
        config = session.query(DatabaseConfig).filter(
            DatabaseConfig.id == config_id,
            DatabaseConfig.tenant_id == tenant_id  # NEW
        ).first()
```

## Important Notes

1. **Always add** `req: Request` parameter to route functions that need tenant isolation
2. **Always filter** by `tenant_id` in queries (except system-wide endpoints)
3. **Always set** `tenant_id` when creating new records
4. **Development mode** (tenant_id=0) allows testing without gateway
5. **Production mode** enforces tenant isolation via gateway

## Next Steps

1. Run migration script: `python backend/migrations/add_tenant_id.py`
2. Update route files following this pattern
3. Test each route with both development and production modes
4. Verify data isolation between tenants
