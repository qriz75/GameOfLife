# Conway's Game of Life - Python Implementation

This project is a Python implementation of John Conway's Game of Life, featuring a graphical user interface built with Tkinter.

## Features

- **Visual Simulation:** Watch the Game of Life evolve on a grid.
- **Optimized Logic:** Uses NumPy for grid operations and SciPy's convolution (if available) for efficient neighbor counting, providing good performance even on larger grids. Falls back to a manual method if SciPy is not installed.
- **Pattern Library:** Includes a library of common patterns categorized as:
  - Still Lifes
  - Oscillators
  - Spaceships
  - Guns
  - Methuselahs
- **Pattern Placement:** Select patterns from the list and place them onto the grid using a left mouse click.
- **Pattern Rotation:** Rotate the selected pattern preview 90 degrees clockwise using a right mouse click before placing.
- **Simulation Controls:**
  - Pause/Resume the simulation.
  - Reset the current run to its starting state.
  - Perform a full reset, clearing the grid.
- **Status Display:** Shows the current generation count and the simulation state (Paused, Running, Stable, Dead, Oscillating, etc.).
- **Statistics:** Displays live population count, average generation calculation time, and population stability (standard deviation).
- **Pattern Challenge Mode:** A mode where you place a pattern, and the simulation runs until it stabilizes, showing the initial and final population counts.
- **Resizable Interface:** The main grid area and the control panel can be resized.

## File Structure

- `main_app.py`: The main application entry point. Handles the Tkinter GUI setup, event handling, state management, and orchestrates the simulation and UI updates.
- `game_logic.py`: Contains the core Game of Life rules, grid initialization, and neighbor counting logic (both SciPy and manual methods).
- `gui_components.py`: Defines reusable Tkinter widgets, such as the `CollapsibleFrame` used for pattern categories and the `draw_pattern_preview` function.
- `patterns.py`: Defines the various Game of Life patterns as NumPy arrays and provides functions to access them.
- `README.md`: This file.

## Requirements

- Python 3.x
- NumPy (`pip install numpy`)
- SciPy (`pip install scipy`) - Optional, but highly recommended for performance.
- Tkinter - Usually included with standard Python installations.

## How to Run

1.  Make sure you have Python and the required libraries installed.
2.  Navigate to the project directory (`e:\Python\GameOfLife`) in your terminal.
3.  Run the main application file:
    ```bash
    python main_app.py
    ```
