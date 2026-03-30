#!/usr/bin/env python3
"""
API Migration System Desktop Application

A modern desktop interface for the Autonomous API Version Migration System.
Lets users select source and target paths, run migrations, review the proof
trail, and export reports from a cleaner visual workflow.
"""

import os
import queue
import sys
import tempfile
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Add current directory to path
sys.path.insert(0, ".")

from api_migration_system import TransformationEngine


class APIMigrationApp:
    """Modern GUI wrapper around the migration engine."""

    COLORS = {
        "bg": "#f3f6fb",
        "bg_alt": "#eaf0f8",
        "hero": "#ffffff",
        "hero_text": "#0f172a",
        "card": "#ffffff",
        "card_alt": "#f8fbff",
        "muted_card": "#eef3f9",
        "border": "#d8e1ec",
        "text": "#172033",
        "subtext": "#66758b",
        "accent": "#2563eb",
        "accent_dark": "#1d4ed8",
        "accent_soft": "#e8f0ff",
        "accent_text": "#ffffff",
        "success": "#16a34a",
        "warning": "#d97706",
        "danger": "#dc2626",
        "info": "#0284c7",
        "console_bg": "#f8fbff",
        "console_text": "#1e293b",
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Autonomous API Migration Studio")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)
        self.root.configure(bg=self.COLORS["bg"])

        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.source_mode = tk.StringVar(value="directory")
        self.status_var = tk.StringVar(value="Ready")
        self.phase_var = tk.StringVar(value="Select a source and destination to begin.")
        self.source_caption_var = tk.StringVar(value="Source directory")
        self.target_caption_var = tk.StringVar(value="Target directory")
        self.helper_var = tk.StringVar(
            value="Directory mode migrates an entire codebase. File mode is ideal for one-off upgrades."
        )

        self.metric_vars = {
            "status": tk.StringVar(value="Ready"),
            "entities": tk.StringVar(value="0"),
            "opportunities": tk.StringVar(value="0"),
            "operations": tk.StringVar(value="0"),
            "confidence": tk.StringVar(value="-"),
        }

        self.engine = None
        self.project_id = None
        self.is_running = False
        self.ui_queue: queue.Queue = queue.Queue()
        self.controls = []
        self.mode_buttons = {}

        self._configure_fonts()
        self._configure_styles()
        self._build_ui()
        self._apply_mode_state()
        self._queue_pump()

    def _configure_fonts(self) -> None:
        """Apply a friendlier font palette to the entire app."""
        family = self._pick_font_family(
            "Ubuntu",
            "Noto Sans",
            "Cantarell",
            "Inter",
            "Segoe UI",
            "SF Pro Display",
            "DejaVu Sans",
            "Liberation Sans",
        )
        mono_family = self._pick_font_family(
            "JetBrains Mono",
            "Fira Code",
            "Consolas",
            "DejaVu Sans Mono",
            "Courier New",
            "Courier",
        )

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family=family, size=11)
        tkfont.nametofont("TkTextFont").configure(family=family, size=11)
        tkfont.nametofont("TkHeadingFont").configure(family=family, size=11, weight="bold")
        tkfont.nametofont("TkMenuFont").configure(family=family, size=10)

        self.fonts = {
            "hero_badge": (family, 9),
            "hero_title": (family, 28, "bold"),
            "hero_subtitle": (family, 11),
            "section_title": (family, 15, "bold"),
            "card_title": (family, 11, "bold"),
            "body": (family, 11),
            "small": (family, 10),
            "metric": (family, 24, "bold"),
            "button": (family, 11, "bold"),
            "mono": (family, 10),
        }

    def _pick_font_family(self, *candidates: str) -> str:
        """Return the first installed font family from *candidates*."""
        available = set(tkfont.families())
        for candidate in candidates:
            if candidate in available:
                return candidate
        return "TkDefaultFont"

    def _configure_styles(self) -> None:
        """Style ttk widgets so they match the custom layout."""
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.style.configure(
            "Studio.Horizontal.TProgressbar",
            troughcolor=self.COLORS["muted_card"],
            background=self.COLORS["accent"],
            bordercolor=self.COLORS["muted_card"],
            lightcolor=self.COLORS["accent"],
            darkcolor=self.COLORS["accent"],
            thickness=10,
        )

        self.style.configure(
            "Studio.Vertical.TScrollbar",
            background=self.COLORS["muted_card"],
            troughcolor=self.COLORS["bg_alt"],
            arrowcolor=self.COLORS["subtext"],
            bordercolor=self.COLORS["bg_alt"],
        )

    def _build_ui(self) -> None:
        """Create the modern desktop layout."""
        shell = tk.Frame(self.root, bg=self.COLORS["bg"])
        shell.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        self._build_hero(shell)

        content = tk.Frame(shell, bg=self.COLORS["bg"])
        content.grid(row=1, column=0, sticky="nsew", pady=(18, 0))
        content.grid_columnconfigure(0, weight=0, minsize=360)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.left_panel = tk.Frame(content, bg=self.COLORS["bg"])
        self.left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 18))

        self.right_panel = tk.Frame(content, bg=self.COLORS["bg"])
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1)

        self._build_setup_panel()
        self._build_metrics_panel()
        self._build_activity_panel()

    def _build_hero(self, parent: tk.Widget) -> None:
        hero = tk.Frame(parent, bg=self.COLORS["hero"], padx=28, pady=24, highlightthickness=0)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left = tk.Frame(hero, bg=self.COLORS["hero"])
        left.grid(row=0, column=0, sticky="w")

        badge = tk.Label(
            left,
            text="Migration command center",
            bg=self.COLORS["accent_soft"],
            fg=self.COLORS["accent"],
            padx=10,
            pady=5,
            font=self.fonts["hero_badge"],
        )
        badge.pack(anchor="w")

        title = tk.Label(
            left,
            text="Autonomous API Migration Studio",
            bg=self.COLORS["hero"],
            fg=self.COLORS["hero_text"],
            font=self.fonts["hero_title"],
        )
        title.pack(anchor="w", pady=(14, 6))

        subtitle = tk.Label(
            left,
            text=(
                "Run API upgrades with clear progress, proof-backed confidence, "
                "and rollback safety from a cleaner desktop workspace."
            ),
            bg=self.COLORS["hero"],
            fg=self.COLORS["subtext"],
            justify=tk.LEFT,
            wraplength=740,
            font=self.fonts["hero_subtitle"],
        )
        subtitle.pack(anchor="w")

        right = tk.Frame(hero, bg=self.COLORS["hero"])
        right.grid(row=0, column=1, sticky="e")

        self.status_chip = tk.Label(
            right,
            textvariable=self.status_var,
            bg=self.COLORS["accent_soft"],
            fg=self.COLORS["accent"],
            padx=16,
            pady=8,
            font=self.fonts["card_title"],
        )
        self.status_chip.pack(anchor="e")

        phase = tk.Label(
            right,
            textvariable=self.phase_var,
            bg=self.COLORS["hero"],
            fg=self.COLORS["subtext"],
            justify=tk.RIGHT,
            wraplength=260,
            font=self.fonts["small"],
        )
        phase.pack(anchor="e", pady=(12, 0))

    def _build_setup_panel(self) -> None:
        setup_card = self._card(self.left_panel, "Migration Setup", "Choose your source, output path, and migration mode.")
        setup_card.pack(fill=tk.X)

        toggle_frame = tk.Frame(setup_card, bg=self.COLORS["muted_card"], padx=6, pady=6)
        toggle_frame.pack(fill=tk.X, pady=(2, 14))
        toggle_frame.grid_columnconfigure(0, weight=1)
        toggle_frame.grid_columnconfigure(1, weight=1)

        self.mode_buttons["directory"] = tk.Button(
            toggle_frame,
            text="Directory Migration",
            command=lambda: self.set_source_mode("directory"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=10,
            font=self.fonts["button"],
        )
        self.mode_buttons["directory"].grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.mode_buttons["file"] = tk.Button(
            toggle_frame,
            text="Single File",
            command=lambda: self.set_source_mode("file"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=14,
            pady=10,
            font=self.fonts["button"],
        )
        self.mode_buttons["file"].grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.controls.extend(self.mode_buttons.values())

        self.source_entry = self._build_path_field(
            setup_card,
            caption_var=self.source_caption_var,
            value_var=self.source_dir,
            button_text="Browse",
            button_command=self.select_source,
        )
        self.target_entry = self._build_path_field(
            setup_card,
            caption_var=self.target_caption_var,
            value_var=self.target_dir,
            button_text="Choose",
            button_command=self.select_target,
            top_padding=10,
        )

        helper = tk.Label(
            setup_card,
            textvariable=self.helper_var,
            bg=self.COLORS["card"],
            fg=self.COLORS["subtext"],
            justify=tk.LEFT,
            wraplength=300,
            font=self.fonts["small"],
        )
        helper.pack(anchor="w", pady=(12, 0))

        shortcuts_card = self._card(
            self.left_panel,
            "Quick Actions",
            "Use the bundled sample project, clear paths, or export and rollback once a run completes.",
        )
        shortcuts_card.pack(fill=tk.X, pady=(18, 0))

        quick_actions = tk.Frame(shortcuts_card, bg=self.COLORS["card"])
        quick_actions.pack(fill=tk.X)
        quick_actions.grid_columnconfigure(0, weight=1)
        quick_actions.grid_columnconfigure(1, weight=1)

        demo_button = self._button(
            quick_actions,
            text="Load Demo Project",
            command=self.load_demo_project,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            active_bg="#dde7f4",
        )
        demo_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.controls.append(demo_button)

        clear_button = self._button(
            quick_actions,
            text="Clear Paths",
            command=self.clear_paths,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            active_bg="#dde7f4",
        )
        clear_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.controls.append(clear_button)

        control_card = self._card(
            self.left_panel,
            "Run Controls",
            "Launch a migration, export the latest report, or restore from the last backup.",
        )
        control_card.pack(fill=tk.X, pady=(18, 0))

        self.run_button = self._button(
            control_card,
            text="Run Migration",
            command=self.run_migration,
            bg=self.COLORS["accent"],
            fg=self.COLORS["accent_text"],
            active_bg=self.COLORS["accent_dark"],
            padx=18,
            pady=14,
        )
        self.run_button.pack(fill=tk.X)

        secondary_actions = tk.Frame(control_card, bg=self.COLORS["card"])
        secondary_actions.pack(fill=tk.X, pady=(10, 0))
        secondary_actions.grid_columnconfigure(0, weight=1)
        secondary_actions.grid_columnconfigure(1, weight=1)

        self.rollback_button = self._button(
            secondary_actions,
            text="Rollback",
            command=self.rollback_migration,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            active_bg="#dde7f4",
            state=tk.DISABLED,
        )
        self.rollback_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.export_button = self._button(
            secondary_actions,
            text="Export Report",
            command=self.export_report,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            active_bg="#dde7f4",
            state=tk.DISABLED,
        )
        self.export_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.controls.extend([self.run_button, self.rollback_button, self.export_button])

    def _build_metrics_panel(self) -> None:
        metrics_frame = tk.Frame(self.right_panel, bg=self.COLORS["bg"])
        metrics_frame.grid(row=0, column=0, sticky="ew")
        for column in range(5):
            metrics_frame.grid_columnconfigure(column, weight=1)

        self._metric_card(metrics_frame, 0, "Status", self.metric_vars["status"], "Live run state")
        self._metric_card(metrics_frame, 1, "Entities", self.metric_vars["entities"], "Detected API symbols")
        self._metric_card(metrics_frame, 2, "Opportunities", self.metric_vars["opportunities"], "Migration candidates")
        self._metric_card(metrics_frame, 3, "Operations", self.metric_vars["operations"], "Files queued")
        self._metric_card(metrics_frame, 4, "Confidence", self.metric_vars["confidence"], "Average proof score")

        progress_card = self._card(
            self.right_panel,
            "Execution Progress",
            "The pipeline runs in the background while the dashboard stays responsive.",
        )
        progress_card.grid(row=1, column=0, sticky="ew", pady=(18, 18))

        self.progress_label = tk.Label(
            progress_card,
            textvariable=self.phase_var,
            bg=self.COLORS["card"],
            fg=self.COLORS["text"],
            anchor="w",
            justify=tk.LEFT,
            font=self.fonts["body"],
        )
        self.progress_label.pack(fill=tk.X)

        self.progress = ttk.Progressbar(progress_card, mode="indeterminate", style="Studio.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, pady=(12, 2))

    def _build_activity_panel(self) -> None:
        activity_card = self._card(
            self.right_panel,
            "Activity Stream",
            "Every analysis step, transformation decision, and export event is logged here.",
        )
        activity_card.grid(row=2, column=0, sticky="nsew")
        activity_card.grid_rowconfigure(1, weight=1)
        activity_card.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(activity_card, bg=self.COLORS["card"])
        toolbar.pack(fill=tk.X, pady=(4, 10))

        clear_log_button = self._button(
            toolbar,
            text="Clear Log",
            command=self.clear_log,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            active_bg="#dde7f4",
            padx=12,
            pady=8,
        )
        clear_log_button.pack(side=tk.LEFT)
        self.controls.append(clear_log_button)

        activity_hint = tk.Label(
            toolbar,
            text="Thread-safe live console",
            bg=self.COLORS["card"],
            fg=self.COLORS["subtext"],
            font=self.fonts["small"],
        )
        activity_hint.pack(side=tk.RIGHT)

        console_shell = tk.Frame(
            activity_card,
            bg=self.COLORS["console_bg"],
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
        )
        console_shell.pack(fill=tk.BOTH, expand=True)
        console_shell.grid_rowconfigure(0, weight=1)
        console_shell.grid_columnconfigure(0, weight=1)

        self.progress_text = tk.Text(
            console_shell,
            bg=self.COLORS["console_bg"],
            fg=self.COLORS["console_text"],
            insertbackground=self.COLORS["console_text"],
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=16,
            pady=16,
            font=self.fonts["mono"],
            selectbackground="#dbeafe",
        )
        self.progress_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(console_shell, orient=tk.VERTICAL, command=self.progress_text.yview, style="Studio.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.progress_text.configure(yscrollcommand=scrollbar.set)

        self.progress_text.tag_configure("success", foreground="#15803d")
        self.progress_text.tag_configure("warning", foreground="#b45309")
        self.progress_text.tag_configure("error", foreground="#b91c1c")
        self.progress_text.tag_configure("info", foreground="#1d4ed8")
        self.progress_text.tag_configure("headline", foreground=self.COLORS["text"])

        self._append_log("Studio ready. Pick a source and target, or load the bundled demo project.")

    def _card(self, parent: tk.Widget, title: str, subtitle: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self.COLORS["card"],
            padx=18,
            pady=18,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
            bd=0,
        )

        title_label = tk.Label(
            frame,
            text=title,
            bg=self.COLORS["card"],
            fg=self.COLORS["text"],
            anchor="w",
            font=self.fonts["section_title"],
        )
        title_label.pack(anchor="w")

        subtitle_label = tk.Label(
            frame,
            text=subtitle,
            bg=self.COLORS["card"],
            fg=self.COLORS["subtext"],
            justify=tk.LEFT,
            wraplength=320,
            font=self.fonts["small"],
        )
        subtitle_label.pack(anchor="w", pady=(6, 14))
        return frame

    def _metric_card(self, parent: tk.Widget, column: int, title: str, value_var: tk.StringVar, subtitle: str) -> None:
        card = tk.Frame(
            parent,
            bg=self.COLORS["card"],
            padx=16,
            pady=16,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))

        card_bg = self.COLORS["card"]
        tk.Label(card, text=title, bg=card_bg, fg=self.COLORS["subtext"], font=self.fonts["small"]).pack(anchor="w")
        tk.Label(card, textvariable=value_var, bg=card_bg, fg=self.COLORS["text"], font=self.fonts["metric"]).pack(anchor="w", pady=(10, 4))
        tk.Label(card, text=subtitle, bg=card_bg, fg=self.COLORS["subtext"], wraplength=150, justify=tk.LEFT, font=self.fonts["small"]).pack(anchor="w")

    def _build_path_field(
        self,
        parent: tk.Widget,
        caption_var: tk.StringVar,
        value_var: tk.StringVar,
        button_text: str,
        button_command,
        top_padding: int = 0,
    ) -> tk.Entry:
        container = tk.Frame(parent, bg=self.COLORS["card"])
        container.pack(fill=tk.X, pady=(top_padding, 0))
        container.grid_columnconfigure(0, weight=1)

        tk.Label(
            container,
            textvariable=caption_var,
            bg=self.COLORS["card"],
            fg=self.COLORS["text"],
            anchor="w",
            font=self.fonts["card_title"],
        ).grid(row=0, column=0, sticky="w")

        field_shell = tk.Frame(
            container,
            bg=self.COLORS["muted_card"],
            padx=8,
            pady=8,
            highlightbackground=self.COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        field_shell.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        field_shell.grid_columnconfigure(0, weight=1)

        entry = tk.Entry(
            field_shell,
            textvariable=value_var,
            relief=tk.FLAT,
            bd=0,
            bg=self.COLORS["muted_card"],
            fg=self.COLORS["text"],
            insertbackground=self.COLORS["text"],
            font=self.fonts["body"],
        )
        entry.grid(row=0, column=0, sticky="ew", padx=(4, 8))

        button = self._button(
            field_shell,
            text=button_text,
            command=button_command,
            bg=self.COLORS["accent"],
            fg=self.COLORS["accent_text"],
            active_bg=self.COLORS["accent_dark"],
            padx=12,
            pady=8,
        )
        button.grid(row=0, column=1)
        self.controls.extend([entry, button])
        return entry

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        bg: str,
        fg: str,
        active_bg: str,
        padx: int = 14,
        pady: int = 10,
        state: str = tk.NORMAL,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            padx=padx,
            pady=pady,
            state=state,
            font=self.fonts["button"],
            highlightthickness=0,
            borderwidth=0,
        )

    def _queue_pump(self) -> None:
        """Process queued UI updates from background threads."""
        while True:
            try:
                callback, args, kwargs = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            callback(*args, **kwargs)
        self.root.after(50, self._queue_pump)

    def _post_ui(self, callback, *args, **kwargs) -> None:
        """Push a UI operation back to the main Tk thread."""
        self.ui_queue.put((callback, args, kwargs))

    def set_source_mode(self, mode: str) -> None:
        """Switch between directory and file migration modes."""
        if self.is_running:
            return
        self.source_mode.set(mode)
        self._apply_mode_state()

    def _apply_mode_state(self) -> None:
        """Refresh labels, hints, and mode button styling."""
        if self.source_mode.get() == "directory":
            self.source_caption_var.set("Source directory")
            self.target_caption_var.set("Target directory")
            self.helper_var.set(
                "Directory mode migrates an entire codebase and keeps file structure in the destination."
            )
        else:
            self.source_caption_var.set("Source file")
            self.target_caption_var.set("Target file")
            self.helper_var.set(
                "File mode upgrades one file in place and writes the transformed output to a single target file."
            )

        for mode, button in self.mode_buttons.items():
            active = mode == self.source_mode.get()
            button.configure(
                bg=self.COLORS["accent"] if active else self.COLORS["muted_card"],
                fg=self.COLORS["accent_text"] if active else self.COLORS["text"],
                activebackground=self.COLORS["accent_dark"] if active else "#dde7f4",
                activeforeground=self.COLORS["accent_text"] if active else self.COLORS["text"],
            )

    def load_demo_project(self) -> None:
        """Populate the bundled demo paths for quick exploration."""
        demo_source = Path.cwd() / "demo_project" / "source"
        demo_target = Path(tempfile.gettempdir()) / "api-migration-studio-output"
        self.source_mode.set("directory")
        self.source_dir.set(str(demo_source))
        self.target_dir.set(str(demo_target))
        self._apply_mode_state()
        self._append_log(f"Loaded demo project from {demo_source}")
        self._set_phase("Demo project loaded and ready to run.")

    def clear_paths(self) -> None:
        """Clear the selected source and target paths."""
        if self.is_running:
            return
        self.source_dir.set("")
        self.target_dir.set("")
        self._append_log("Cleared source and target fields.")
        self._set_phase("Waiting for source and target paths.")

    def select_source(self) -> None:
        """Open the native picker for the source path."""
        if self.source_mode.get() == "directory":
            path = filedialog.askdirectory(title="Select Source Directory")
        else:
            path = filedialog.askopenfilename(
                title="Select Source File",
                filetypes=[("Python files", "*.py"), ("JavaScript files", "*.js"), ("All files", "*.*")],
            )
        if path:
            self.source_dir.set(path)

    def select_target(self) -> None:
        """Open the native picker for the target path."""
        if self.source_mode.get() == "directory":
            path = filedialog.askdirectory(title="Select Target Directory")
        else:
            path = filedialog.asksaveasfilename(
                title="Select Target File",
                defaultextension=".py",
                filetypes=[("Python files", "*.py"), ("JavaScript files", "*.js"), ("All files", "*.*")],
            )
        if path:
            self.target_dir.set(path)

    def run_migration(self) -> None:
        """Validate inputs and launch the migration thread."""
        if self.is_running:
            return

        source = self.source_dir.get().strip()
        target = self.target_dir.get().strip()

        if not source or not target:
            messagebox.showerror("Missing Paths", "Choose both a source path and a target path before starting.")
            return

        if not os.path.exists(source):
            source_type = "file" if self.source_mode.get() == "file" else "directory"
            messagebox.showerror("Missing Source", f"The selected source {source_type} does not exist.")
            return

        if self.source_mode.get() == "directory":
            os.makedirs(target, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(target) or ".", exist_ok=True)

        self._reset_metrics()
        self._clear_log_widget()
        self._append_log("Starting migration pipeline...")
        self._append_log(f"Source: {source}")
        self._append_log(f"Target: {target}")
        self._set_running_state(True)
        self._set_status("Running", tone="info")
        self._set_phase("Initializing migration engine...")

        thread = threading.Thread(target=self._run_migration_thread, args=(source, target), daemon=True)
        thread.start()

    def _run_migration_thread(self, source: str, target: str) -> None:
        """Execute the migration flow off the main thread."""
        try:
            self._post_ui(self._append_log, "Bootstrapping engine...")
            self.engine = TransformationEngine()

            self._post_ui(self._set_phase, "Creating migration project...")
            self.project_id = self.engine.create_project(
                name="gui_migration",
                source_path=source,
                target_path=target,
            )
            self._post_ui(self._append_log, f"Created project {self.project_id[:8]}...")

            self._post_ui(self._set_phase, "Analyzing source for API entities and migration opportunities...")
            analysis_results = self.engine.analyze_project(self.project_id)
            entity_count = len(analysis_results["api_entities"])
            opportunity_count = len(analysis_results["transformation_opportunities"])

            self._post_ui(self._set_metric, "entities", str(entity_count))
            self._post_ui(self._set_metric, "opportunities", str(opportunity_count))
            self._post_ui(self._append_log, f"Detected {entity_count} API entities.")
            self._post_ui(self._append_log, f"Found {opportunity_count} transformation opportunities.")
            self._post_ui(self._append_log, f"Complexity score: {analysis_results['complexity_score']:.2f}")

            self._post_ui(self._set_phase, "Planning file-level transformation operations...")
            operations = self.engine.plan_transformations(self.project_id)
            self._post_ui(self._set_metric, "operations", str(len(operations)))
            self._post_ui(self._append_log, f"Planned {len(operations)} transformation operations.")

            for index, operation in enumerate(operations, start=1):
                self._post_ui(self._append_log, f"  {index}. {operation.file_path} ({len(operation.changes)} changes)")

            confidence_values = [
                operation.proof_certificate.get("confidence", 0)
                for operation in operations
                if operation.proof_certificate
            ]
            if confidence_values:
                avg_confidence = sum(confidence_values) / len(confidence_values)
                self._post_ui(self._set_metric, "confidence", f"{avg_confidence:.2f}")

            self._post_ui(self._set_phase, "Executing migration and writing transformed output...")
            execution_results = self.engine.execute_transformations(self.project_id, dry_run=False)
            self._post_ui(self._append_log, f"Completed {execution_results['successful_operations']} operations.")
            self._post_ui(self._append_log, f"Backup path: {execution_results.get('backup_path', 'N/A')}")

            self._post_ui(self._append_log, "Reviewing generated proof certificates...")
            for operation in operations:
                if operation.proof_certificate:
                    certificate = operation.proof_certificate
                    self._post_ui(
                        self._append_log,
                        f"  {operation.file_path}: {certificate['verification_status']} ({certificate['confidence']:.2f})",
                    )

            self._post_ui(self._set_phase, "Running source and target verification checks...")
            test_results = self.engine.test_source_and_target(self.project_id)
            source_ok = test_results["source_tests"].get("success", test_results["source_tests"].get("overall_success"))
            target_ok = test_results["target_tests"].get("success", test_results["target_tests"].get("overall_success"))

            self._post_ui(self._append_log, f"Source tests: {'passed' if source_ok else 'failed'}")
            self._post_ui(self._append_log, f"Target tests: {'passed' if target_ok else 'failed'}")
            self._post_ui(
                self._append_log,
                "Behavioral comparison: equivalent" if test_results["comparison"]["equivalent"] else "Behavioral comparison: review needed",
            )

            self._post_ui(self._set_phase, "Generating companion validation file...")
            try:
                test_file_path = self.engine.create_tested_file(self.project_id)
                self._post_ui(self._append_log, f"Generated validation file: {test_file_path}")
            except Exception as exc:
                self._post_ui(self._append_log, f"Validation file skipped: {exc}")

            self._post_ui(self._handle_success)
        except Exception as exc:
            self._post_ui(self._handle_failure, str(exc))

    def rollback_migration(self) -> None:
        """Rollback the latest migration result."""
        if not self.engine or not self.project_id:
            messagebox.showerror("No Migration", "Run a migration before attempting rollback.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Rollback",
            "Rollback will restore the last backed-up target. Do you want to continue?",
        )
        if not confirmed:
            return

        try:
            self._append_log("Starting rollback...")
            success = self.engine.rollback_transformations(self.project_id)
            if success:
                self._append_log("Rollback completed successfully.")
                self._set_status("Rolled Back", tone="warning")
                self._set_metric("status", "Rolled Back")
                self._set_phase("Rollback completed. You can rerun the migration or export the previous report.")
            else:
                self._append_log("Rollback failed.")
                self._set_status("Rollback Failed", tone="danger")
        except Exception as exc:
            self._append_log(f"Rollback error: {exc}")
            self._set_status("Rollback Failed", tone="danger")
            messagebox.showerror("Rollback Error", f"An error occurred during rollback:\n\n{exc}")

    def export_report(self) -> None:
        """Export the latest migration report to a JSON file."""
        if not self.engine or not self.project_id:
            messagebox.showerror("No Report", "Run a migration before exporting a report.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Migration Report",
        )

        if not file_path:
            return

        try:
            exported_path = self.engine.export_project_report(self.project_id, file_path)
            self._append_log(f"Report exported to {exported_path}")
            self._set_phase("Report exported successfully.")
            messagebox.showinfo("Export Complete", f"Migration report saved to:\n\n{exported_path}")
        except Exception as exc:
            self._append_log(f"Report export failed: {exc}")
            messagebox.showerror("Export Error", f"Failed to export the migration report:\n\n{exc}")

    def clear_log(self) -> None:
        """Public action for clearing the activity stream."""
        self._clear_log_widget()
        self._append_log("Activity stream cleared.")

    def _clear_log_widget(self) -> None:
        self.progress_text.delete("1.0", tk.END)

    def _append_log(self, message: str) -> None:
        """Write one message to the activity stream with light categorization."""
        lowered = message.lower()
        tag = "headline"
        if "failed" in lowered or "error" in lowered:
            tag = "error"
        elif "warning" in lowered or "review needed" in lowered or "skipped" in lowered:
            tag = "warning"
        elif "completed" in lowered or "success" in lowered or "passed" in lowered or "equivalent" in lowered:
            tag = "success"
        elif "starting" in lowered or "bootstrapping" in lowered or "created" in lowered or "detected" in lowered:
            tag = "info"

        self.progress_text.insert(tk.END, message + "\n", tag)
        self.progress_text.see(tk.END)

    def _set_status(self, text: str, tone: str = "neutral") -> None:
        """Update the hero status chip and the status metric."""
        tone_map = {
            "neutral": (self.COLORS["accent_soft"], self.COLORS["accent"]),
            "info": ("#e0f2fe", self.COLORS["info"]),
            "success": ("#dcfce7", self.COLORS["success"]),
            "warning": ("#ffedd5", self.COLORS["warning"]),
            "danger": ("#fee2e2", self.COLORS["danger"]),
        }
        bg, fg = tone_map.get(tone, tone_map["neutral"])
        self.status_chip.configure(bg=bg, fg=fg)
        self.status_var.set(text)
        self.metric_vars["status"].set(text)

    def _set_phase(self, text: str) -> None:
        self.phase_var.set(text)

    def _set_metric(self, name: str, value: str) -> None:
        if name in self.metric_vars:
            self.metric_vars[name].set(value)

    def _reset_metrics(self) -> None:
        self.metric_vars["status"].set("Preparing")
        self.metric_vars["entities"].set("0")
        self.metric_vars["opportunities"].set("0")
        self.metric_vars["operations"].set("0")
        self.metric_vars["confidence"].set("-")

    def _set_running_state(self, running: bool) -> None:
        """Toggle controls and the progress animation based on run state."""
        self.is_running = running

        for control in self.controls:
            try:
                if control in (self.rollback_button, self.export_button) and not running:
                    continue
                control.configure(state=tk.DISABLED if running else tk.NORMAL)
            except tk.TclError:
                continue

        if running:
            self.rollback_button.configure(state=tk.DISABLED)
            self.export_button.configure(state=tk.DISABLED)
            self.run_button.configure(text="Migration Running...")
            self.progress.start(10)
        else:
            self.run_button.configure(text="Run Migration")
            self.progress.stop()

    def _handle_success(self) -> None:
        """Finish a successful run on the main thread."""
        self._set_running_state(False)
        self.rollback_button.configure(state=tk.NORMAL)
        self.export_button.configure(state=tk.NORMAL)
        self._set_status("Migration Complete", tone="success")
        self._set_phase("Migration finished successfully. Review the log, export a report, or rollback.")
        self._append_log("Migration completed successfully.")

    def _handle_failure(self, error_message: str) -> None:
        """Finish a failed run on the main thread."""
        self._set_running_state(False)
        self._set_status("Migration Failed", tone="danger")
        self._set_phase("The run stopped early. Review the activity stream for the failing step.")
        self._append_log(f"Migration error: {error_message}")
        messagebox.showerror("Migration Error", f"An error occurred during migration:\n\n{error_message}")


def main() -> None:
    """Main application entry point."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print("GUI launch failed: no graphical display is available.")
        print("Run the CLI instead: python3 cli.py --source <path> --target <path>")
        raise SystemExit(1) from exc

    APIMigrationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
