import os
import sys
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk


def resource_path(filename):
    """
    Works both in normal Python mode and PyInstaller EXE mode.
    If ffmpeg.exe is bundled with PyInstaller, it will be found inside _MEIPASS.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


def format_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Compress Tool by Vlad")
        self.root.geometry("900x700")
        self.root.minsize(900, 700)
        self.root.resizable(True, True)

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
        self.progress_text = tk.StringVar(value="Progress: 0%")
        self.status_text = tk.StringVar(value="Ready")

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill="both", expand=True)

        title = ttk.Label(main_frame, text="Video Compress Tool by Vlad", font=("Segoe UI", 16, "bold"))
        title.pack(pady=(0, 15))

        # Source video
        source_frame = ttk.LabelFrame(main_frame, text="Source Video", padding=10)
        source_frame.pack(fill="x", pady=5)

        ttk.Entry(source_frame, textvariable=self.input_file).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(source_frame, text="Browse", command=self.select_input).pack(side="right")

        # Output video
        output_frame = ttk.LabelFrame(main_frame, text="Output Video", padding=10)
        output_frame.pack(fill="x", pady=5)

        ttk.Entry(output_frame, textvariable=self.output_file).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(output_frame, text="Save As", command=self.select_output).pack(side="right")

        # Settings
        settings_frame = ttk.LabelFrame(main_frame, text="Compression Settings", padding=10)
        settings_frame.pack(fill="x", pady=10)

        # CRF slider
        crf_frame = ttk.Frame(settings_frame)
        crf_frame.pack(fill="x", pady=8)

        ttk.Label(crf_frame, text="CRF Quality:", width=18).pack(side="left")

        self.crf_label = ttk.Label(crf_frame, text="26", width=4)
        self.crf_label.pack(side="right")

        crf_slider = ttk.Scale(
            crf_frame,
            from_=18,
            to=35,
            orient="horizontal",
            variable=self.crf_value,
            command=self.update_crf_label
        )
        crf_slider.pack(side="left", fill="x", expand=True, padx=10)

        ttk.Label(
            settings_frame,
            text="Lower CRF = better quality and larger file. Higher CRF = smaller file and lower quality.",
            foreground="gray"
        ).pack(anchor="w", pady=(0, 5))

        # Codec dropdown
        codec_frame = ttk.Frame(settings_frame)
        codec_frame.pack(fill="x", pady=6)

        ttk.Label(codec_frame, text="Codec:", width=18).pack(side="left")
        codec_dropdown = ttk.Combobox(
            codec_frame,
            textvariable=self.codec_choice,
            values=["H.264 (libx264)", "H.265 / HEVC (libx265)"],
            state="readonly"
        )
        codec_dropdown.pack(side="left", fill="x", expand=True)

        # Resolution dropdown
        resolution_frame = ttk.Frame(settings_frame)
        resolution_frame.pack(fill="x", pady=6)

        ttk.Label(resolution_frame, text="Resolution:", width=18).pack(side="left")
        resolution_dropdown = ttk.Combobox(
            resolution_frame,
            textvariable=self.resolution_choice,
            values=["Original", "1920x1080", "1280x720", "800x600", "640x360"],
            state="readonly"
        )
        resolution_dropdown.pack(side="left", fill="x", expand=True)

        # Frame rate dropdown
        framerate_frame = ttk.Frame(settings_frame)
        framerate_frame.pack(fill="x", pady=6)

        ttk.Label(framerate_frame, text="Frame Rate:", width=18).pack(side="left")
        framerate_dropdown = ttk.Combobox(
            framerate_frame,
            textvariable=self.frame_rate_choice,
            values=["Original", "60", "30", "25"],
            state="readonly"
        )
        framerate_dropdown.pack(side="left", fill="x", expand=True)

        # Checkboxes
        options_frame = ttk.Frame(settings_frame)
        options_frame.pack(fill="x", pady=8)

        ttk.Checkbutton(options_frame, text="Keep sound", variable=self.keep_audio).pack(anchor="w")
        ttk.Checkbutton(
            options_frame,
            text="Open output folder when finished",
            variable=self.open_folder_after_finish
        ).pack(anchor="w")

        # Progress
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding=10)
        progress_frame.pack(fill="x", pady=10)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_value,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(progress_frame, textvariable=self.progress_text).pack(anchor="w")
        ttk.Label(progress_frame, textvariable=self.status_text).pack(anchor="w", pady=(5, 0))

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=15)

        self.start_button = ttk.Button(button_frame, text="Start Compression", command=self.start_compression)
        self.start_button.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.cancel_button = ttk.Button(button_frame, text="Cancel Compression", command=self.cancel_compression, state="disabled")
        self.cancel_button.pack(side="left", expand=True, fill="x", padx=(5, 0))

    def update_crf_label(self, value=None):
        self.crf_label.config(text=str(int(float(self.crf_value.get()))))

    def select_input(self):
        file = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm"),
                ("All files", "*.*")
            ]
        )

        if file:
            self.input_file.set(file)

            folder = os.path.dirname(file)
            name = os.path.splitext(os.path.basename(file))[0]
            self.output_file.set(os.path.join(folder, f"{name}_compressed.mp4"))

    def select_output(self):
        file = filedialog.asksaveasfilename(
            title="Save Compressed Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4"), ("All files", "*.*")]
        )

        if file:
            self.output_file.set(file)

    def get_codec_value(self):
        if self.codec_choice.get() == "H.265 / HEVC (libx265)":
            return "libx265"
        return "libx264"

    def validate_inputs(self):
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select a source video.")
            return False

        if not os.path.exists(self.input_file.get()):
            messagebox.showerror("Error", "Source video does not exist.")
            return False

        if not self.output_file.get():
            messagebox.showerror("Error", "Please select output file path.")
            return False

        ffmpeg_path = resource_path("ffmpeg.exe")
        if not os.path.exists(ffmpeg_path):
            messagebox.showerror(
                "Error",
                "ffmpeg.exe was not found.\n\nPut ffmpeg.exe in the same folder as this Python script before running or building EXE."
            )
            return False

        return True

    def start_compression(self):
        if self.is_compressing:
            return

        if not self.validate_inputs():
            return

        self.is_compressing = True
        self.cancel_requested = False

        self.progress_value.set(0)
        self.progress_text.set("Progress: 0%")
        self.status_text.set("Starting compression...")

        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        thread = threading.Thread(target=self.compress_video, daemon=True)
        thread.start()

    def build_ffmpeg_command(self, ffmpeg_path):
        command = [
            ffmpeg_path,
            "-y",
            "-i", self.input_file.get(),
            "-vcodec", self.get_codec_value(),
            "-crf", str(int(self.crf_value.get())),
            "-preset", "medium",
        ]

        # Resolution
        if self.resolution_choice.get() != "Original":
            width, height = self.resolution_choice.get().split("x")
            command += ["-vf", f"scale={width}:{height}"]

        # Frame rate
        if self.frame_rate_choice.get() != "Original":
            command += ["-r", self.frame_rate_choice.get()]

        # Audio
        if self.keep_audio.get():
            command += ["-acodec", "aac", "-b:a", "128k"]
        else:
            command += ["-an"]

        # FFmpeg progress output
        command += [
            "-progress", "pipe:1",
            "-nostats",
            self.output_file.get()
        ]

        return command

    def compress_video(self):
        ffmpeg_path = resource_path("ffmpeg.exe")
        command = self.build_ffmpeg_command(ffmpeg_path)

        duration_seconds = None

        try:
            startupinfo = None

            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.ffmpeg_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            # Read stderr in separate thread to find duration
            def read_stderr():
                nonlocal duration_seconds

                for line in self.ffmpeg_process.stderr:
                    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
                    if duration_match:
                        hours = float(duration_match.group(1))
                        minutes = float(duration_match.group(2))
                        seconds = float(duration_match.group(3))
                        duration_seconds = hours * 3600 + minutes * 60 + seconds

            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()

            # Read progress from stdout
            for line in self.ffmpeg_process.stdout:
                if self.cancel_requested:
                    break

                line = line.strip()

                if line.startswith("out_time_ms=") and duration_seconds:
                    try:
                        out_time_ms = int(line.split("=")[1])
                        current_seconds = out_time_ms / 1_000_000
                        percent = min((current_seconds / duration_seconds) * 100, 100)

                        self.root.after(0, self.update_progress, percent, current_seconds, duration_seconds)
                    except ValueError:
                        pass

                elif line.startswith("progress=end"):
                    self.root.after(0, self.update_progress, 100, duration_seconds or 0, duration_seconds or 0)

            return_code = self.ffmpeg_process.wait()

            if self.cancel_requested:
                self.cleanup_after_cancel()
                return

            if return_code == 0:
                self.root.after(0, self.compression_finished)
            else:
                self.root.after(0, self.compression_failed)

        except Exception as e:
            self.root.after(0, lambda: self.compression_error(str(e)))

    def update_progress(self, percent, current_seconds, duration_seconds):
        percent_int = int(percent)
        self.progress_value.set(percent)
        self.progress_text.set(f"Progress: {percent_int}%")
        self.status_text.set(f"Processing: {format_time(current_seconds)} / {format_time(duration_seconds)}")

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
            output = self.output_file.get()
            if output and os.path.exists(output):
                os.remove(output)
        except Exception:
            pass

        self.root.after(0, self.cancel_finished)

    def cancel_finished(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.progress_value.set(0)
        self.progress_text.set("Progress: 0%")
        self.status_text.set("Compression cancelled. Incomplete output file deleted.")

        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        messagebox.showinfo("Cancelled", "Compression cancelled.\nIncomplete output file was deleted.")

    def compression_finished(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.progress_value.set(100)
        self.progress_text.set("Progress: 100%")
        self.status_text.set("Compression completed successfully.")

        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        messagebox.showinfo("Success", "Video compressed successfully.")

        if self.open_folder_after_finish.get():
            output_folder = os.path.dirname(self.output_file.get())
            if os.path.exists(output_folder):
                os.startfile(output_folder)

    def compression_failed(self):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.status_text.set("Compression failed.")
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        messagebox.showerror("Error", "Compression failed. Please check the selected video and settings.")

    def compression_error(self, error_message):
        self.is_compressing = False
        self.ffmpeg_process = None

        self.status_text.set("Error.")
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        messagebox.showerror("Error", error_message)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()
