"""
YouTube Transcript Viewer
A simple application to view YouTube video transcripts.
"""

import json
import re
import threading
import urllib.request
import urllib.error
import customtkinter as ctk
from youtube_transcript_api import YouTubeTranscriptApi

from constants import APP_VERSION, APP_UPDATE
from components.video_thumbnail_frame import (
    THUMBNAIL_MAX_HEIGHT,
    THUMBNAIL_MAX_WIDTH,
    VideoThumbnailFrame,
)


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
        self._autopaste_clipboard_url()

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
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=12)

        # Frame for URL and button
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.pack(fill="x", pady=(0, 10))

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

        # Frame for video info (title and author)
        self.video_info_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.video_info_frame.pack(fill="x", pady=(0, 8))

        self.thumbnail_widget = VideoThumbnailFrame(
            self.video_info_frame,
            width=THUMBNAIL_MAX_WIDTH,
            height=THUMBNAIL_MAX_HEIGHT
        )
        self.thumbnail_widget.pack(side="left", padx=(0, 12), anchor="n")

        self.video_meta_frame = ctk.CTkFrame(self.video_info_frame, fg_color="transparent")
        self.video_meta_frame.pack(side="left", fill="x", expand=True, anchor="n")

        # Video title label
        self.video_title_label = ctk.CTkLabel(
            self.video_meta_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=420,
            justify="left"
        )
        self.video_title_label.pack(anchor="w")

        # Video author label
        self.video_author_label = ctk.CTkLabel(
            self.video_meta_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        self.video_author_label.pack(anchor="w")

        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(anchor="w", pady=(0, 4))

        # Text area for transcript
        self.transcript_textbox = ctk.CTkTextbox(
            self.main_frame,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.transcript_textbox.pack(fill="both", expand=True, pady=(0, 8))
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

        # Status bar at the bottom
        self.status_bar = ctk.CTkFrame(self, height=25, fg_color="transparent")
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=(0, 5))

        self.version_label = ctk.CTkLabel(
            self.status_bar,
            text=f"Version {APP_VERSION} | Last update: {APP_UPDATE}",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.version_label.pack(side="right")

        # Bind Enter key
        self.url_entry.bind("<Return>", lambda e: self._on_load_clicked())
        self.video_info_frame.bind("<Configure>", self._on_video_info_resized)

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

    def _autopaste_clipboard_url(self):
        """Autofill input with clipboard URL when it contains a valid YouTube link."""
        try:
            clipboard_text = self.clipboard_get().strip()
        except Exception:
            return

        if not clipboard_text:
            return

        if not self._extract_video_id(clipboard_text):
            return

        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, clipboard_text)

    def _set_ui_state(self, enabled: bool):
        """Enable or disable UI elements."""
        state = "normal" if enabled else "disabled"
        self.url_entry.configure(state=state)
        self.load_button.configure(state=state)

    def _on_video_info_resized(self, _event=None):
        """Keep title wrapping reasonable next to fixed thumbnail size."""
        frame_width = self.video_info_frame.winfo_width()
        available_width = frame_width - THUMBNAIL_MAX_WIDTH - 24
        self.video_title_label.configure(wraplength=max(120, available_width))

    def _update_video_info(self, title: str = "", author: str = ""):
        """Update the video title and author labels."""
        self.video_title_label.configure(text=title)
        self.video_author_label.configure(text=f"by {author}" if author else "")

    def _fetch_video_info(self, video_id: str) -> tuple[str, str, float | None]:
        """Fetch video title, author, and thumbnail aspect ratio from oEmbed API."""
        try:
            url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                thumbnail_width = data.get("thumbnail_width")
                thumbnail_height = data.get("thumbnail_height")
                thumbnail_ratio = None
                if isinstance(thumbnail_width, (int, float)) and isinstance(thumbnail_height, (int, float)) and thumbnail_height > 0:
                    thumbnail_ratio = thumbnail_width / thumbnail_height
                return data.get("title", ""), data.get("author_name", ""), thumbnail_ratio
        except Exception:
            return "", "", None

    def _fetch_thumbnail_data(self, video_id: str) -> bytes:
        """Fetch thumbnail image bytes with fallback URLs."""
        thumbnail_urls = [
            f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        ]

        for thumbnail_url in thumbnail_urls:
            try:
                with urllib.request.urlopen(thumbnail_url, timeout=10) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "image" not in content_type.lower():
                        continue
                    data = response.read()
                    if data:
                        return data
            except Exception:
                continue

        raise RuntimeError("Thumbnail unavailable")

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
            self.thumbnail_widget.reset()
            return

        video_id = self._extract_video_id(url)

        if not video_id:
            self._update_status("Invalid URL. Please enter a valid YouTube link.", is_error=True)
            self.thumbnail_widget.reset()
            return

        # Disable UI and start loading
        self._set_ui_state(False)
        self._update_status("Loading transcript...")
        self._display_transcript("")
        self._update_video_info("", "")
        self.thumbnail_widget.set_loading()

        # Run in background to avoid blocking the UI
        thread = threading.Thread(target=self._fetch_transcript, args=(video_id,))
        thread.daemon = True
        thread.start()

    def _fetch_transcript(self, video_id: str):
        """Fetch the transcript in a separate thread."""
        try:
            # Fetch video info (title and author)
            title, author, thumbnail_ratio = self._fetch_video_info(video_id)
            self.after(0, self._update_video_info, title, author)

            try:
                thumbnail_data = self._fetch_thumbnail_data(video_id)
                self.after(0, self.thumbnail_widget.set_image, thumbnail_data, thumbnail_ratio)
            except Exception:
                self.after(0, self.thumbnail_widget.set_error, "Thumbnail unavailable")

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

            # Keep API snippet boundaries so transcript remains readable.
            lines = [entry.text.strip() for entry in transcript_data if entry.text and entry.text.strip()]
            text = "\n".join(lines)

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
