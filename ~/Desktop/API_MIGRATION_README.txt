API Migration System - Desktop Application

This is the updated API Migration System with bug fixes and working migration functionality.

HOW TO USE:
1. Double-click the "API Migration System" icon on your desktop
2. In the application:
   - Select source type (Directory or File)
   - Browse and select your source code file/directory
   - Browse and select a target file for the migrated code
   - Click "Run Migration"
3. The system will analyze your code and apply API migrations automatically
4. Check the progress in the text area
5. Use "Rollback" if needed, or "Export Report" for documentation

WHAT IT DOES:
- Converts timeout values from seconds to milliseconds (*1000)
- Changes data=json.dumps(...) to json=...
- Updates API client initialization for new timeout handling
- Transforms requests.post/put calls to use json parameter

EXAMPLE:
Use test_samples/sample_project_v1.py as source and create a new file as target to see the migration in action.

The application is located at: /home/mandar12/Desktop/software/