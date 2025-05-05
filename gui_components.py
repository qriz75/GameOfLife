import tkinter as tk
from tkinter import ttk
import numpy as np

def draw_pattern_preview(preview_canvas, pattern_array, preview_canvas_size):
    """Draws a small preview of a pattern on a given canvas."""
    preview_canvas.delete("all") # Clear previous preview
    if pattern_array is None: return

    rows, cols = pattern_array.shape
    if rows == 0 or cols == 0: return # Skip empty patterns

    canvas_size = preview_canvas_size
    padding = 1 # Minimal padding

    # Calculate available drawing area
    available_width = canvas_size - 2 * padding
    available_height = canvas_size - 2 * padding
    if available_width <= 0 or available_height <= 0: return # Not enough space

    # Calculate cell size to fit the pattern within the available area
    cell_w = available_width / cols
    cell_h = available_height / rows
    cell_size = max(1, min(cell_w, cell_h)) # Use floor to avoid drawing outside bounds

    # Calculate total drawing dimensions and centering offset
    pattern_draw_width = cols * cell_size
    pattern_draw_height = rows * cell_size
    offset_x = padding + (available_width - pattern_draw_width) / 2
    offset_y = padding + (available_height - pattern_draw_height) / 2

    # Draw the pattern cells
    for r in range(rows):
        for c in range(cols):
            if pattern_array[r, c] == 1:
                # Calculate cell coordinates, ensuring they are integers
                x0 = int(offset_x + c * cell_size)
                y0 = int(offset_y + r * cell_size)
                x1 = int(x0 + cell_size)
                y1 = int(y0 + cell_size)
                # Ensure x1 > x0 and y1 > y0, minimum 1 pixel size
                if x1 <= x0: x1 = x0 + 1
                if y1 <= y0: y1 = y0 + 1
                preview_canvas.create_rectangle(x0, y0, x1, y1, fill="black", outline="")


class CollapsibleFrame(tk.Frame):
    """A collapsible frame widget using ttk for better styling."""
    def __init__(self, parent, title="", start_expanded=True, **kwargs):
        # Use ttk.Frame for potentially better theme integration
        super().__init__(parent, **kwargs)
        self.columnconfigure(0, weight=1) # Allow content to expand horizontally
        self.title = title
        self._expanded = tk.BooleanVar(value=start_expanded)

        # Header Frame
        # Use a subtle background for the header
        self.header_frame = tk.Frame(self, bd=1, relief="raised", bg="lightgrey")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.columnconfigure(1, weight=1) # Allow title label to expand

        # Use ttk.Button for a more modern look
        self.toggle_button = ttk.Button(self.header_frame, text="-", width=2, command=self.toggle, style="Toolbutton") # Small style
        self.toggle_button.grid(row=0, column=0, sticky="w", padx=(2,0), pady=1)

        # Use ttk.Label
        self.title_label = ttk.Label(self.header_frame, text=self.title, anchor="w", background="lightgrey")
        self.title_label.grid(row=0, column=1, sticky="ew", padx=5)

        # Content Frame (use standard tk.Frame for content)
        self.content_frame = tk.Frame(self, borderwidth=1, relief="sunken")
        # Don't grid content_frame yet, toggle() will handle it

        # Bind header click to toggle as well (more intuitive)
        self.header_frame.bind("<Button-1>", lambda e: self.toggle())
        self.title_label.bind("<Button-1>", lambda e: self.toggle())

        # Initial state update
        self.update_state()

    def toggle(self, event=None):
        """Toggles the visibility of the content frame."""
        self._expanded.set(not self._expanded.get())
        self.update_state()

    def update_state(self):
        """Updates the button text and content visibility based on _expanded state."""
        if self._expanded.get():
            # Reduced padding
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0,1))
            self.toggle_button.configure(text="-")
        else:
            # Hide content frame
            self.content_frame.grid_forget()
            self.toggle_button.configure(text="+")

    def get_content_frame(self):
        """Returns the frame where content should be placed."""
        return self.content_frame
