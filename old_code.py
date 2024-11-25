import pygame
import sys
import math
from enum import Enum
from typing import List, Set
from dataclasses import dataclass

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 600
ROWS, COLS = 20, 20
TILE_SIZE = GRID_SIZE // COLS
SIDEBAR_WIDTH = WIDTH - GRID_SIZE
MAX_PRESSURE = 10.0
GAS_SPREAD_RATE = 0.1
MACHINE_DAMAGE_RATE = 0.05
VACUUM_COLOR = (51, 51, 51)  # #333333
MIN_O2_FOR_ENGINE = 5.0
PLANT_O2_RATE = 0.1
PLANT_CO2_CONSUMPTION = 0.2
SPAC_CO2_RATE = 1.0
PIPE_COLOR = (128, 64, 0)  # Brown color for pipes

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
DARK_BG = (20, 20, 30)
DARK_GRID = (40, 40, 50)
ORANGE = (255, 165, 0)
YELLOW_BRIGHT = (255, 255, 128)

# Game modes
class Mode(Enum):
    CREATE = "Room Creation"
    INSPECT = "Inspect"
    PLAY = "Play"

class Tool(Enum):
    # Construction
    WALL = "Wall"
    DOOR = "Door"
    
    # Power
    WIRE = "Wire"
    ENGINE = "Engine"
    
    # Life Support
    OXYGEN = "O2 Generator"
    VENT = "Ventilation"
    PIPE = "Pipe"
    PLANT = "Plant"
    SPAC = "SPAC-12"
    
    # Utility
    DELETE = "Delete"

    @staticmethod
    def get_categories():
        return {
            "Construction": [Tool.WALL, Tool.DOOR],
            "Power": [Tool.WIRE, Tool.ENGINE],
            "Life Support": [Tool.OXYGEN, Tool.VENT, Tool.PIPE, Tool.PLANT, Tool.SPAC],
            "Utility": [Tool.DELETE]
        }

@dataclass
class GasCell:
    o2: float = 0
    co2: float = 0
    n2: float = 0  # nitrogen for air
    
    def total(self):
        return self.o2 + self.co2 + self.n2
    
    def pressure(self):
        return self.total() / 100.0  # normalize to 0-1 scale

    def add_gas(self, gas_type: str, amount: float):
        if gas_type == 'O2':
            self.o2 += amount
        elif gas_type == 'CO2':
            self.co2 += amount
        elif gas_type == 'N2':
            self.n2 += amount

    def consume_gas(self, gas_type: str, amount: float):
        if gas_type == 'O2':
            self.o2 = max(self.o2 - amount, 0)
        elif gas_type == 'CO2':
            self.co2 = max(self.co2 - amount, 0)
        elif gas_type == 'N2':
            self.n2 = max(self.n2 - amount, 0)

class RoomInfoPopup:
    def __init__(self, room, pos):
        self.room = room
        self.rect = pygame.Rect(pos[0], pos[1], 300, 200)
        self.visible = True
        self.font = pygame.font.SysFont('arial', 16)
        
    def draw(self, win):
        if not self.visible:
            return
            
        pygame.draw.rect(win, DARK_GRID, self.rect)
        pygame.draw.rect(win, WHITE, self.rect, 2)
        
        # Draw pressure bar on the right first
        pressure_container = pygame.Rect(self.rect.right - 40, self.rect.y + 10, 30, 150)
        pygame.draw.rect(win, DARK_GRID, pressure_container)
        pygame.draw.rect(win, WHITE, pressure_container, 1)
        
        pressure_height = min(self.room.pressure() / MAX_PRESSURE, 1) * 150
        pressure_rect = pygame.Rect(
            pressure_container.x,
            pressure_container.bottom - pressure_height,
            pressure_container.width,
            pressure_height
        )
        pygame.draw.rect(win, ORANGE, pressure_rect)
        
        # Draw text information with adjusted spacing
        x = self.rect.x + 10
        y = self.rect.y + 10
        
        texts = [
            f"Room Size: {len(self.room.tiles)} tiles",
            f"O2: {self.room.gases.o2:.1f}",
            f"CO2: {self.room.gases.co2:.1f}",
            f"N2: {self.room.gases.n2:.1f}",
            f"Damage: {self.room.damage:.1%}",
            f"Breathable: {self.room.breathable}",
            f"Pressure: {self.room.pressure():.1f}/{MAX_PRESSURE}"
        ]
        
        for text in texts:
            text_surface = self.font.render(text, True, WHITE)
            win.blit(text_surface, (x, y))
            y += 20
        
        # Draw gas composition bar at the bottom
        # Draw gas composition bar on the left
        bar_width = 200
        bar_height = 20
        x = self.rect.x + 10
        y = self.rect.bottom - 40
        
        # Draw container for gas bar
        pygame.draw.rect(win, DARK_GRID, (x, y, bar_width, bar_height))
        pygame.draw.rect(win, WHITE, (x, y, bar_width, bar_height), 1)
        
        total_gas = self.room.gases.total()
        if total_gas > 0:
            # O2 bar (green)
            o2_width = (self.room.gases.o2 / total_gas) * bar_width
            pygame.draw.rect(win, GREEN, (x, y, o2_width, bar_height))
            
            # CO2 bar (red)
            co2_width = (self.room.gases.co2 / total_gas) * bar_width
            pygame.draw.rect(win, RED, (x + o2_width, y, co2_width, bar_height))
            
            # N2 bar (blue)
            n2_width = (self.room.gases.n2 / total_gas) * bar_width
            pygame.draw.rect(win, BLUE, (x + o2_width + co2_width, y, n2_width, bar_height))

class Tile:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.x = col * TILE_SIZE
        self.y = row * TILE_SIZE
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.wall = False
        self.door = False
        self.room = None
        self.component = None
        self.wire = False
        self.powered = False
        self.gases = GasCell()
        self.damage = 0.0
        self.pipe = False  # Add pipe property

    def draw(self, win):
        # Set base color - change vacuum color
        color = VACUUM_COLOR if not (self.wall or self.room) else DARK_GRID if not self.wall else GRAY
        if self.door:
            color = YELLOW
        pygame.draw.rect(win, color, self.rect)
        
        if self.wire:
            # Check adjacent tiles for wire connections
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = self.row + dr, self.col + dc
                if (0 <= new_row < self.simulator.ROWS and 
                    0 <= new_col < self.simulator.COLS and 
                    self.simulator.grid[new_row][new_col].wire):
                    # Draw connection line
                    start_x = self.x + TILE_SIZE // 2
                    start_y = self.y + TILE_SIZE // 2
                    end_x = start_x + dc * TILE_SIZE
                    end_y = start_y + dr * TILE_SIZE
                    color = ORANGE if self.powered else RED
                    pygame.draw.line(win, color, (start_x, start_y), 
                                  (end_x, end_y), 2)

            # Draw wire node
            center_x = self.x + TILE_SIZE // 2
            center_y = self.y + TILE_SIZE // 2
            pygame.draw.circle(win, ORANGE if self.powered else RED, 
                             (center_x, center_y), 4)
            
            # Draw power icon when powered
            if self.powered:
                bolt_points = [
                    (center_x - 3, center_y - 5),
                    (center_x + 2, center_y - 1),
                    (center_x - 1, center_y + 1),
                    (center_x + 3, center_y + 5)
                ]
                pygame.draw.lines(win, YELLOW_BRIGHT, False, bolt_points, 2)

        # Draw pipes (similar to wire but with different color)
        if self.pipe:
            # Check adjacent tiles for pipe connections
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = self.row + dr, self.col + dc
                if (0 <= new_row < self.simulator.ROWS and 
                    0 <= new_col < self.simulator.COLS and 
                    self.simulator.grid[new_row][new_col].pipe):
                    start_x = self.x + TILE_SIZE // 2
                    start_y = self.y + TILE_SIZE // 2
                    end_x = start_x + dc * TILE_SIZE
                    end_y = start_y + dr * TILE_SIZE
                    pygame.draw.line(win, PIPE_COLOR, (start_x, start_y), 
                                  (end_x, end_y), 3)

            # Draw pipe node
            center_x = self.x + TILE_SIZE // 2
            center_y = self.y + TILE_SIZE // 2
            pygame.draw.circle(win, PIPE_COLOR, (center_x, center_y), 4)
            
        if self.component:
            inner_rect = pygame.Rect(
                self.x + 2, self.y + 2, 
                TILE_SIZE - 4, TILE_SIZE - 4
            )
            component_color = self.get_component_color()
            pygame.draw.rect(win, component_color, inner_rect)
                
        if self.room and hasattr(self, 'simulator') and self.simulator.mode == Mode.INSPECT:
            o2_level = self.room.gases.o2 / 100  # Normalize to 0-1
            pressure_level = self.room.pressure()
            avg_level = (o2_level + pressure_level) / 2
            overlay = pygame.Surface((TILE_SIZE, TILE_SIZE))
            overlay.fill(CYAN)
            overlay.set_alpha(int(128 * avg_level))  # Semi-transparent based on levels
            win.blit(overlay, self.rect)
            
        pygame.draw.rect(win, BLACK, self.rect, 1)

        # Draw gas levels
        if self.simulator.mode == Mode.INSPECT:
            gas_total = self.gases.total()
            if gas_total > 0:
                # Create colored overlay based on gas composition
                overlay = pygame.Surface((TILE_SIZE, TILE_SIZE))
                o2_color = (0, 255, 0, int(128 * self.gases.o2 / gas_total))
                co2_color = (255, 0, 0, int(128 * self.gases.co2 / gas_total))
                n2_color = (0, 0, 255, int(128 * self.gases.n2 / gas_total))
                
                for color in [o2_color, co2_color, n2_color]:
                    if color[3] > 0:
                        temp_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                        temp_surface.fill(color)
                        win.blit(temp_surface, self.rect)
        
        # Draw damage
        if self.damage > 0:
            damage_overlay = pygame.Surface((TILE_SIZE, TILE_SIZE))
            damage_overlay.fill((255, 0, 0))
            damage_overlay.set_alpha(int(128 * self.damage))
            win.blit(damage_overlay, self.rect)

    def get_component_color(self):
        if not self.component:
            return None
        
        base_color = RED if isinstance(self.component, Engine) else \
                    GREEN if isinstance(self.component, OxygenGenerator) else \
                    BLUE if isinstance(self.component, Ventilation) else \
                    (0, 128, 0) if isinstance(self.component, Plant) else \
                    (128, 0, 128) if isinstance(self.component, Spac12) else None
                    
        if isinstance(self.component, Engine) and not self.component.powered:
            return (base_color[0]//3, base_color[1]//3, base_color[2]//3)
        if not self.powered and isinstance(self.component, (OxygenGenerator, Spac12)):
            return (base_color[0]//3, base_color[1]//3, base_color[2]//3)
        return base_color

    def spread_gas(self, neighbors):
        if self.wall:  # Walls don't spread gas
            return
            
        valid_neighbors = [n for n in neighbors if not n.wall]
        if not valid_neighbors:
            return
            
        rate = GAS_SPREAD_RATE
        if self.door:
            rate *= 2
            
        for neighbor in valid_neighbors:
            self.gases.mix_with(neighbor.gases, rate / len(valid_neighbors))

class Room:
    def __init__(self, tiles):
        self.tiles = tiles
        self.gases = GasCell()
        self.damage = 0
        self.breathable = True
        for tile in tiles:
            tile.room = self
    
    def pressure(self):
        return self.gases.pressure()
    
    def update(self):
        # Check pressure damage
        if self.pressure() > MAX_PRESSURE:
            self.damage += MACHINE_DAMAGE_RATE
            # Damage components when pressure is too high
            for tile in self.tiles:
                if tile.component or tile.wire:
                    tile.damage = min(1.0, tile.damage + MACHINE_DAMAGE_RATE)

    def add_gas(self, gas_type: str, amount: float):
        self.gases.add_gas(gas_type, amount)

    def consume_gas(self, gas_type: str, amount: float):
        self.gases.consume_gas(gas_type, amount)

class Engine:
    def __init__(self, room):
        self.room = room
        self.consumption_rate = 8  # Higher oxygen consumption
        self.powered = False
        
    def run(self):
        if hasattr(self, 'tile'):
            # Check if enough O2 is available
            if self.tile.gases.o2 >= MIN_O2_FOR_ENGINE:
                self.powered = True
                self.tile.gases.consume_gas('O2', self.consumption_rate)
                self.tile.gases.add_gas('CO2', self.consumption_rate * 0.8)
            else:
                self.powered = False

class OxygenGenerator:
    def __init__(self, room):
        self.room = room
        self.generation_rate = 10  # Increased for better visibility

    def generate(self):
        if hasattr(self, 'tile') and self.tile.powered:
            self.tile.gases.add_gas('O2', self.generation_rate)

class Ventilation:
    def __init__(self, room):
        self.room = room
        self.transfer_rate = 1.0  # CO2 transfer rate
        self.connected_spacs = []

    def find_connected_spacs(self):
        """Find all SPAC-12 units connected via pipes"""
        if not hasattr(self, 'tile'):
            return []
        
        visited = set()
        to_check = {self.tile}
        spacs = []
        
        while to_check:
            current = to_check.pop()
            if current not in visited:
                visited.add(current)
                
                # Check if current tile has a SPAC-12
                if (current.component and 
                    isinstance(current.component, Spac12) and 
                    current != self.tile):
                    spacs.append(current.component)
                
                # Add connected pipe tiles
                row, col = current.row, current.col
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    new_row, new_col = row + dr, col + dc
                    if (0 <= new_row < self.tile.simulator.ROWS and 
                        0 <= new_col < self.tile.simulator.COLS):
                        next_tile = self.tile.simulator.grid[new_row][new_col]
                        if next_tile.pipe and next_tile not in visited:
                            to_check.add(next_tile)
        
        return spacs

    def update(self):
        """Transfer CO2 from connected SPAC-12s to room"""
        if not hasattr(self, 'tile') or not self.tile.powered:
            return
            
        # Update connected SPACs
        self.connected_spacs = self.find_connected_spacs()
        
        # Transfer CO2 from each connected SPAC
        for spac in self.connected_spacs:
            if spac.tile.gases.co2 > 0:
                transfer_amount = min(spac.tile.gases.co2, self.transfer_rate)
                spac.tile.gases.consume_gas('CO2', transfer_amount)
                self.tile.gases.add_gas('CO2', transfer_amount)

class Plant:
    def __init__(self, room):
        self.room = room
        self.generation_rate = PLANT_O2_RATE
        self.consumption_rate = PLANT_CO2_CONSUMPTION

    def generate(self):
        if hasattr(self, 'tile'):
            if self.tile.gases.co2 >= self.consumption_rate:
                self.tile.gases.consume_gas('CO2', self.consumption_rate)
                self.tile.gases.add_gas('O2', self.generation_rate)

class Spac12:
    def __init__(self, room):
        self.room = room
        self.generation_rate = SPAC_CO2_RATE

    def generate(self):
        if hasattr(self, 'tile') and self.tile.powered:
            # Only work in vacuum (no room)
            if not self.tile.room:
                self.tile.gases.add_gas('CO2', self.generation_rate)

class Simulator:
    def __init__(self):
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Room Pressure Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 20)
        
        self.mode = Mode.CREATE
        self.selected_tool = Tool.WALL
        self.grid = [[Tile(row, col) for col in range(COLS)] for row in range(ROWS)]
        self.rooms = []
        self.selected_tiles = []
        self.mouse_held = False
        self.last_modified_pos = None
        self.powered_tiles = set()
        self.update_counter = 0
        self.active_popup = None
        
        for row in self.grid:
            for tile in row:
                tile.simulator = self
                tile.room = None  # Ensure no room (vacuum)
                tile.gases = GasCell()  # Empty gases for vacuum

        self.ROWS = ROWS  # Add these for tile access
        self.COLS = COLS

    def draw_sidebar(self):
        sidebar_x = GRID_SIZE
        pygame.draw.rect(self.win, GRAY, (sidebar_x, 0, SIDEBAR_WIDTH, HEIGHT))
        
        y_pos = 10
        # Draw mode selection
        for mode in Mode:
            color = GREEN if self.mode == mode else WHITE
            text = self.font.render(mode.value, True, color)
            rect = text.get_rect(x=sidebar_x + 10, y=y_pos)
            self.win.blit(text, rect)
            y_pos += 30

        if self.mode == Mode.CREATE:
            y_pos += 20
            # Draw tool categories
            for category, tools in Tool.get_categories().items():
                # Draw category header
                self.win.blit(self.font.render(category + ":", True, WHITE), 
                            (sidebar_x + 10, y_pos))
                y_pos += 25
                
                # Draw tools in category
                for tool in tools:
                    color = GREEN if self.selected_tool == tool else WHITE
                    text = self.font.render("  " + tool.value, True, color)
                    rect = text.get_rect(x=sidebar_x + 10, y=y_pos)
                    self.win.blit(text, rect)
                    
                    # Add simple tool preview/icon
                    if tool != Tool.DELETE:
                        preview_rect = pygame.Rect(sidebar_x + SIDEBAR_WIDTH - 30, 
                                                y_pos, 20, 20)
                        if tool == Tool.WALL:
                            pygame.draw.rect(self.win, GRAY, preview_rect)
                        elif tool == Tool.DOOR:
                            pygame.draw.rect(self.win, YELLOW, preview_rect)
                        elif tool == Tool.WIRE:
                            pygame.draw.rect(self.win, RED, preview_rect)
                        elif tool == Tool.ENGINE:
                            pygame.draw.rect(self.win, RED, preview_rect)
                        # ... add more tool previews ...
                    
                    y_pos += 30
                y_pos += 10  # Space between categories

    def flood_fill(self, start_tile) -> Set[Tile]:
        """Find connected room tiles, excluding vacuum"""
        if start_tile.wall or start_tile.door:
            return set()
            
        to_check = {start_tile}
        room_tiles = set()
        room_enclosed = True  # Track if room is properly enclosed
        
        while to_check:
            tile = to_check.pop()
            if tile not in room_tiles:
                room_tiles.add(tile)
                row, col = tile.row, tile.col
                
                # Check for room edges
                if (row == 0 or row == ROWS-1 or col == 0 or col == COLS-1):
                    room_enclosed = False  # Room touches the edge, consider it vacuum
                
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    new_row, new_col = row + dr, col + dc
                    if 0 <= new_row < ROWS and 0 <= new_col < COLS:
                        next_tile = self.grid[new_row][new_col]
                        if not next_tile.wall and not next_tile.door:
                            to_check.add(next_tile)
                    else:
                        room_enclosed = False  # Found an edge
        
        # Only return tiles if room is properly enclosed
        return room_tiles if room_enclosed else set()

    def create_room(self, tiles):
        """Create a new room from a set of tiles"""
        if not tiles:
            return None
            
        room = Room(tiles)
        self.rooms.append(room)
        for tile in tiles:
            tile.room = room
        return room

    def handle_click(self, pos, is_held=False):
        # Clear popup when clicking elsewhere or changing modes
        if self.mode != Mode.INSPECT or pos[0] >= GRID_SIZE:
            self.active_popup = None

        if pos[0] >= GRID_SIZE:
            if not is_held:
                y = pos[1]
                y_pos = 10
                for mode in Mode:
                    if y_pos <= y <= y_pos + 30:
                        self.mode = mode
                        return
                    y_pos += 30
                
                if self.mode == Mode.CREATE:
                    y_pos += 50
                    for tool in Tool:
                        if y_pos <= y <= y_pos + 30:
                            self.selected_tool = tool
                            return
                        y_pos += 30
        else:
            row = pos[1] // TILE_SIZE
            col = pos[0] // TILE_SIZE
            if 0 <= row < ROWS and 0 <= col < COLS:
                if is_held and (row, col) == self.last_modified_pos:
                    return
                    
                self.last_modified_pos = (row, col)
                tile = self.grid[row][col]
                
                if self.mode == Mode.CREATE:
                    if self.selected_tool == Tool.DELETE:
                        # Don't delete vacuum, only components and structures
                        if tile.component:
                            tile.component = None
                            tile.damage = 0  # Reset damage when component is removed
                        tile.wire = False
                        tile.door = False
                        if tile.wall:  # Only remove wall if it exists
                            tile.wall = False
                            tile.damage = 0
                    elif self.selected_tool == Tool.WIRE:
                        tile.wire = True
                        self.update_power_network()
                    elif self.selected_tool == Tool.WALL:
                        tile.wall = True
                        tile.door = False
                        tile.wire = False
                        tile.component = None
                    elif self.selected_tool == Tool.DOOR:
                        tile.door = True
                        tile.wall = False
                        tile.component = None
                    elif self.selected_tool in [Tool.ENGINE, Tool.OXYGEN, Tool.VENT, Tool.PLANT]:
                        if not tile.wall and not tile.door:
                            room_tiles = self.flood_fill(tile)
                            if room_tiles:  # Only create room if enclosed
                                # Create room if tile isn't already in one
                                room = tile.room or self.create_room(room_tiles)
                                
                                if self.selected_tool == Tool.ENGINE:
                                    tile.component = Engine(room)
                                elif self.selected_tool == Tool.OXYGEN:
                                    tile.component = OxygenGenerator(room)
                                elif self.selected_tool == Tool.VENT:
                                    tile.component = Ventilation(room)
                                elif self.selected_tool == Tool.PLANT:
                                    tile.component = Plant(room)
                                
                                if tile.component:
                                    tile.component.tile = tile
                    elif self.selected_tool == Tool.SPAC:
                        if not tile.wall and not tile.door and not tile.room:  # Must be in vacuum
                            tile.component = Spac12(None)
                            tile.component.tile = tile
                    elif self.selected_tool == Tool.PIPE:
                        tile.pipe = True

        if self.mode == Mode.INSPECT:
            row = pos[1] // TILE_SIZE
            col = pos[0] // TILE_SIZE
            if 0 <= row < ROWS and 0 <= col < COLS:
                tile = self.grid[row][col]
                if tile.room:
                    # Highlight room and show popup
                    self.active_popup = RoomInfoPopup(tile.room, (pos[0], pos[1]))

    def update_gases(self):
        # Faster gas dissipation in vacuum
        VACUUM_DISSIPATION_RATE = 0.5  # Adjust this value for faster/slower dissipation
        
        for row in range(ROWS):
            for col in range(COLS):
                tile = self.grid[row][col]
                if not tile.room and not tile.wall:  # Vacuum tiles
                    # Rapidly decrease gas levels
                    tile.gases.o2 *= (1 - VACUUM_DISSIPATION_RATE)
                    tile.gases.co2 *= (1 - VACUUM_DISSIPATION_RATE)
                    tile.gases.n2 *= (1 - VACUUM_DISSIPATION_RATE)
                    
                    # Clean up very small values
                    if tile.gases.o2 < 0.01: tile.gases.o2 = 0
                    if tile.gases.co2 < 0.01: tile.gases.co2 = 0
                    if tile.gases.n2 < 0.01: tile.gases.n2 = 0

        # Clear gases from vacuum tiles first
        for row in range(ROWS):
            for col in range(COLS):
                tile = self.grid[row][col]
                if not tile.room and not tile.wall:  # Vacuum tiles
                    tile.gases = GasCell()  # Reset to zero
                    
        # Create copy of current gas state
        old_gases = [[GasCell() for _ in range(COLS)] for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                tile = self.grid[row][col]
                old_gases[row][col] = GasCell(tile.gases.o2, tile.gases.co2, tile.gases.n2)

        # Update each tile's gases based on neighbors
        for row in range(ROWS):
            for col in range(COLS):
                tile = self.grid[row][col]
                if tile.wall or tile.door:  # Skip walls AND closed doors
                    continue
                    
                # Get valid neighbors (no walls, respect doors)
                valid_neighbors = []
                curr_gas = old_gases[row][col]
                
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    new_row, new_col = row + dr, col + dc
                    if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                        neighbor = self.grid[new_row][new_col]
                        if not neighbor.wall and not neighbor.door:  # Only spread through open tiles
                            valid_neighbors.append((new_row, new_col))
                
                if not valid_neighbors:
                    continue

                # Calculate spread for each valid neighbor
                base_rate = GAS_SPREAD_RATE / len(valid_neighbors)
                for n_row, n_col in valid_neighbors:
                    neighbor_gas = old_gases[n_row][n_col]
                    spread_rate = base_rate * 2 if (tile.door or self.grid[n_row][n_col].door) else base_rate
                    
                    # Calculate gas exchange
                    for gas_type in ['o2', 'co2', 'n2']:
                        curr_val = getattr(curr_gas, gas_type)
                        neighbor_val = getattr(neighbor_gas, gas_type)
                        diff = (neighbor_val - curr_val) * spread_rate
                        setattr(tile.gases, gas_type, getattr(tile.gases, gas_type) + diff)

        # Update room gases (optional - if you want rooms to track their total gases)
        for room in self.rooms:
            if room.tiles:
                room_gases = GasCell()
                for tile in room.tiles:
                    room_gases.o2 += tile.gases.o2
                    room_gases.co2 += tile.gases.co2
                    room_gases.n2 += tile.gases.n2
                count = len(room.tiles)
                room.gases = GasCell(
                    room_gases.o2 / count,
                    room_gases.co2 / count,
                    room_gases.n2 / count
                )
            room.update()

    def propagate_power(self, start_tile):
        to_check = {start_tile}
        powered = set()
        
        while to_check:
            tile = to_check.pop()
            if tile not in powered:
                powered.add(tile)
                tile.powered = True
                row, col = tile.row, tile.col
                
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    new_row, new_col = row + dr, col + dc
                    if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                        next_tile = self.grid[new_row][new_col]
                        if next_tile.wire and not next_tile.powered:
                            to_check.add(next_tile)
        
        return powered

    def update_power_network(self):
        for row in self.grid:
            for tile in row:
                tile.powered = False
        
        for row in self.grid:
            for tile in row:
                if tile.component and isinstance(tile.component, Engine):
                    self.propagate_power(tile)

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            self.update_counter += 1
            
            if self.update_counter % 10 == 0:
                self.update_power_network()
                for row in self.grid:
                    for tile in row:
                        if tile.component:
                            if isinstance(tile.component, Engine):
                                tile.component.run()  # This will check O2 and set powered state
                            elif isinstance(tile.component, (OxygenGenerator, Plant, Spac12)):
                                if isinstance(tile.component, (OxygenGenerator, Spac12)):
                                    if tile.powered:
                                        tile.component.generate()
                                else:  # Plant doesn't need power
                                    tile.component.generate()
                            elif isinstance(tile.component, Ventilation):
                                tile.component.update()  # Update ventilation systems
            
            if self.mouse_held:
                self.handle_click(pygame.mouse.get_pos(), is_held=True)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_held = True
                    self.handle_click(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.mouse_held = False
                    self.last_modified_pos = None

            self.win.fill(DARK_BG)
            
            for row in self.grid:
                for tile in row:
                    tile.draw(self.win)
            
            self.draw_sidebar()
            
            if self.update_counter % 5 == 0:
                self.update_gases()
            
            # Draw popup last
            if self.active_popup:
                self.active_popup.draw(self.win)
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    simulator = Simulator()
    simulator.run()
