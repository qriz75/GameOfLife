import numpy as np
from scipy.signal import convolve2d

def initialize_grid(size):
    """Initializes a grid of the given size with zeros."""
    return np.zeros((size, size), dtype=np.int8)

def update_grid_logic(grid, wrap_edges=True):
    """
    Updates the grid based on Conway's Game of Life rules.

    Args:
        grid (np.ndarray): The current state of the grid.
        wrap_edges (bool): If True, edges wrap around (toroidal array).
                           If False, edges are treated as dead cells.

    Returns:
        np.ndarray: The next state of the grid.
    """
    size = grid.shape[0]
    # Kernel to count neighbors
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=np.int8)

    # Determine boundary condition for convolution based on wrap_edges
    boundary_condition = 'wrap' if wrap_edges else 'fill'

    # Calculate the number of live neighbors for each cell
    neighbor_count = convolve2d(grid, kernel, mode='same', boundary=boundary_condition, fillvalue=0)

    # Apply Conway's rules:
    # 1. A living cell with 2 or 3 live neighbors survives.
    # 2. A dead cell with exactly 3 live neighbors becomes a live cell.
    # 3. All other live cells die in the next generation. Similarly, all other dead cells stay dead.
    new_grid = np.where(
        (grid == 1) & ((neighbor_count == 2) | (neighbor_count == 3)) |
        (grid == 0) & (neighbor_count == 3),
        1,  # Cell becomes/stays alive
        0   # Cell becomes/stays dead
    ).astype(np.int8)

    return new_grid

# You can add other game logic related functions here if needed
