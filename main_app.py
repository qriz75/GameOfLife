import tkinter as tk
from tkinter import ttk, font
import numpy as np
import time
from collections import deque
import copy # Keep for potential future use, though maybe not needed now

# --- Local Imports ---
from patterns import get_pattern, get_pattern_names
from game_logic import initialize_grid, update_grid_logic # Import from game_logic
from gui_components import CollapsibleFrame, draw_pattern_preview # Import from gui_components

# --- GUI Setup Constants ---
GRID_SIZE = 100 # Increased grid size from 50 to 100
UPDATE_INTERVAL = 30
PREVIEW_CANVAS_SIZE = 30
MAX_HISTORY_SIZE = 10
DIGITAL_FONT_SIZE = 18
STATS_FONT_SIZE = 10

# --- Global State ---
# (Keep global state management in the main application file)
grid = initialize_grid(GRID_SIZE) # Use imported function
paused = True
canvas_rects = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
CELL_SIZE = 10
generation_count = 0
simulation_state = "Paused"
previous_grid_states = deque(maxlen=MAX_HISTORY_SIZE)
previous_grid_state_for_stable_check = None
population_count = 0
initial_run_grid = None
initial_run_generation = 0
live_cell_count_history = deque(maxlen=20)
generation_time_history = deque(maxlen=20)
challenge_mode_active = False
challenge_pattern_placed = False
challenge_initial_population = 0
challenge_final_population = 0

# Pattern Selection State
selected_pattern_name = None
selected_pattern_array = None
ghost_pattern_ids = []
last_mouse_event = None

# --- Tkinter UI Widgets (defined globally for access in callbacks) ---
# Define placeholders, they will be assigned during UI setup
root = None
canvas = None
pause_button = None
reset_run_button = None
full_reset_button = None
challenge_button = None
generation_digital_label = None
state_digital_label = None
population_label = None
gen_time_label = None
pop_stability_label = None
initial_pop_label = None
final_pop_label = None

# --- UI Update and Event Handlers ---
# (Keep these in the main app as they interact heavily with global state and UI widgets)

def draw_grid(canvas_width=None, canvas_height=None):
    """Draws the grid state onto the main canvas, optimizing for reuse."""
    global CELL_SIZE, canvas_rects, grid, canvas # Need grid and canvas
    if canvas is None: return # Check if canvas exists
    if canvas_width is None: canvas_width = canvas.winfo_width()
    if canvas_height is None: canvas_height = canvas.winfo_height()
    if canvas_width <= 1 or canvas_height <= 1: return

    cell_width = canvas_width // GRID_SIZE
    cell_height = canvas_height // GRID_SIZE
    new_cell_size = max(1, min(cell_width, cell_height))

    needs_creation = not any(any(r is not None for r in row) for row in canvas_rects)

    CELL_SIZE = new_cell_size
    outline_color = "grey" if CELL_SIZE > 2 else ""

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            color = "black" if grid[r, c] == 1 else "white"
            x0, y0 = c * CELL_SIZE, r * CELL_SIZE
            x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE

            if needs_creation or canvas_rects[r][c] is None:
                 try:
                     if canvas_rects[r][c] is not None: canvas.delete(canvas_rects[r][c])
                 except tk.TclError: pass
                 canvas_rects[r][c] = canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline=outline_color, tags=("grid_cell",))
            else:
                try:
                    canvas.coords(canvas_rects[r][c], x0, y0, x1, y1)
                    canvas.itemconfig(canvas_rects[r][c], fill=color, outline=outline_color)
                except tk.TclError:
                    canvas_rects[r][c] = None

    if needs_creation:
        canvas.tag_lower("grid_cell")

def handle_resize(event):
    """Callback for window resize event."""
    global canvas, selected_pattern_name, last_mouse_event # Need canvas
    if canvas is None: return
    canvas.after_idle(lambda: draw_grid(event.width, event.height))
    if selected_pattern_name and last_mouse_event:
         canvas.after_idle(lambda: update_ghost_position(last_mouse_event))
    elif selected_pattern_name:
         canvas.after_idle(clear_ghost_pattern)

def update_info_labels():
    """Updates the generation count, simulation state, and stats labels."""
    global population_count, generation_count, simulation_state, generation_time_history, live_cell_count_history
    global challenge_initial_population, challenge_final_population, challenge_mode_active
    global generation_digital_label, state_digital_label, population_label, gen_time_label, pop_stability_label, initial_pop_label, final_pop_label # Need widgets

    # Check if widgets exist before configuring
    if generation_digital_label is None: return

    generation_digital_label.config(text=f"{generation_count:06d}")
    state_digital_label.config(text=f"{simulation_state.upper()}")

    population_label.config(text=f"Population: {population_count}")
    if generation_time_history:
        avg_gen_time = sum(generation_time_history) / len(generation_time_history)
        gen_time_label.config(text=f"Avg Gen Time: {avg_gen_time:.3f}s")
    else:
        gen_time_label.config(text="Avg Gen Time: N/A")

    if len(live_cell_count_history) > 1:
        pop_std_dev = np.std(list(live_cell_count_history))
        pop_stability_label.config(text=f"Pop Stability (StdDev): {pop_std_dev:.2f}")
    else:
        pop_stability_label.config(text="Pop Stability (StdDev): N/A")

    state_colors = {
        "Paused": "grey", "Running": "#20A020", "Stable": "#3030C0",
        "Dead": "#C03030", "Oscillating": "#D08000", "Running Challenge": "#20A020",
        "PLACE PATTERN": "blue" # Added state for challenge setup
    }
    state_digital_label.config(fg=state_colors.get(simulation_state, "black"))

    if challenge_initial_population > 0 and simulation_state in ["Stable", "Dead", "Oscillating"] and not challenge_mode_active:
        initial_pop_label.config(text=f"Challenge Initial Pop: {challenge_initial_population}")
        final_pop_label.config(text=f"Challenge Final Pop: {challenge_final_population}")
    else:
        initial_pop_label.config(text="")
        final_pop_label.config(text="")

def animation_step():
    """Performs one step of the simulation and updates state."""
    global grid, paused, generation_count, simulation_state, previous_grid_state_for_stable_check, population_count, initial_run_grid, initial_run_generation, previous_grid_states, live_cell_count_history, generation_time_history
    global root, canvas, canvas_rects # Need root and canvas

    if root is None or canvas is None: return # Exit if UI not ready

    if paused:
        if simulation_state not in ["Stable", "Dead", "Oscillating", "PLACE PATTERN"]: # Keep PLACE PATTERN state
             simulation_state = "Paused"
        update_info_labels()
        root.after(UPDATE_INTERVAL, animation_step)
        return

    start_time = time.perf_counter()

    if initial_run_grid is None:
        initial_run_grid = grid.copy()
        initial_run_generation = generation_count

    generation_count += 1
    # Keep "Running Challenge" state if active
    if not (challenge_mode_active and challenge_pattern_placed):
        simulation_state = "Running"

    current_grid_bytes = grid.tobytes()
    previous_grid_state_for_stable_check = grid.copy()

    # Use imported game logic function
    new_grid = update_grid_logic(grid)

    # --- Check for End States ---
    current_population = np.sum(new_grid)
    is_stable = False
    is_dead = False
    is_oscillating = False

    if current_population == 0:
        is_dead = True
        simulation_state = "Dead"
        paused = True
    elif np.array_equal(new_grid, previous_grid_state_for_stable_check):
        is_stable = True
        simulation_state = "Stable"
        paused = True
    else:
        new_grid_bytes = new_grid.tobytes()
        if new_grid_bytes in previous_grid_states:
             is_oscillating = True
             simulation_state = "Oscillating"
             paused = True
             print(f"Oscillation detected!")
        previous_grid_states.append(current_grid_bytes)

    # --- Update Grid, Stats and UI ---
    grid = new_grid
    population_count = current_population
    live_cell_count_history.append(population_count)
    end_time = time.perf_counter()
    generation_time_history.append(end_time - start_time)

    update_info_labels()
    if paused and pause_button: # Check if pause_button exists
        pause_button.config(text="Resume")

    # Update canvas
    diff = grid != previous_grid_state_for_stable_check
    rows, cols = np.where(diff)
    needs_full_redraw = False
    for r, c in zip(rows, cols):
         if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            rect = canvas_rects[r][c]
            if rect is not None:
                color = "black" if grid[r, c] == 1 else "white"
                try:
                    if canvas.winfo_exists() and rect in canvas.find_all():
                        canvas.itemconfig(rect, fill=color)
                    else:
                        canvas_rects[r][c] = None
                        needs_full_redraw = True
                except tk.TclError:
                    canvas_rects[r][c] = None
                    needs_full_redraw = True
            else:
                 needs_full_redraw = True

    if needs_full_redraw:
        draw_grid(canvas.winfo_width(), canvas.winfo_height())

    # --- Handle Challenge Mode End ---
    if paused and challenge_mode_active and challenge_pattern_placed and simulation_state in ["Stable", "Dead", "Oscillating"]:
        print(f"Challenge ended: {simulation_state}")
        global challenge_final_population
        challenge_final_population = population_count
        end_challenge_mode(display_results=True)

    # Schedule next step
    root.after(UPDATE_INTERVAL, animation_step)


def pause_resume():
    global paused, simulation_state, initial_run_grid, previous_grid_states, previous_grid_state_for_stable_check
    global pause_button # Need widget

    if paused and simulation_state in ["Stable", "Dead", "Oscillating"]:
        print(f"Cannot resume, simulation ended ({simulation_state})")
        return

    paused = not paused

    if not paused:
        simulation_state = "Running Challenge" if challenge_mode_active else "Running"
        previous_grid_states.clear()
        previous_grid_state_for_stable_check = None
        initial_run_grid = None
        print("Simulation Resumed")
    else:
        if simulation_state.startswith("Running"): # Covers "Running" and "Running Challenge"
             simulation_state = "Paused"
        print("Simulation Paused")

    if pause_button:
        pause_button.config(text="Resume" if paused else "Pause")
    update_info_labels()

def reset_run():
    global grid, paused, generation_count, simulation_state, previous_grid_state_for_stable_check, initial_run_grid, initial_run_generation, population_count, live_cell_count_history, generation_time_history, previous_grid_states
    global canvas # Need canvas

    if initial_run_grid is None:
        print("No previous run state to reset to. Performing full reset instead.")
        full_reset_simulation()
        return

    print("Resetting to start of the last run.")
    if initial_run_grid.shape != (GRID_SIZE, GRID_SIZE):
         print(f"Warning: Stored grid size {initial_run_grid.shape} differs from current GRID_SIZE ({GRID_SIZE}). Full reset.")
         full_reset_simulation()
         return

    grid = initial_run_grid.copy()
    generation_count = initial_run_generation
    population_count = np.sum(grid)
    paused = True
    simulation_state = "Paused"
    previous_grid_states.clear()
    previous_grid_state_for_stable_check = None
    initial_run_grid = None
    initial_run_generation = 0
    live_cell_count_history.clear()
    generation_time_history.clear()

    if pause_button: pause_button.config(text="Resume")
    cancel_selection()
    update_info_labels()
    if canvas: draw_grid(canvas.winfo_width(), canvas.winfo_height())

def full_reset_simulation():
    global grid, paused, generation_count, simulation_state, previous_grid_state_for_stable_check, canvas_rects, initial_run_grid, initial_run_generation, population_count, live_cell_count_history, generation_time_history, previous_grid_states
    global canvas, pause_button # Need widgets

    print("Performing full grid reset.")
    grid = initialize_grid(GRID_SIZE) # Use imported function with updated GRID_SIZE
    canvas_rects = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)] # Use new GRID_SIZE
    paused = True
    generation_count = 0
    population_count = 0
    simulation_state = "Paused"
    previous_grid_states.clear()
    previous_grid_state_for_stable_check = None
    initial_run_grid = None
    initial_run_generation = 0
    live_cell_count_history.clear()
    generation_time_history.clear()

    if pause_button: pause_button.config(text="Resume")
    cancel_selection()
    # Don't call update_info_labels here, let caller handle it if needed
    if canvas: draw_grid(canvas.winfo_width(), canvas.winfo_height())


# --- Pattern Selection / Placement Functions ---

def clear_ghost_pattern():
    global ghost_pattern_ids, canvas # Need canvas
    if canvas and canvas.winfo_exists():
        for item_id in ghost_pattern_ids:
            try:
                 if item_id in canvas.find_all():
                     canvas.delete(item_id)
            except tk.TclError: pass
    ghost_pattern_ids = []

def update_ghost_position(event):
    global ghost_pattern_ids, last_mouse_event, selected_pattern_array, CELL_SIZE, canvas # Need canvas
    clear_ghost_pattern()
    last_mouse_event = event

    if selected_pattern_array is not None and CELL_SIZE > 0 and canvas:
        canvas_x = event.x
        canvas_y = event.y
        col = int(canvas_x // CELL_SIZE)
        row = int(canvas_y // CELL_SIZE)

        pattern_height, pattern_width = selected_pattern_array.shape
        new_ghost_ids = []
        for r_offset in range(pattern_height):
            for c_offset in range(pattern_width):
                if selected_pattern_array[r_offset, c_offset] == 1:
                    target_row, target_col = row + r_offset, col + c_offset
                    if 0 <= target_row < GRID_SIZE and 0 <= target_col < GRID_SIZE:
                        x0, y0 = target_col * CELL_SIZE, target_row * CELL_SIZE
                        x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
                        rect_id = canvas.create_rectangle(x0, y0, x1, y1,
                                                          fill="blue", outline="lightblue",
                                                          stipple="gray50", width=1, tags="ghost")
                        new_ghost_ids.append(rect_id)
        ghost_pattern_ids = new_ghost_ids
        if ghost_pattern_ids:
            canvas.tag_raise("ghost")

def select_pattern(event, pattern_name):
    global selected_pattern_name, selected_pattern_array, last_mouse_event, canvas, root # Need canvas, root
    pattern = get_pattern(pattern_name)
    if pattern is not None:
        if selected_pattern_name == pattern_name:
             cancel_selection()
             return

        cancel_selection()
        selected_pattern_name = pattern_name
        selected_pattern_array = pattern.copy()
        print(f"Selected: {selected_pattern_name}")

        if canvas:
            canvas.bind("<Motion>", update_ghost_position)
            canvas.bind("<Button-3>", rotate_selected_pattern)

        if root and canvas: # Check both exist
            x_root, y_root = root.winfo_pointerxy()
            canvas_x_root = canvas.winfo_rootx()
            canvas_y_root = canvas.winfo_rooty()
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()

            if (canvas_x_root <= x_root < canvas_x_root + canvas_width and
                canvas_y_root <= y_root < canvas_y_root + canvas_height):
                 canvas_x = x_root - canvas_x_root
                 canvas_y = y_root - canvas_y_root
                 fake_event = tk.Event()
                 fake_event.x = canvas_x
                 fake_event.y = canvas_y
                 update_ghost_position(fake_event)

def place_pattern(event):
    global selected_pattern_name, selected_pattern_array, grid, population_count, CELL_SIZE, canvas, canvas_rects
    global challenge_mode_active, challenge_pattern_placed, challenge_initial_population, paused, simulation_state
    global pause_button # Need widget

    if selected_pattern_name and selected_pattern_array is not None and CELL_SIZE > 0 and canvas:
        canvas_x = event.x
        canvas_y = event.y
        col = int(canvas_x // CELL_SIZE)
        row = int(canvas_y // CELL_SIZE)

        print(f"Placed {selected_pattern_name} at grid ({row}, {col})")

        pattern_height, pattern_width = selected_pattern_array.shape
        redraw_required = False
        cells_changed = False # Track if any cell *actually* changed state

        for r_offset in range(pattern_height):
            for c_offset in range(pattern_width):
                target_row, target_col = row + r_offset, col + c_offset
                # Place pattern only within grid boundaries
                if 0 <= target_row < GRID_SIZE and 0 <= target_col < GRID_SIZE:
                    # Get the value from the pattern array (0 or 1)
                    pattern_value = selected_pattern_array[r_offset, c_offset]
                    # Check if the grid cell needs to be updated
                    if grid[target_row, target_col] != pattern_value:
                        grid[target_row, target_col] = pattern_value # Overwrite grid cell
                        cells_changed = True
                        # Update the specific cell on the canvas immediately
                        new_color = "black" if pattern_value == 1 else "white"
                        if canvas_rects[target_row][target_col] is not None:
                             try: canvas.itemconfig(canvas_rects[target_row][target_col], fill=new_color)
                             except tk.TclError: redraw_required = True # Mark for full redraw if error
                        else: redraw_required = True # Mark for full redraw if rect doesn't exist

        if cells_changed:
            population_count = np.sum(grid) # Update population count immediately

            # --- Handle Challenge Mode Pattern Placement ---
            if challenge_mode_active and not challenge_pattern_placed:
                challenge_initial_population = population_count
                challenge_pattern_placed = True
                paused = False
                simulation_state = "Running Challenge"
                print(f"Challenge Pattern Placed. Initial Pop: {challenge_initial_population}. Running...")
                if pause_button:
                    pause_button.config(text="Pause", state=tk.NORMAL) # Enable and set text

            update_info_labels() # Update display

        if redraw_required:
            # If itemconfig failed, redraw the whole grid to be safe
            draw_grid(canvas.winfo_width(), canvas.winfo_height())

        cancel_selection()

def rotate_selected_pattern(event=None):
    global selected_pattern_array, last_mouse_event, canvas # Need canvas
    if selected_pattern_name and selected_pattern_array is not None:
        selected_pattern_array = np.rot90(selected_pattern_array, k=-1)
        print("Rotated pattern")
        if last_mouse_event and canvas:
            canvas.after_idle(lambda: update_ghost_position(last_mouse_event))
        else:
            clear_ghost_pattern()

def cancel_selection(event=None):
    global selected_pattern_name, selected_pattern_array, last_mouse_event, canvas # Need canvas
    if selected_pattern_name:
        print("Selection cancelled.")
    selected_pattern_name = None
    selected_pattern_array = None
    last_mouse_event = None
    clear_ghost_pattern()
    if canvas:
        canvas.unbind("<Motion>")
        canvas.unbind("<Button-3>")

# --- Challenge Mode Functions ---

def toggle_challenge_mode():
    if not challenge_mode_active:
        start_challenge_mode()
    else:
        cancel_challenge_mode()

def start_challenge_mode():
    global challenge_mode_active, challenge_pattern_placed, challenge_initial_population, challenge_final_population, paused, simulation_state
    global challenge_button, pause_button, reset_run_button, full_reset_button, state_digital_label # Need widgets

    print("Starting Pattern Challenge Mode.")
    challenge_mode_active = True
    challenge_pattern_placed = False
    challenge_initial_population = 0
    challenge_final_population = 0
    paused = True

    full_reset_simulation() # Reset board and state first

    simulation_state = "PLACE PATTERN" # Set state *after* reset

    # Update UI for challenge mode
    if challenge_button: challenge_button.config(text="Cancel Challenge")
    if pause_button: pause_button.config(state=tk.DISABLED)
    if reset_run_button: reset_run_button.config(state=tk.DISABLED)
    if full_reset_button: full_reset_button.config(state=tk.DISABLED)
    # state_digital_label is updated via update_info_labels

    update_info_labels() # Update all info labels

def end_challenge_mode(display_results=True):
    global challenge_mode_active, challenge_pattern_placed, paused
    global challenge_button, pause_button, reset_run_button, full_reset_button # Need widgets
    global challenge_initial_population, challenge_final_population # Need state vars

    challenge_mode_active = False
    challenge_pattern_placed = False
    # Don't force pause if simulation ended naturally as stable/dead/oscillating
    # paused = True

    # Re-enable buttons
    if challenge_button: challenge_button.config(text="Start Challenge")
    if pause_button: pause_button.config(state=tk.NORMAL)
    if reset_run_button: reset_run_button.config(state=tk.NORMAL)
    if full_reset_button: full_reset_button.config(state=tk.NORMAL)

    if display_results:
        update_info_labels() # Show results
    else:
        challenge_initial_population = 0
        challenge_final_population = 0
        update_info_labels() # Clear results display

def cancel_challenge_mode():
    print("Pattern Challenge Mode Cancelled.")
    end_challenge_mode(display_results=False)
    full_reset_simulation() # Also reset the grid

# --- Pattern Categories ---
PATTERN_CATEGORIES = {
    "Still Lifes": ["Block", "Beehive", "Loaf", "Boat", "Tub"],
    "Oscillators": ["Blinker", "Toad", "Beacon", "Pulsar", "Pentadecathlon", "Figure Eight"], # Added Figure Eight
    "Spaceships": [
        "Glider", "Lightweight Spaceship (LWSS)", "Middleweight Spaceship (MWSS)",
        "Heavyweight Spaceship (HWSS)", "Spider" # Replaced Copperhead with Spider
        ],
    "Guns": ["Gosper Glider Gun"], # Removed Simkin Glider Gun
    "Methuselahs": ["R-pentomino", "Diehard", "Acorn", "Bunnies", "Thunderbird"]
}

# --- Main Application Setup ---

def build_gui(root_widget):
    """Builds the Tkinter GUI layout."""
    global root, canvas, pause_button, reset_run_button, full_reset_button, challenge_button
    global generation_digital_label, state_digital_label, population_label, gen_time_label, pop_stability_label, initial_pop_label, final_pop_label # Assign widgets

    root = root_widget # Assign the main window passed in

    try:
        if root.tk.call('tk', 'windowingsystem') == 'win32': root.state('zoomed')
        elif root.tk.call('tk', 'windowingsystem') == 'x11': root.attributes('-zoomed', True)
        else: root.geometry("1200x800")
    except tk.TclError:
        print("Could not maximize window automatically.")
        root.geometry("1200x800")
    root.minsize(width=900, height=600)
    root.bind('<Escape>', cancel_selection)

    main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
    main_pane.pack(fill=tk.BOTH, expand=True)

    canvas_frame = tk.Frame(main_pane, bg="lightgrey")
    main_pane.add(canvas_frame, stretch="always", minsize=400)

    canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas_frame.bind("<Configure>", handle_resize)
    canvas.bind("<Button-1>", place_pattern)

    control_frame_outer = tk.Frame(main_pane, width=300)
    control_frame_outer.pack_propagate(False)
    main_pane.add(control_frame_outer, stretch="never", minsize=250)

    control_frame = tk.Frame(control_frame_outer)
    control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # --- Top Buttons ---
    top_button_frame = tk.Frame(control_frame)
    top_button_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    challenge_button = ttk.Button(top_button_frame, text="Start Challenge", command=toggle_challenge_mode)
    challenge_button.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    pause_button = ttk.Button(top_button_frame, text="Resume", command=pause_resume)
    pause_button.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    reset_run_button = ttk.Button(top_button_frame, text="Reset Run", command=reset_run)
    reset_run_button.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    full_reset_button = ttk.Button(top_button_frame, text="Full Reset", command=full_reset_simulation)
    full_reset_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- Digital Status Display ---
    status_display_frame = tk.LabelFrame(control_frame, text="Status", relief="ridge", borderwidth=2, padx=5, pady=5)
    status_display_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    status_display_frame.columnconfigure(0, weight=1)
    try:
        digital_font = font.Font(family="Consolas", size=DIGITAL_FONT_SIZE, weight="bold")
    except tk.TclError:
        digital_font = font.Font(family="Courier", size=DIGITAL_FONT_SIZE, weight="bold")
    generation_digital_label = tk.Label(status_display_frame, text="000000", font=digital_font, anchor="center", fg="black", bg="lightgrey", relief="sunken", bd=2)
    generation_digital_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))
    state_digital_label = tk.Label(status_display_frame, text="PAUSED", font=digital_font, anchor="center", fg="grey", bg="lightgrey", relief="sunken", bd=2)
    state_digital_label.grid(row=1, column=0, sticky="ew")

    # --- Stats Panel ---
    stats_panel_frame = tk.LabelFrame(control_frame, text="Statistics", relief="ridge", borderwidth=2, padx=5, pady=5)
    stats_panel_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
    stats_font = font.Font(size=STATS_FONT_SIZE)
    population_label = tk.Label(stats_panel_frame, text="Population: 0", font=stats_font, anchor="w")
    population_label.pack(fill=tk.X)
    gen_time_label = tk.Label(stats_panel_frame, text="Avg Gen Time: N/A", font=stats_font, anchor="w")
    gen_time_label.pack(fill=tk.X)
    pop_stability_label = tk.Label(stats_panel_frame, text="Pop Stability (StdDev): N/A", font=stats_font, anchor="w")
    pop_stability_label.pack(fill=tk.X)
    initial_pop_label = tk.Label(stats_panel_frame, text="", font=stats_font, anchor="w", fg="blue")
    initial_pop_label.pack(fill=tk.X)
    final_pop_label = tk.Label(stats_panel_frame, text="", font=stats_font, anchor="w", fg="blue")
    final_pop_label.pack(fill=tk.X)

    # --- Pattern Area ---
    patterns_area_frame = tk.Frame(control_frame)
    patterns_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    patterns_area_frame.columnconfigure(0, weight=1, uniform="col")
    patterns_area_frame.columnconfigure(1, weight=1, uniform="col")
    column1_frame = tk.Frame(patterns_area_frame)
    column1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
    column2_frame = tk.Frame(patterns_area_frame)
    column2_frame.grid(row=0, column=1, sticky="nsew", padx=(1, 0))

    # --- Populate Patterns ---
    column_index = 0
    all_pattern_names = get_pattern_names()
    for category_title, pattern_names_in_category in PATTERN_CATEGORIES.items():
        target_column = column1_frame if column_index % 2 == 0 else column2_frame
        column_index += 1

        # Use imported CollapsibleFrame
        collapsible = CollapsibleFrame(target_column, title=category_title, start_expanded=True)
        collapsible.pack(fill=tk.X, pady=(1, 0))
        category_content_frame = collapsible.get_content_frame()

        for name in pattern_names_in_category:
            if name not in all_pattern_names:
                print(f"Warning: Pattern '{name}' in category '{category_title}' not found. Skipping.")
                continue
            pattern_array = get_pattern(name)
            if pattern_array is None: continue

            entry_frame = tk.Frame(category_content_frame, relief="groove", borderwidth=1)
            entry_frame.pack(fill=tk.X, padx=1, pady=0)
            entry_frame.columnconfigure(1, weight=1)

            preview_canvas = tk.Canvas(entry_frame, width=PREVIEW_CANVAS_SIZE, height=PREVIEW_CANVAS_SIZE, bg="white", highlightthickness=0)
            preview_canvas.grid(row=0, column=0, padx=(1, 3), pady=1, sticky="w")

            # Use imported draw_pattern_preview
            draw_pattern_preview(preview_canvas, pattern_array, PREVIEW_CANVAS_SIZE)

            lbl = ttk.Label(entry_frame, text=name, anchor="w", cursor="hand2")
            lbl.grid(row=0, column=1, sticky="ew")

            click_handler = lambda event, p=name: select_pattern(event, p)
            entry_frame.bind("<Button-1>", click_handler)
            preview_canvas.bind("<Button-1>", click_handler)
            lbl.bind("<Button-1>", click_handler)

            def on_enter(e, frame=entry_frame): frame.config(bg="lightblue")
            def on_leave(e, frame=entry_frame): frame.config(bg=category_content_frame.cget("bg"))
            entry_frame.bind("<Enter>", on_enter)
            entry_frame.bind("<Leave>", on_leave)
            preview_canvas.bind("<Enter>", lambda e, f=entry_frame: on_enter(e, f))
            preview_canvas.bind("<Leave>", lambda e, f=entry_frame: on_leave(e, f))
            lbl.bind("<Enter>", lambda e, f=entry_frame: on_enter(e, f))
            lbl.bind("<Leave>", lambda e, f=entry_frame: on_leave(e, f))

# --- Main Execution ---
if __name__ == "__main__":
    main_window = tk.Tk()
    main_window.title("Conway's Game of Life (Refactored)")
    build_gui(main_window) # Build the UI onto the main window

    # Initial setup after UI is built
    root.update_idletasks() # Ensure UI is fully drawn
    update_info_labels() # Set initial label text
    # Corrected typo: winfo_height() instead of winfo.height()
    if canvas: draw_grid(canvas.winfo_width(), canvas.winfo_height()) # Initial grid draw

    # Start the animation loop
    animation_step()
    main_window.mainloop()