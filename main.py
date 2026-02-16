"""
YouTube Transcript Viewer
A simple application to view YouTube video transcripts.
"""

import re
import threading
import customtkinter as ctk
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeTranscriptApp(ctk.CTk):
    """Main application for viewing YouTube transcripts."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("YouTube Transcript Viewer")
        self.geometry("800x600")
        self.minsize(600, 400)

        # Theme
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self._setup_ui()
        self._center_window()

        # Bring window to front
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_ui(self):
        """Set up the user interface."""
        # Main frame with padding
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="YouTube Transcript Viewer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(0, 20))

        # Frame for URL and button
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.pack(fill="x", pady=(0, 15))

        # URL Label
        self.url_label = ctk.CTkLabel(
            self.input_frame,
            text="YouTube Video URL:",
            font=ctk.CTkFont(size=14)
        )
        self.url_label.pack(anchor="w", pady=(0, 5))

        # Frame for entry and button on the same row
        self.url_button_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.url_button_frame.pack(fill="x")

        # URL Entry
        self.url_entry = ctk.CTkEntry(
            self.url_button_frame,
            placeholder_text="Paste your YouTube video link here...",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Pulsante Load
        self.load_button = ctk.CTkButton(
            self.url_button_frame,
            text="Load Transcript",
            command=self._on_load_clicked,
            height=40,
            width=140,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.load_button.pack(side="right")

        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(anchor="w", pady=(0, 5))

        # Text area for transcript
        self.transcript_textbox = ctk.CTkTextbox(
            self.main_frame,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.transcript_textbox.pack(fill="both", expand=True, pady=(0, 10))
        self.transcript_textbox.configure(state="disabled")

        # Copy button
        self.copy_button = ctk.CTkButton(
            self.main_frame,
            text="Copy to Clipboard",
            command=self._on_copy_clicked,
            height=36,
            width=160,
            font=ctk.CTkFont(size=13)
        )
        self.copy_button.pack(anchor="e")

        # Bind Enter key
        self.url_entry.bind("<Return>", lambda e: self._on_load_clicked())

    def _extract_video_id(self, url: str) -> str | None:
        """Extract the video ID from a YouTube URL."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If input is already a video ID (11 characters)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url.strip()):
            return url.strip()

        return None

    def _set_ui_state(self, enabled: bool):
        """Enable or disable UI elements."""
        state = "normal" if enabled else "disabled"
        self.url_entry.configure(state=state)
        self.load_button.configure(state=state)

    def _update_status(self, message: str, is_error: bool = False, is_success: bool = False):
        """Update the status message."""
        if is_error:
            color = "#e74c3c"
        elif is_success:
            color = "#27ae60"
        else:
            color = "gray"
        self.status_label.configure(text=message, text_color=color)

    def _display_transcript(self, text: str):
        """Display the transcript in the text area."""
        self.transcript_textbox.configure(state="normal")
        self.transcript_textbox.delete("1.0", "end")
        self.transcript_textbox.insert("1.0", text)
        self.transcript_textbox.configure(state="disabled")

    def _on_copy_clicked(self):
        """Handler for Copy button click."""
        self.transcript_textbox.configure(state="normal")
        text = self.transcript_textbox.get("1.0", "end").strip()
        self.transcript_textbox.configure(state="disabled")

        if not text:
            self._update_status("No transcript to copy.", is_error=True)
            return

        self.clipboard_clear()
        self.clipboard_append(text)
        self._update_status("✓ Transcript copied to clipboard!", is_success=True)

    def _on_load_clicked(self):
        """Handler for Load button click."""
        url = self.url_entry.get().strip()

        if not url:
            self._update_status("Please enter a valid URL.", is_error=True)
            return

        video_id = self._extract_video_id(url)

        if not video_id:
            self._update_status("Invalid URL. Please enter a valid YouTube link.", is_error=True)
            return

        # Disable UI and start loading
        self._set_ui_state(False)
        self._update_status("Loading transcript...")
        self._display_transcript("")

        # Run in background to avoid blocking the UI
        thread = threading.Thread(target=self._fetch_transcript, args=(video_id,))
        thread.daemon = True
        thread.start()

    def _fetch_transcript(self, video_id: str):
        """Fetch the transcript in a separate thread."""
        try:
            # Create API instance
            ytt_api = YouTubeTranscriptApi()

            # Try Italian first, then English, then any available language
            transcript_list = ytt_api.list(video_id)

            transcript = None
            try:
                transcript = transcript_list.find_transcript(['en'])
            except Exception:
                # Get the first available transcript
                for t in transcript_list:
                    transcript = t
                    break

            if transcript is None:
                self.after(0, self._on_fetch_error, "No transcript available for this video.")
                return

            transcript_data = transcript.fetch()

            # Extract only the text and join as continuous text
            lines = [entry.text for entry in transcript_data]
            text = " ".join(lines)

            self.after(0, self._on_fetch_success, text)

        except Exception as e:
            error_msg = str(e)
            if "disabled" in error_msg.lower():
                error_msg = "Transcripts are disabled for this video."
            elif "not found" in error_msg.lower() or "404" in error_msg:
                error_msg = "Video not found. Please check the URL."
            else:
                error_msg = f"Loading error: {error_msg}"

            self.after(0, self._on_fetch_error, error_msg)

    def _on_fetch_success(self, text: str):
        """Callback for successful fetch."""
        self._display_transcript(text)
        self._update_status("✓ Transcript loaded successfully!", is_success=True)
        self._set_ui_state(True)

    def _on_fetch_error(self, error: str):
        """Callback for fetch errors."""
        self._update_status(error, is_error=True)
        self._set_ui_state(True)


def main():
    """Entry point dell'applicazione."""
    app = YouTubeTranscriptApp()
    app.mainloop()


if __name__ == "__main__":
    main()

