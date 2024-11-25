import pygame
import sys
import math
from typing import List, Set
from enum import Enum
from constants import *
from enums import Mode, Tool
from gas import GasCell
from room import Room, RoomInfoPopup
from components import Engine, OxygenGenerator, InputVent, OutputVent, Plant, Spac12  # Update imports
from snackbar import Snackbar
from tile import Tile
import time
from ui import UI

class Simulator:
    def __init__(self):
        pygame.init()
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Room Pressure Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 20)
        
        self.mode = Mode.CREATE
        self.selected_tool = Tool.WALL
        self.grid = [[Tile(row, col, self) for col in range(COLS)] for row in range(ROWS)]
        self.rooms = []
        self.selected_tiles = []
        self.mouse_held = False
        self.last_modified_pos = None
        self.powered_tiles = set()
        self.update_counter = 0
        self.active_popup = None
        self.closing_popup = None
        self.snackbar = Snackbar(WIDTH, HEIGHT)
        
        # Initialize UI
        self.ui = UI(self.win, self.font)
        
        # Initialize all tiles as vacuum (no room)
        for row in self.grid:
            for tile in row:
                tile.room = None
                tile.gases = GasCell()
                # Initialize the tile as vacuum
                self.update_vacuum_state(tile)

    def ease_out_cubic(self, x):
        return 1 - pow(1 - x, 3)

    def ease_in_out_cubic(self, x):
        return 4 * x * x * x if x < 0.5 else 1 - pow(-2 * x + 2, 3) / 2

    def flood_fill(self, start_tile) -> Set['Tile']:
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
        # First check if clicking any UI elements
        if self.ui.is_clicking_ui(pos):
            # Check for toggle button click
            toggle_x = WIDTH - 20 if not self.ui.sidebar_visible else GRID_SIZE + self.ui.game_view_offset - 20
            toggle_btn = pygame.Rect(toggle_x, HEIGHT // 2 - 40, 20, 80)
            if toggle_btn.collidepoint(pos) and not is_held:
                self.ui.toggle_sidebar()
                return

            # Check sidebar clicks if visible
            if self.ui.sidebar_animation > 0:
                sidebar_visible_width = SIDEBAR_WIDTH * self.ui.sidebar_animation
                if pos[0] >= WIDTH - sidebar_visible_width:
                    if not is_held:
                        y = pos[1]
                        y_pos = 10
                        
                        # Mode buttons
                        for mode in Mode:
                            if y_pos <= y < y_pos + 30:
                                self.mode = mode
                                return
                            y_pos += 40

                        if self.mode == Mode.CREATE:
                            # Tool categories
                            for category, tools in Tool.get_categories().items():
                                y_pos += 35  # Skip category header
                                for tool in tools:
                                    if y_pos <= y < y_pos + 30:
                                        self.selected_tool = tool
                                        return
                                    y_pos += 30
                                y_pos += 10
            return  # Important: return here to prevent grid interaction when clicking UI

        # Rest of the method remains unchanged for grid interaction
        game_pos = (pos[0] - self.ui.game_view_offset, pos[1])
        
        # Only process grid clicks if within game area
        if 0 <= game_pos[0] < GRID_SIZE:
            # Convert to integers for grid indices
            row = int(game_pos[1] // TILE_SIZE)
            col = int(game_pos[0] // TILE_SIZE)
            
            # Ensure coordinates are within grid bounds
            if 0 <= row < ROWS and 0 <= col < COLS:
                if is_held and (row, col) == self.last_modified_pos:
                    return
                    
                self.last_modified_pos = (row, col)
                tile = self.grid[row][col]
                
                if self.mode == Mode.CREATE:
                    if self.selected_tool == Tool.DELETE:
                        # Delete walls, doors, wires, and pipes
                        if tile.component:
                            tile.component = None
                            tile.damage = 0  # Reset damage when component is removed
                        if tile.wire or tile.pipe:
                            tile.wire = False
                            tile.pipe = False
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
                        tile.pipe = False
                        tile.component = None
                    elif self.selected_tool == Tool.DOOR:
                        tile.door = True
                        tile.wall = False
                        tile.component = None
                    elif self.selected_tool in [Tool.ENGINE, Tool.OXYGEN, Tool.VENT_IN, Tool.VENT_OUT, 
                                             Tool.PLANT, Tool.SPAC, Tool.PIPE]:
                        if self.selected_tool == Tool.PIPE:
                            tile.pipe = True
                        else:
                            if not tile.wall and not tile.door:
                                if self.selected_tool == Tool.SPAC:
                                    # For SPAC, we want to place it in vacuum (no room)
                                    if not tile.room:
                                        tile.component = Spac12(None)
                                        tile.component.tile = tile
                                        self.snackbar.show(f"{self.selected_tool.value} placed successfully.")
                                    else:
                                        self.snackbar.show("SPAC-12 can only be placed in vacuum!")
                                else:
                                    room_tiles = self.flood_fill(tile)
                                    if room_tiles:  # Only create room if enclosed
                                        # Create room if tile isn't already in one
                                        room = tile.room or self.create_room(room_tiles)
                                        
                                        if self.selected_tool == Tool.ENGINE:
                                            tile.component = Engine(room)
                                        elif self.selected_tool == Tool.OXYGEN:
                                            tile.component = OxygenGenerator(room)
                                        elif self.selected_tool == Tool.VENT_IN:
                                            tile.component = InputVent(room)
                                        elif self.selected_tool == Tool.VENT_OUT:
                                            tile.component = OutputVent(room)
                                        elif self.selected_tool == Tool.PLANT:
                                            tile.component = Plant(room)
                                        
                                        if tile.component:
                                            tile.component.tile = tile
                                            self.snackbar.show(f"{self.selected_tool.value} placed successfully.")
                    
                elif self.mode == Mode.INSPECT:
                    # Close popup when clicking a non-room tile
                    if not tile.room:
                        if self.active_popup:
                            self.closing_popup = self.active_popup
                            self.closing_popup.close()
                            self.active_popup = None
                    else:
                        # Only show popup and snackbar if we're not already inspecting this room
                        if not self.active_popup or self.active_popup.room != tile.room:
                            if self.active_popup:
                                self.closing_popup = self.active_popup
                                self.closing_popup.close()
                            self.active_popup = RoomInfoPopup(tile.room, (game_pos[0], game_pos[1]))
                            self.snackbar.show("Room inspected.")

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

        # Update room gases
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
        # Reset power state for all tiles
        for row in self.grid:
            for tile in row:
                tile.powered = False
        
        # Propagate power from engines
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
                            elif isinstance(tile.component, OxygenGenerator):
                                if tile.powered:
                                    tile.component.generate()
                            elif isinstance(tile.component, Plant):
                                tile.component.generate()  # Plant doesn't need power
                            elif isinstance(tile.component, Spac12):
                                tile.component.generate()  # SPAC doesn't need power
                            # Update this section to use new vent classes
                            elif isinstance(tile.component, (InputVent, OutputVent)):
                                tile.component.update()  # Update ventilation systems
            
            if self.mouse_held:
                self.handle_click(pygame.mouse.get_pos(), is_held=True)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (4, 5) and self.ui.sidebar_animation > 0:  # Mouse wheel
                        self.ui.handle_scroll(event)
                    else:
                        self.mouse_held = True
                        self.handle_click(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button not in (4, 5):  # Ignore mouse wheel
                        self.mouse_held = False
                        self.last_modified_pos = None

            self.win.fill(DARK_BG)
            
            # Create game view surface
            game_view_surface = pygame.Surface((GRID_SIZE, HEIGHT))
            game_view_surface.fill(DARK_BG)
            
            # Draw tiles to game surface
            for row in self.grid:
                for tile in row:
                    tile.draw(game_view_surface)
            
            # Draw game view with offset
            self.win.blit(game_view_surface, (self.ui.game_view_offset, 0))
            
            # Draw sidebar using UI class
            self.ui.draw_sidebar(self.mode, self.selected_tool)
            
            if self.update_counter % 5 == 0:
                self.update_gases()
            
            # Draw popups with adjusted positions
            if self.closing_popup and self.closing_popup.visible:
                # Adjust popup position based on game view offset
                self.closing_popup.rect.x = self.closing_popup.rect.x + self.ui.game_view_offset
                self.closing_popup.draw(self.win)
                self.closing_popup.rect.x = self.closing_popup.rect.x - self.ui.game_view_offset
                if not self.closing_popup.visible:
                    self.closing_popup = None
            if self.active_popup:
                # Adjust popup position based on game view offset
                self.active_popup.rect.x = self.active_popup.rect.x + self.ui.game_view_offset
                self.active_popup.draw(self.win)
                self.active_popup.rect.x = self.active_popup.rect.x - self.ui.game_view_offset
            
            # Draw snackbar on top
            self.snackbar.draw(self.win)
            
            pygame.display.flip()



        pygame.quit()
        pygame.quit()

    def update_vacuum_state(self, tile):
        """Mark a tile as vacuum if it's not part of a room and not a wall"""
        if not tile.room and not tile.wall:
            room_tiles = self.flood_fill(tile)
            if not room_tiles:  # If flood fill returns empty set, it's vacuum
                tile.room = None  # Ensure it's None to mark as vacuum
