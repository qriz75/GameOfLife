import numpy as np
try:
    import scipy.signal
    use_scipy = True
    print("Using SciPy for optimized neighbor counting.")
except ImportError:
    use_scipy = False
    print("SciPy not found. Using slower neighbor counting method.")

def initialize_grid(size):
    """Initializes an empty grid of the given size."""
    return np.zeros((size, size), dtype=int)

def count_live_neighbors_convolve(grid):
    """Counts live neighbors using 2D convolution."""
    kernel = np.array([[1, 1, 1],
                       [1, 0, 1],
                       [1, 1, 1]], dtype=int)
    # 'wrap' handles boundary conditions like modulo
    return scipy.signal.convolve2d(grid, kernel, mode='same', boundary='wrap')

def count_live_neighbors_manual(grid, x, y):
    """Counts the live neighbors of a cell at (x, y) using toroidal boundaries."""
    size = grid.shape[0]
    count = 0
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue
            row, col = (x + i) % size, (y + j) % size
            count += grid[row, col]
    return count

def update_grid_logic(grid):
    """Computes the next generation state based on Conway's rules."""
    size = grid.shape[0]
    new_grid = grid.copy()

    if use_scipy:
        live_neighbors = count_live_neighbors_convolve(grid)
        # Apply Conway's rules using boolean masking (vectorized)
        survivors = (grid == 1) & ((live_neighbors == 2) | (live_neighbors == 3))
        births = (grid == 0) & (live_neighbors == 3)
        new_grid = np.zeros_like(grid) # Start fresh
        new_grid[survivors | births] = 1
    else:
        # Fallback to manual iteration if scipy not available
        for i in range(size):
            for j in range(size):
                live_neighbors = count_live_neighbors_manual(grid, i, j)
                if grid[i, j] == 1: # Live cell
                    if live_neighbors < 2 or live_neighbors > 3:
                        new_grid[i, j] = 0 # Dies
                else: # Dead cell
                    if live_neighbors == 3:
                        new_grid[i, j] = 1 # Becomes alive
    return new_grid
