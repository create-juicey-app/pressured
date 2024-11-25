import math  # Add this import if not already present

# Screen dimensions
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 600
ROWS, COLS = 20, 20
TILE_SIZE = GRID_SIZE // COLS
SIDEBAR_WIDTH = WIDTH /4
MAX_PRESSURE = 10.0
GAS_SPREAD_RATE = 0.05
MACHINE_DAMAGE_RATE = 0.05
VACUUM_COLOR = (35, 35, 40)  # Slightly blueish dark
MIN_N2_FOR_ENGINE = 2.0  # Rename to MIN_N2_FOR_ENGINE if you want to be more precise
PLANT_O2_RATE = 0.1
PLANT_CO2_CONSUMPTION = 0.2
SPAC_N2_RATE = 2.0  # Changed from SPAC_CO2_RATE
PIPE_COLOR = (168, 132, 80)  # Warmer brown

# Base Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_LIGHT = (200, 200, 200)
GRAY_MID = (130, 130, 130)
GRAY_DARK = (70, 70, 70)
GRAY = GRAY_MID  # Add this line to define GRAY

# Theme Colors
PRIMARY = (66, 133, 244)      # Google Blue
PRIMARY_DARK = (25, 103, 210)
SECONDARY = (52, 168, 83)     # Green
SECONDARY_DARK = (30, 120, 50)
DANGER = (234, 67, 53)        # Red
DANGER_DARK = (190, 45, 35)
WARNING = (251, 188, 4)       # Yellow
WARNING_DARK = (200, 150, 0)
INFO = (26, 115, 232)         # Light Blue
INFO_DARK = (20, 90, 180)

# UI Colors
UI_BG = (32, 33, 36)          # Dark background
UI_SURFACE = (41, 42, 46)     # Slightly lighter surface
UI_SURFACE_LIGHT = (53, 54, 58)
UI_ACCENT = (138, 180, 248)   # Light blue accent
UI_BORDER = (95, 99, 104)     # Gray border

# Game Colors
DARK_BG = UI_BG              # Use UI background
DARK_GRID = UI_SURFACE       # Use UI surface

# Existing game colors but brighter
BLUE = (66, 133, 244)        # Google Blue
RED = (234, 67, 53)          # Google Red
GREEN = (52, 168, 83)        # Google Green
YELLOW = (251, 188, 4)       # Google Yellow
CYAN = (24, 190, 200)        # Bright Cyan
ORANGE = (250, 123, 5)       # Bright Orange
YELLOW_BRIGHT = (255, 235, 59)  # Material Yellow


SNACKBAR_HEIGHT = 50
SNACKBAR_DURATION = 3000  # Duration in milliseconds
