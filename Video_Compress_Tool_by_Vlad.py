import ctypes
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk


APP_NAME = "Video Compress Tool by Vlad"
APP_VERSION = "v1.1.0"

# Modern dark theme
BG = "#0B1118"
CARD = "#121B25"
CARD_ALT = "#17222E"
INPUT_BG = "#0E1720"
BORDER = "#263544"
TEXT = "#F4F7FA"
MUTED = "#92A3B5"
ACCENT = "#1687F8"
ACCENT_HOVER = "#2C96FF"
DANGER = "#B9414A"
DANGER_HOVER = "#D04B56"
DISABLED = "#344250"
SUCCESS = "#25B46B"
WARNING = "#F0A43A"


def resource_path(relative_path):
    """Return a valid resource path in Python and PyInstaller modes."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


def find_ffmpeg():
    """Find bundled ffmpeg.exe first, then fall back to the system PATH."""
    bundled_ffmpeg = resource_path("ffmpeg.exe")
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg

    return shutil.which("ffmpeg")


def format_time(seconds):
    seconds = max(0, int(seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def apply_windows_dark_title_bar(window):
    """Enable a dark native title bar on supported Windows 10/11 versions."""
    if os.name != "nt":
        return

    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        enabled = ctypes.c_int(1)

        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
            ctypes.byref(enabled),
            ctypes.sizeof(enabled),
        )

        if result != 0:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                19,
                ctypes.byref(enabled),
                ctypes.sizeof(enabled),
            )

        ctypes.windll.user32.SetWindowPos(
            hwnd,
            0,
            0,
            0,
            0,
            0,
            0x0001 | 0x0002 | 0x0020,
        )
    except Exception:
        pass


class DarkDialog:
    """Reusable modal dialog styled to match the application's dark UI."""

    TYPE_STYLES = {
        "success": ("✓", SUCCESS),
        "info": ("i", ACCENT),
        "warning": ("!", WARNING),
        "error": ("×", DANGER_HOVER),
        "question": ("?", ACCENT),
    }

    def __init__(
        self,
        parent,
        title,
        message,
        dialog_type="info",
        question=False,
        confirm_text="Yes",
        cancel_text="No",
    ):
        self.parent = parent
        self.result = False
        self.question = question

        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.title(title)
        self.window.configure(bg=BG)
        self.window.resizable(False, False)
        self.window.transient(parent)

        self._set_icon()
        self._build_content(
            title=title,
            message=message,
            dialog_type=dialog_type,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
        )

        self.window.protocol("WM_DELETE_WINDOW", self._cancel)
        self.window.bind("<Escape>", lambda _event: self._cancel())
        self.window.bind(
            "<Return>",
            lambda _event: self._confirm(),
        )

        self._show_centered()

    def _set_icon(self):
        icon_candidates = [
            resource_path(os.path.join("assets", "vcompress.ico")),
            resource_path("vcompress.ico"),
        ]

        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    self.window.iconbitmap(default=icon_path)
                    break
                except tk.TclError:
                    continue

    def _build_content(
        self,
        title,
        message,
        dialog_type,
        confirm_text,
        cancel_text,
    ):
        symbol, accent_color = self.TYPE_STYLES.get(
            dialog_type,
            self.TYPE_STYLES["info"],
        )

        outer = tk.Frame(
            self.window,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        outer.pack(fill="both", expand=True)

        tk.Frame(
            outer,
            bg=accent_color,
            height=4,
        ).pack(fill="x", side="top")

        content = tk.Frame(outer, bg=CARD, padx=24, pady=22)
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(1, weight=1)

        icon = tk.Label(
            content,
            text=symbol,
            bg=accent_color,
            fg="#FFFFFF",
            font=("Segoe UI", 17, "bold"),
            width=2,
            height=1,
            bd=0,
            padx=4,
            pady=3,
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 16))

        tk.Label(
            content,
            text=title,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

        tk.Label(
            content,
            text=message,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=350,
        ).grid(row=1, column=1, sticky="ew", pady=(7, 0))

        button_bar = tk.Frame(outer, bg=CARD_ALT, padx=20, pady=14)
        button_bar.pack(fill="x", side="bottom")

        if self.question:
            cancel_button = tk.Button(
                button_bar,
                text=cancel_text,
                command=self._cancel,
                bg=CARD_ALT,
                fg=TEXT,
                activebackground="#213040",
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                padx=22,
                pady=8,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2",
            )
            cancel_button.pack(side="right")

        confirm_button = tk.Button(
            button_bar,
            text=confirm_text if self.question else "OK",
            command=self._confirm,
            bg=accent_color if not self.question else ACCENT,
            fg="#FFFFFF",
            activebackground=ACCENT_HOVER,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=24,
            pady=8,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        confirm_button.pack(side="right", padx=(0, 10) if self.question else 0)
        confirm_button.focus_set()

    def _show_centered(self):
        self.window.update_idletasks()

        width = max(460, self.window.winfo_reqwidth())
        height = max(220, self.window.winfo_reqheight())

        self.parent.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        x = parent_x + max(0, (parent_width - width) // 2)
        y = parent_y + max(0, (parent_height - height) // 2)

        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        self.window.after(0, lambda: apply_windows_dark_title_bar(self.window))
        self.window.grab_set()
        self.parent.wait_window(self.window)

    def _confirm(self):
        self.result = True
        self._close()

    def _cancel(self):
        self.result = False
        self._close()

    def _close(self):
        try:
            self.window.grab_release()
        except tk.TclError:
            pass
        self.window.destroy()


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("960x780")
        self.root.minsize(940, 760)
        self.root.configure(bg=BG)

        self.set_app_identity()
        self.configure_styles()

        self.ffmpeg_process = None
        self.is_compressing = False
        self.cancel_requested = False

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()

        self.crf_value = tk.IntVar(value=26)
        self.codec_choice = tk.StringVar(value="H.264 (libx264)")
        self.resolution_choice = tk.StringVar(value="Original")
        self.frame_rate_choice = tk.StringVar(value="Original")

        self.keep_audio = tk.BooleanVar(value=True)
        self.open_folder_after_finish = tk.BooleanVar(value=True)

        self.progress_value = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="0%")
        self.status_text = tk.StringVar(value="Ready to compress")

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_app_identity(self):
        """Set the app icon, taskbar identity, and dark Windows title bar."""
        if os.name == "nt":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "Vlad.VideoCompressTool.1.1"
                )
            except Exception:
                pass

        icon_candidates = [
            resource_path(os.path.join("assets", "vcompress.ico")),
            resource_path("vcompress.ico"),
        ]

        for icon_path in icon_candidates:
            if os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(default=icon_path)
                    break
                except tk.TclError:
                    continue

        # Apply after Tk has created the native Windows window.
        self.root.after(0, self.enable_dark_title_bar)

    def enable_dark_title_bar(self):
        """Apply the shared dark native title-bar styling."""
        apply_windows_dark_title_bar(self.root)

    def show_dialog(self, title, message, dialog_type="info"):
        """Display a branded dark modal dialog."""
        dialog = DarkDialog(
            self.root,
            title=title,
            message=message,
            dialog_type=dialog_type,
        )
        return dialog.result

    def ask_question(
        self,
        title,
        message,
        dialog_type="question",
        confirm_text="Yes",
        cancel_text="No",
    ):
        """Display a branded dark confirmation dialog and return the answer."""
        dialog = DarkDialog(
            self.root,
            title=title,
            message=message,
            dialog_type=dialog_type,
            question=True,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
        )
        return dialog.result

    def configure_styles(self):
        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 10))

        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("CardAlt.TFrame", background=CARD_ALT)

        style.configure(
            "Title.TLabel",
            background=BG,
            foreground=TEXT,
            font=("Segoe UI", 21, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=BG,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Version.TLabel",
            background=CARD_ALT,
            foreground=ACCENT_HOVER,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 5),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "CardText.TLabel",
            background=CARD,
            foreground=TEXT,
        )
        style.configure(
            "Muted.TLabel",
            background=CARD,
            foreground=MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background=CARD,
            foreground=MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "ProgressText.TLabel",
            background=CARD,
            foreground=ACCENT_HOVER,
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "Modern.TEntry",
            fieldbackground=INPUT_BG,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            insertcolor=TEXT,
            padding=(10, 9),
            relief="flat",
        )
        style.map(
            "Modern.TEntry",
            bordercolor=[("focus", ACCENT), ("!focus", BORDER)],
            lightcolor=[("focus", ACCENT), ("!focus", BORDER)],
            darkcolor=[("focus", ACCENT), ("!focus", BORDER)],
        )

        style.configure(
            "Modern.TCombobox",
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(9, 7),
            relief="flat",
        )
        style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", INPUT_BG)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", INPUT_BG)],
            selectforeground=[("readonly", TEXT)],
            bordercolor=[("focus", ACCENT), ("!focus", BORDER)],
            lightcolor=[("focus", ACCENT), ("!focus", BORDER)],
            darkcolor=[("focus", ACCENT), ("!focus", BORDER)],
        )

        style.configure(
            "Modern.TCheckbutton",
            background=CARD,
            foreground=TEXT,
            indicatorcolor=INPUT_BG,
            padding=(0, 4),
        )
        style.map(
            "Modern.TCheckbutton",
            background=[("active", CARD)],
            foreground=[("disabled", MUTED), ("!disabled", TEXT)],
            indicatorcolor=[
                ("selected", ACCENT),
                ("pressed", ACCENT_HOVER),
                ("!selected", INPUT_BG),
            ],
        )

        style.configure(
            "Primary.TButton",
            background=ACCENT,
            foreground="#FFFFFF",
            borderwidth=0,
            focuscolor=ACCENT,
            padding=(18, 11),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", ACCENT_HOVER),
                ("pressed", "#0874DD"),
                ("disabled", DISABLED),
            ],
            foreground=[("disabled", "#7F8B97"), ("!disabled", "#FFFFFF")],
        )

        style.configure(
            "Secondary.TButton",
            background=CARD_ALT,
            foreground=TEXT,
            borderwidth=1,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            focuscolor=CARD_ALT,
            padding=(14, 9),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("active", "#213040"),
                ("pressed", "#192633"),
                ("disabled", CARD),
            ],
            foreground=[("disabled", "#667482"), ("!disabled", TEXT)],
            bordercolor=[("active", ACCENT), ("!active", BORDER)],
            lightcolor=[("active", ACCENT), ("!active", BORDER)],
            darkcolor=[("active", ACCENT), ("!active", BORDER)],
        )

        style.configure(
            "Danger.TButton",
            background=DANGER,
            foreground="#FFFFFF",
            borderwidth=0,
            focuscolor=DANGER,
            padding=(18, 11),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[
                ("active", DANGER_HOVER),
                ("pressed", "#9F343D"),
                ("disabled", DISABLED),
            ],
            foreground=[("disabled", "#7F8B97"), ("!disabled", "#FFFFFF")],
        )

        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=INPUT_BG,
            background=ACCENT,
            bordercolor=INPUT_BG,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=14,
        )

        # Dropdown list colors
        self.root.option_add("*TCombobox*Listbox.background", INPUT_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")

    def create_widgets(self):
        main = ttk.Frame(self.root, style="App.TFrame", padding=(24, 20, 24, 20))
        main.grid(row=0, column=0, sticky="nsew")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        self.create_header(main)
        self.create_files_card(main)
        self.create_settings_card(main)
        self.create_progress_card(main)
        self.create_action_bar(main)

    def create_header(self, parent):
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(1, weight=1)

        logo = tk.Label(
            header,
            text="V",
            bg=ACCENT,
            fg="#FFFFFF",
            font=("Segoe UI", 18, "bold"),
            width=2,
            height=1,
            bd=0,
            padx=4,
            pady=3,
        )
        logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        ttk.Label(
            header,
            text="Video Compress Tool",
            style="Title.TLabel",
        ).grid(row=0, column=1, sticky="sw")

        ttk.Label(
            header,
            text="Fast and simple FFmpeg video compression for Windows",
            style="Subtitle.TLabel",
        ).grid(row=1, column=1, sticky="nw", pady=(2, 0))

        ttk.Label(
            header,
            text=APP_VERSION,
            style="Version.TLabel",
        ).grid(row=0, column=2, rowspan=2, sticky="e")

    def create_files_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(1, weight=1)

        ttk.Label(card, text="Video files", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        ttk.Label(card, text="Source video", style="CardText.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 14), pady=6
        )
        ttk.Entry(
            card,
            textvariable=self.input_file,
            style="Modern.TEntry",
        ).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Button(
            card,
            text="Browse",
            style="Secondary.TButton",
            command=self.select_input,
        ).grid(row=1, column=2, sticky="e", padx=(10, 0), pady=6)

        ttk.Label(card, text="Output video", style="CardText.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 14), pady=6
        )
        ttk.Entry(
            card,
            textvariable=self.output_file,
            style="Modern.TEntry",
        ).grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Button(
            card,
            text="Save As",
            style="Secondary.TButton",
            command=self.select_output,
        ).grid(row=2, column=2, sticky="e", padx=(10, 0), pady=6)

    def create_settings_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=2, column=0, sticky="nsew", pady=(0, 14))

        for column in range(3):
            card.grid_columnconfigure(column, weight=1)

        ttk.Label(card, text="Compression settings", style="SectionTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        # CRF
        quality_header = ttk.Frame(card, style="Card.TFrame")
        quality_header.grid(row=1, column=0, columnspan=3, sticky="ew")
        quality_header.grid_columnconfigure(1, weight=1)

        ttk.Label(
            quality_header,
            text="CRF quality",
            style="CardText.TLabel",
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            quality_header,
            text="Lower = higher quality  •  Higher = smaller file",
            style="Muted.TLabel",
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))

        self.crf_badge = tk.Label(
            quality_header,
            text="26",
            bg=ACCENT,
            fg="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            width=4,
            padx=6,
            pady=3,
        )
        self.crf_badge.grid(row=0, column=2, sticky="e")

        self.crf_slider = ttk.Scale(
            card,
            from_=18,
            to=35,
            orient="horizontal",
            variable=self.crf_value,
            command=self.update_crf_label,
        )
        self.crf_slider.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(12, 20),
        )

        # Three setting columns
        ttk.Label(card, text="Codec", style="Muted.TLabel").grid(
            row=3, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Label(card, text="Resolution", style="Muted.TLabel").grid(
            row=3, column=1, sticky="w", padx=10
        )
        ttk.Label(card, text="Frame rate", style="Muted.TLabel").grid(
            row=3, column=2, sticky="w", padx=(10, 0)
        )

        ttk.Combobox(
            card,
            textvariable=self.codec_choice,
            values=["H.264 (libx264)", "H.265 / HEVC (libx265)"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=4, column=0, sticky="ew", padx=(0, 10), pady=(6, 16))

        ttk.Combobox(
            card,
            textvariable=self.resolution_choice,
            values=["Original", "1920x1080", "1280x720", "800x600", "640x360"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=4, column=1, sticky="ew", padx=10, pady=(6, 16))

        ttk.Combobox(
            card,
            textvariable=self.frame_rate_choice,
            values=["Original", "60", "30", "25"],
            state="readonly",
            style="Modern.TCombobox",
        ).grid(row=4, column=2, sticky="ew", padx=(10, 0), pady=(6, 16))

        separator = ttk.Separator(card, orient="horizontal")
        separator.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        options = ttk.Frame(card, style="Card.TFrame")
        options.grid(row=6, column=0, columnspan=3, sticky="ew")

        ttk.Checkbutton(
            options,
            text="Keep sound",
            variable=self.keep_audio,
            style="Modern.TCheckbutton",
        ).pack(side="left", padx=(0, 28))

        ttk.Checkbutton(
            options,
            text="Open output folder when finished",
            variable=self.open_folder_after_finish,
            style="Modern.TCheckbutton",
        ).pack(side="left")

        ttk.Label(
            card,
            text="Tip: H.264 offers the best compatibility. H.265 usually creates smaller files but may require HEVC support.",
            style="Muted.TLabel",
        ).grid(row=7, column=0, columnspan=3, sticky="w", pady=(12, 0))

    def create_progress_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)

        heading = ttk.Frame(card, style="Card.TFrame")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        heading.grid_columnconfigure(0, weight=1)

        ttk.Label(heading, text="Progress", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            heading,
            textvariable=self.progress_text,
            style="ProgressText.TLabel",
        ).grid(row=0, column=1, sticky="e")

        self.progress_bar = ttk.Progressbar(
            card,
            variable=self.progress_value,
            maximum=100,
            mode="determinate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(
            card,
            textvariable=self.status_text,
            style="Status.TLabel",
        ).grid(row=2, column=0, sticky="w")

    def create_action_bar(self, parent):
        action_bar = ttk.Frame(parent, style="App.TFrame")
        action_bar.grid(row=4, column=0, sticky="ew")
        action_bar.grid_columnconfigure(0, weight=1)
        action_bar.grid_columnconfigure(1, weight=1)

        self.start_button = ttk.Button(
            action_bar,
            text="Start Compression",
            style="Primary.TButton",
            command=self.start_compression,
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 7))

        self.cancel_button = ttk.Button(
            action_bar,
            text="Cancel Compression",
            style="Danger.TButton",
            command=self.cancel_compression,
            state="disabled",
        )
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=(7, 0))

    def update_crf_label(self, _value=None):
        value = int(float(self.crf_value.get()))
        self.crf_badge.config(text=str(value))

    def select_input(self):
        selected_file = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
                ("All files", "*.*"),
            ],
        )

        if selected_file:
            self.input_file.set(selected_file)

            folder = os.path.dirname(selected_file)
            name = os.path.splitext(os.path.basename(selected_file))[0]
            self.output_file.set(os.path.join(folder, f"{name}_compressed.mp4"))

    def select_output(self):
        selected_file = filedialog.asksaveasfilename(
            title="Save Compressed Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4"), ("All files", "*.*")],
        )

        if selected_file:
            self.output_file.set(selected_file)

    def get_codec_value(self):
        if self.codec_choice.get() == "H.265 / HEVC (libx265)":
            return "libx265"
        return "libx264"

    def validate_inputs(self):
        input_path = self.input_file.get().strip()
        output_path = self.output_file.get().strip()

        if not input_path:
            self.show_dialog("Missing source", "Please select a source video.", "warning")
            return False

        if not os.path.isfile(input_path):
            self.show_dialog("Invalid source", "The selected source video does not exist.", "error")
            return False

        if not output_path:
            self.show_dialog("Missing output", "Please select an output file path.", "warning")
            return False

        if os.path.abspath(input_path) == os.path.abspath(output_path):
            self.show_dialog(
                "Invalid output",
                "The output file must be different from the source video.",
                "error",
            )
            return False

        output_folder = os.path.dirname(output_path) or os.getcwd()
        if not os.path.isdir(output_folder):
            self.show_dialog("Invalid output", "The selected output folder does not exist.", "error")
            return False

        if not find_ffmpeg():
            self.show_dialog(
                "FFmpeg not found",
                "ffmpeg.exe was not found.\n\n"
                "Place ffmpeg.exe next to the Python script, bundle it with PyInstaller, "
                "or add FFmpeg to the Windows PATH.",
                "error",
            )
            return False

        return True

    def start_compression(self):
        if self.is_compressing or not self.validate_inputs():
            return

        self.is_compressing = True
        self.cancel_requested = False

        self.progress_value.set(0)
        self.progress_text.set("0%")
        self.status_text.set("Starting compression...")

        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        threading.Thread(target=self.compress_video, daemon=True).start()

    def build_ffmpeg_command(self, ffmpeg_path):
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            self.input_file.get(),
            "-vcodec",
            self.get_codec_value(),
            "-crf",
            str(int(self.crf_value.get())),
            "-preset",
            "medium",
        ]

        if self.resolution_choice.get() != "Original":
            width, height = self.resolution_choice.get().split("x")
            command += ["-vf", f"scale={width}:{height}"]

        if self.frame_rate_choice.get() != "Original":
            command += ["-r", self.frame_rate_choice.get()]

        if self.keep_audio.get():
            command += ["-acodec", "aac", "-b:a", "128k"]
        else:
            command += ["-an"]

        command += [
            "-progress",
            "pipe:1",
            "-nostats",
            self.output_file.get(),
        ]

        return command

    def compress_video(self):
        ffmpeg_path = find_ffmpeg()
        command = self.build_ffmpeg_command(ffmpeg_path)
        duration_seconds = None

        try:
            startupinfo = None
            creationflags = 0

            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            self.ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=creationflags,
                encoding="utf-8",
                errors="replace",
            )

            def read_stderr():
                nonlocal duration_seconds

                if not self.ffmpeg_process or not self.ffmpeg_process.stderr:
                    return

                for line in self.ffmpeg_process.stderr:
                    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
                    if match:
                        hours = float(match.group(1))
                        minutes = float(match.group(2))
                        seconds = float(match.group(3))
                        duration_seconds = hours * 3600 + minutes * 60 + seconds

            threading.Thread(target=read_stderr, daemon=True).start()

            if self.ffmpeg_process.stdout:
                for line in self.ffmpeg_process.stdout:
                    if self.cancel_requested:
                        break

                    line = line.strip()

                    if line.startswith("out_time_ms=") and duration_seconds:
                        try:
                            out_time_ms = int(line.split("=", 1)[1])
                            current_seconds = out_time_ms / 1_000_000
                            percent = min(
                                (current_seconds / duration_seconds) * 100,
                                100,
                            )
                            self.root.after(
                                0,
                                self.update_progress,
                                percent,
                                current_seconds,
                                duration_seconds,
                            )
                        except (ValueError, ZeroDivisionError):
                            pass

                    elif line == "progress=end":
                        self.root.after(
                            0,
                            self.update_progress,
                            100,
                            duration_seconds or 0,
                            duration_seconds or 0,
                        )

            return_code = self.ffmpeg_process.wait()

            if self.cancel_requested:
                self.cleanup_after_cancel()
            elif return_code == 0:
                self.root.after(0, self.compression_finished)
            else:
                self.root.after(0, self.compression_failed)

        except Exception as error:
            self.root.after(0, self.compression_error, str(error))

    def update_progress(self, percent, current_seconds, duration_seconds):
        percent_int = int(percent)
        self.progress_value.set(percent)
        self.progress_text.set(f"{percent_int}%")
        self.status_text.set(
            f"Processing  {format_time(current_seconds)}  /  {format_time(duration_seconds)}"
        )

    def cancel_compression(self):
        if not self.is_compressing or not self.ffmpeg_process:
            return

        self.cancel_requested = True
        self.status_text.set("Cancelling compression...")

        try:
            self.ffmpeg_process.terminate()

            try:
                self.ffmpeg_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
        except Exception:
            pass

    def cleanup_after_cancel(self):
        try:
            output_path = self.output_file.get()
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass

        self.root.after(0, self.cancel_finished)

    def cancel_finished(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.progress_value.set(0)
        self.progress_text.set("0%")
        self.status_text.set("Compression cancelled. Incomplete output deleted.")

        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        self.show_dialog(
            "Compression cancelled",
            "Compression was cancelled and the incomplete output file was deleted.",
            "info",
        )

    def compression_finished(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.progress_value.set(100)
        self.progress_text.set("100%")
        self.status_text.set("Compression completed successfully.")

        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        self.show_dialog("Compression complete", "Video compressed successfully.", "success")

        if self.open_folder_after_finish.get():
            output_folder = os.path.dirname(self.output_file.get())
            if output_folder and os.path.exists(output_folder):
                if os.name == "nt":
                    os.startfile(output_folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", output_folder])
                else:
                    subprocess.Popen(["xdg-open", output_folder])

    def compression_failed(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.status_text.set("Compression failed.")
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        self.show_dialog(
            "Compression failed",
            "Compression failed. Please check the selected video and settings.",
            "error",
        )

    def compression_error(self, error_message):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.status_text.set("Unexpected error.")
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        self.show_dialog("Unexpected error", error_message, "error")

    def on_close(self):
        if self.is_compressing:
            should_close = self.ask_question(
                "Compression in progress",
                "Compression is still running. Cancel it and close the application?",
                dialog_type="warning",
                confirm_text="Cancel and close",
                cancel_text="Keep running",
            )
            if not should_close:
                return

            self.cancel_requested = True
            try:
                if self.ffmpeg_process:
                    self.ffmpeg_process.terminate()
            except Exception:
                pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()
