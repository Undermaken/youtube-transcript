"""Reusable fixed-size thumbnail widget for YouTube metadata."""

import io

import customtkinter as ctk
from PIL import Image, UnidentifiedImageError


THUMBNAIL_MAX_WIDTH = 150
THUMBNAIL_MAX_HEIGHT = 150


class VideoThumbnailFrame(ctk.CTkFrame):
    """Fixed-size thumbnail widget with loading and error states."""

    def __init__(self, master, width: int = THUMBNAIL_MAX_WIDTH, height: int = THUMBNAIL_MAX_HEIGHT):
        super().__init__(master, width=width, height=height, corner_radius=8)
        self._width = width
        self._height = height
        self._ctk_image = None

        self.pack_propagate(False)
        self.grid_propagate(False)

        self._content_label = ctk.CTkLabel(
            self,
            text="",
            width=width,
            height=height,
            anchor="center",
            justify="center",
            wraplength=width - 20
        )
        self._content_label.pack(fill="both", expand=True)

        self.reset()

    def reset(self):
        """Reset to idle placeholder state."""
        self._ctk_image = None
        self._content_label.configure(text="", image=None, text_color="gray")

    def set_loading(self):
        """Show loading state."""
        self._ctk_image = None
        self._content_label.configure(text="Loading thumbnail...", image=None, text_color="gray")

    def set_error(self, message: str = "Thumbnail unavailable"):
        """Show a short non-blocking error."""
        self._ctk_image = None
        self._content_label.configure(text=message, image=None, text_color="#e67e22")

    def _get_size_from_ratio(self, aspect_ratio: float | None) -> tuple[int, int]:
        """Compute target bounds from metadata ratio within max thumbnail area."""
        if aspect_ratio is None or aspect_ratio <= 0:
            return self._width, self._height

        if aspect_ratio >= 1:
            width = self._width
            height = max(1, round(width / aspect_ratio))
            if height > self._height:
                height = self._height
                width = max(1, round(height * aspect_ratio))
            return width, height

        height = self._height
        width = max(1, round(height * aspect_ratio))
        if width > self._width:
            width = self._width
            height = max(1, round(width / aspect_ratio))
        return width, height

    def set_image(self, image_data: bytes, aspect_ratio: float | None = None):
        """Decode, resize, and display image bytes."""
        try:
            image = Image.open(io.BytesIO(image_data))
            image = image.convert("RGB")
            resampling = getattr(Image, "Resampling", Image)
            ratio = aspect_ratio
            if ratio is None and image.height > 0:
                ratio = image.width / image.height
            target_size = self._get_size_from_ratio(ratio)
            image.thumbnail(target_size, resampling.LANCZOS)

            self._ctk_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=image.size
            )
            self._content_label.configure(text="", image=self._ctk_image)
        except (UnidentifiedImageError, OSError):
            self.set_error()
