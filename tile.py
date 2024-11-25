import pygame
from constants import *
from enums import Mode
from gas import GasCell
from components import Engine, OxygenGenerator, InputVent, OutputVent, Plant, Spac12  # Update imports

class Tile:
    def __init__(self, row, col, simulator):
        self.row = row
        self.col = col
        self.simulator = simulator
        self.x = col * TILE_SIZE
        self.y = row * TILE_SIZE
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.wall = False
        self.door = False
        self.room = None
        self.component = None
        self.wire = False
        self.pipe = False
        self.powered = False
        self.gases = GasCell()
        self.damage = 0.0
    
    def draw(self, win):
        # Set base color
        color = VACUUM_COLOR if not (self.wall or self.room) else DARK_GRID if not self.wall else GRAY
        if self.door:
            color = YELLOW
        pygame.draw.rect(win, color, self.rect)
        
        if self.wire:
            # Draw wire connections
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = self.row + dr, self.col + dc
                if (0 <= new_row < ROWS and 
                    0 <= new_col < COLS and 
                    self.simulator.grid[new_row][new_col].wire):
                    start_x = self.x + TILE_SIZE // 2
                    start_y = self.y + TILE_SIZE // 2
                    end_x = start_x + dc * TILE_SIZE
                    end_y = start_y + dr * TILE_SIZE
                    color_line = ORANGE if self.powered else RED
                    pygame.draw.line(win, color_line, (start_x, start_y), 
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

        if self.pipe:
            # Draw pipe connections
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = self.row + dr, self.col + dc
                if (0 <= new_row < ROWS and 
                    0 <= new_col < COLS and 
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
                
        if self.room and self.simulator.mode == Mode.INSPECT:
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
        
        # Fix multiline expression
        base_color = (
            RED if isinstance(self.component, Engine)
            else GREEN if isinstance(self.component, OxygenGenerator)
            else BLUE if isinstance(self.component, (InputVent, OutputVent))
            else (0, 128, 0) if isinstance(self.component, Plant)
            else (128, 0, 128) if isinstance(self.component, Spac12)
            else None
        )
                        
        if isinstance(self.component, Engine) and not self.powered:
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
