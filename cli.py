#!/usr/bin/env python3
"""
Command-Line Interface for Autonomous API Version Migration System
"""

import argparse
import sys
import os
import json
from api_migration_system import TransformationEngine

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous API Version Migration System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a dry-run migration to see proposed changes
  python cli.py --source ./src --target ./migrated --dry-run
  
  # Execute an actual migration and export a report
  python cli.py --source ./src --target ./migrated --export-report report.json
  
  # Rollback a previous migration (requires the backup to still exist)
  python cli.py --rollback --target ./migrated
"""
    )

    parser.add_argument("--source", type=str, help="Source directory or file to migrate")
    parser.add_argument("--target", type=str, help="Target directory for migrated code")
    parser.add_argument("--dry-run", action="store_true", help="Plan transformations without writing files")
    parser.add_argument("--export-report", type=str, metavar="PATH", help="Export migration report to JSON file")
    parser.add_argument("--rollback", action="store_true", help="Rollback target directory using backup")
    
    args = parser.parse_args()

    engine = TransformationEngine()

    if args.rollback:
        if not args.target:
            print("Error: --target is required for rollback.")
            sys.exit(1)
        
        # We need a project ID to rollback, but in CLI context we might just want to restore the backup
        backup_path = f"{args.target}.backup"
        if not os.path.exists(backup_path):
            print(f"Error: Backup path '{backup_path}' does not exist.")
            sys.exit(1)
            
        print(f"Rolling back '{args.target}' from backup '{backup_path}'...")
        import shutil
        if os.path.exists(args.target):
            if os.path.isfile(args.target):
                os.remove(args.target)
            else:
                shutil.rmtree(args.target)
                
        if os.path.isfile(backup_path):
            shutil.copy2(backup_path, args.target)
        else:
            shutil.copytree(backup_path, args.target, dirs_exist_ok=True)
            
        print("Rollback successful.")
        sys.exit(0)

    if not args.source or not args.target:
        print("Error: --source and --target are required for migration.")
        parser.print_help()
        sys.exit(1)

    print(f"🔍 Analyzing source: {args.source}")
    project_id = engine.create_project("cli_migration", args.source, args.target)
    
    analysis = engine.analyze_project(project_id)
    entities_count = len(analysis.get("api_entities", []))
    opportunities = len(analysis.get("transformation_opportunities", []))
    
    print(f"   📊 Found {entities_count} API entities")
    print(f"   🔧 Identified {opportunities} transformation opportunities")

    print(f"📋 Planning transformations...")
    operations = engine.plan_transformations(project_id)
    print(f"   ✅ Planned {len(operations)} operations")

    if args.dry_run:
        print(f"🚀 Executing dry run...")
        results = engine.execute_transformations(project_id, dry_run=True)
        print(f"   ✅ Simulated {results['successful_operations']} operations")
    else:
        print(f"💾 Executing transformations...")
        results = engine.execute_transformations(project_id, dry_run=False)
        print(f"   ✅ Completed {results['successful_operations']} successful operations")
        if results['failed_operations'] > 0:
            print(f"   ❌ {results['failed_operations']} operations failed")
        if results.get('backup_path'):
            print(f"   💾 Backup created at: {results['backup_path']}")

    if args.export_report:
        print(f"📊 Exporting report to {args.export_report}...")
        report_json = engine.export_project_report(project_id, args.export_report)
        print("   ✅ Export complete")

if __name__ == "__main__":
    main()
