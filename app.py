#!/usr/bin/env python3
"""
API Migration System Desktop Application

A user-friendly GUI application for the Autonomous API Version Migration System.
Allows users to select source and target directories and run API migrations with
formal verification.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import sys
import threading
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

from api_migration_system import TransformationEngine


class APIMigrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("API Migration System")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Initialize variables
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.source_mode = tk.StringVar(value="directory")  # "directory" or "file"
        self.engine = None
        self.project_id = None
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(main_frame, text="Autonomous API Version Migration System",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Directory selection frame
        dir_frame = tk.LabelFrame(main_frame, text="Project Source & Target", padx=10, pady=10)
        dir_frame.pack(fill=tk.X, pady=(0, 20))

        # Source mode selection
        mode_frame = tk.Frame(dir_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(mode_frame, text="Source Type:", width=12, anchor="w").pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="Directory", variable=self.source_mode,
                      value="directory", command=self.update_source_label).pack(side=tk.LEFT, padx=(10, 5))
        tk.Radiobutton(mode_frame, text="File", variable=self.source_mode,
                      value="file", command=self.update_source_label).pack(side=tk.LEFT)

        # Source directory/file
        source_frame = tk.Frame(dir_frame)
        source_frame.pack(fill=tk.X, pady=(0, 10))

        self.source_label = tk.Label(source_frame, text="Source Directory:", width=15, anchor="w")
        self.source_label.pack(side=tk.LEFT)
        tk.Entry(source_frame, textvariable=self.source_dir, width=50).pack(side=tk.LEFT, padx=(10, 10))
        tk.Button(source_frame, text="Browse", command=self.select_source).pack(side=tk.LEFT)

        # Target file
        target_frame = tk.Frame(dir_frame)
        target_frame.pack(fill=tk.X)

        tk.Label(target_frame, text="Target File:", width=15, anchor="w").pack(side=tk.LEFT)
        tk.Entry(target_frame, textvariable=self.target_dir, width=50).pack(side=tk.LEFT, padx=(10, 10))
        tk.Button(target_frame, text="Browse", command=self.select_target_file).pack(side=tk.LEFT)

        # Control buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=(0, 20))

        self.run_button = tk.Button(button_frame, text="Run Migration", command=self.run_migration,
                                   bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))

        self.rollback_button = tk.Button(button_frame, text="Rollback", command=self.rollback_migration,
                                        state=tk.DISABLED)
        self.rollback_button.pack(side=tk.LEFT, padx=(0, 10))

        self.export_button = tk.Button(button_frame, text="Export Report", command=self.export_report,
                                     state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT)

        # Progress and results frame
        results_frame = tk.LabelFrame(main_frame, text="Progress & Results", padx=10, pady=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Progress text area
        self.progress_text = scrolledtext.ScrolledText(results_frame, height=20, wrap=tk.WORD)
        self.progress_text.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def update_source_label(self):
        """Update the source label based on selected mode."""
        if self.source_mode.get() == "directory":
            self.source_label.config(text="Source Directory:")
        else:
            self.source_label.config(text="Source File:")

    def select_source(self):
        """Select source directory or file based on mode."""
        if self.source_mode.get() == "directory":
            path = filedialog.askdirectory(title="Select Source Directory")
        else:
            path = filedialog.askopenfilename(
                title="Select Source File",
                filetypes=[("Python files", "*.py"), ("JavaScript files", "*.js"), ("All files", "*.*")]
            )
        if path:
            self.source_dir.set(path)

    def select_target_file(self):
        """Select target file."""
        file_path = filedialog.askopenfilename(
            title="Select Target File",
            filetypes=[("Python files", "*.py"), ("JavaScript files", "*.js"), ("All files", "*.*")]
        )
        if file_path:
            self.target_dir.set(file_path)

    def log_message(self, message):
        """Log a message to the progress text area."""
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.root.update_idletasks()

    def run_migration(self):
        """Run the migration process."""
        if self.is_running:
            return

        source = self.source_dir.get()
        target = self.target_dir.get()

        if not source or not target:
            messagebox.showerror("Error", "Please select both source and target.")
            return

        if not os.path.exists(source):
            source_type = "file" if self.source_mode.get() == "file" else "directory"
            messagebox.showerror("Error", f"Source {source_type} does not exist.")
            return

        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target), exist_ok=True)

        # Disable buttons
        self.run_button.config(state=tk.DISABLED, text="Running...")
        self.is_running = True
        self.status_var.set("Running migration...")

        # Clear progress
        self.progress_text.delete(1.0, tk.END)

        # Run migration in separate thread
        thread = threading.Thread(target=self._run_migration_thread, args=(source, target))
        thread.daemon = True
        thread.start()

    def _run_migration_thread(self, source, target):
        """Run migration in a separate thread."""
        try:
            self.log_message("🔍 Initializing API Migration System...")

            # Initialize engine
            self.engine = TransformationEngine()

            # Create project
            self.log_message("📁 Creating migration project...")
            self.project_id = self.engine.create_project(
                name="gui_migration",
                source_path=source,
                target_path=target
            )
            self.log_message(f"   ✅ Project created with ID: {self.project_id[:8]}...")

            # Analyze project
            self.log_message("\n🔍 Analyzing project for API changes...")
            analysis_results = self.engine.analyze_project(self.project_id)

            self.log_message(f"   📊 Found {len(analysis_results['api_entities'])} API entities")
            self.log_message(f"   🔧 Identified {len(analysis_results['transformation_opportunities'])} transformation opportunities")
            self.log_message(f"   📈 Complexity score: {analysis_results['complexity_score']:.2f}")

            # Plan transformations
            self.log_message("\n📋 Planning transformations...")
            operations = self.engine.plan_transformations(self.project_id)
            self.log_message(f"   ✅ Planned {len(operations)} transformation operations")

            # Show planned transformations
            for i, op in enumerate(operations, 1):
                self.log_message(f"   {i}. {op.file_path} - {len(op.changes)} changes")

            # Execute transformations
            self.log_message("\n🚀 Executing transformations...")
            results = self.engine.execute_transformations(self.project_id, dry_run=False)
            self.log_message(f"   ✅ Completed {results['successful_operations']} operations")
            self.log_message(f"   💾 Created backup at: {results.get('backup_path', 'N/A')}")

            # Show transformation results
            self.log_message("\n📄 Transformation Results:")
            for operation in operations:
                original_lines = operation.original_content.count('\n') + 1
                transformed_lines = operation.transformed_content.count('\n') + 1
                self.log_message(f"   📁 {operation.file_path}: {original_lines} → {transformed_lines} lines")

                # Show proof certificate summary
                if operation.proof_certificate:
                    cert = operation.proof_certificate
                    self.log_message(f"      🔐 Proof ID: {cert['transformation_id'][:8]}...")
                    self.log_message(f"      ✅ Status: {cert['verification_status']}")

            # Test source and target files
            self.log_message("\n🧪 Testing source and target files...")
            test_results = self.engine.test_source_and_target(self.project_id)

            self.log_message(f"   📊 Source tests: {'✅ Passed' if test_results['source_tests'].get('success') else '❌ Failed'}")
            self.log_message(f"   📊 Target tests: {'✅ Passed' if test_results['target_tests'].get('success') else '❌ Failed'}")

            if test_results['comparison']['equivalent']:
                self.log_message("   ✅ Test results are equivalent")
            else:
                self.log_message("   ⚠️  Test results differ - please review")

            # Create tested file (test file for migrated code)
            self.log_message("\n📝 Creating tested file...")
            try:
                test_file_path = self.engine.create_tested_file(self.project_id)
                self.log_message(f"   ✅ Test file created: {test_file_path}")
            except Exception as e:
                self.log_message(f"   ⚠️  Could not create test file: {str(e)}")

            self.log_message("\n✅ Migration completed successfully!")
            self.status_var.set("Migration completed")

            # Enable buttons
            self.rollback_button.config(state=tk.NORMAL)
            self.export_button.config(state=tk.NORMAL)

        except Exception as e:
            self.log_message(f"\n❌ Error during migration: {str(e)}")
            self.status_var.set("Migration failed")
            messagebox.showerror("Migration Error", f"An error occurred: {str(e)}")

        finally:
            self.run_button.config(state=tk.NORMAL, text="Run Migration")
            self.is_running = False

    def rollback_migration(self):
        """Rollback the migration."""
        if not self.engine or not self.project_id:
            messagebox.showerror("Error", "No migration to rollback.")
            return

        if messagebox.askyesno("Confirm Rollback", "Are you sure you want to rollback the migration? This will restore the original files."):
            try:
                self.log_message("\n🔄 Performing rollback...")
                success = self.engine.rollback_transformations(self.project_id)
                if success:
                    self.log_message("   ✅ Rollback completed successfully")
                    self.status_var.set("Rollback completed")
                else:
                    self.log_message("   ❌ Rollback failed")
                    self.status_var.set("Rollback failed")
            except Exception as e:
                self.log_message(f"   ❌ Rollback error: {str(e)}")
                messagebox.showerror("Rollback Error", f"An error occurred: {str(e)}")

    def export_report(self):
        """Export migration report."""
        if not self.engine or not self.project_id:
            messagebox.showerror("Error", "No migration report to export.")
            return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Migration Report"
        )

        if file_path:
            try:
                exported_path = self.engine.export_project_report(self.project_id, file_path)
                self.log_message(f"\n📊 Report exported to: {exported_path}")
                messagebox.showinfo("Export Complete", f"Report saved to: {exported_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export report: {str(e)}")


def main():
    """Main application entry point."""
    root = tk.Tk()
    app = APIMigrationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()