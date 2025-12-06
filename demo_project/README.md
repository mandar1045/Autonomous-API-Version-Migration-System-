# Demo Project for API Migration

This is a sample project to demonstrate the API Migration System application.

## Files

- `source/api_client.py` - API client code using old timeout format (seconds)
- `source/utils.py` - Utility functions with API calls
- `target/` - Directory where migrated code will be placed

## Expected Migrations

The system should automatically detect and migrate:

1. **Timeout scaling**: `timeout=30` → `timeout=30*1000` (seconds to milliseconds)
2. **Parameter renaming**: `data=json.dumps(payload)` → `json=json.dumps(payload)`
3. **Consistent API usage patterns**

## How to Use

1. Run the GUI application: `python3 app.py`
2. Select `demo_project/source` as source directory
3. Select `demo_project/target` as target directory
4. Click "Run Migration"
5. View the results and export reports if needed

## After Migration

Check the `target/` directory for the migrated code with updated API calls.