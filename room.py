from gas import GasCell
from constants import MAX_PRESSURE, MACHINE_DAMAGE_RATE, DARK_GRID, WHITE, ORANGE, GREEN, RED, BLUE, YELLOW
import pygame
import math

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
            # Implement additional damage effects here
    
    def add_gas(self, gas_type: str, amount: float):
        self.gases.add_gas(gas_type, amount)
    
    def consume_gas(self, gas_type: str, amount: float):
        self.gases.consume_gas(gas_type, amount)

    def get_breathability(self):
        o2_level = self.gases.o2
        co2_level = self.gases.co2
        n2_level = self.gases.n2

        # Check for O2 toxicity first (increased threshold)
        if o2_level >= 350:  # Changed from 300
            return "O2 Toxic"

        # Rest of the conditions remain the same
        if (o2_level >= 50 and o2_level <= 100 and 
            co2_level < 4 and n2_level < 4):
            return "Very Breathable"
        
        if (o2_level >= 30 and 
            co2_level < 10 and n2_level < 10):
            return "Breathable"
        
        if (o2_level >= 5 and 
            co2_level < 20 and n2_level < 20):
            return "Barely Breathable"
        
        return "Unbreathable"

class RoomInfoPopup:
    def __init__(self, room, pos):
        self.room = room
        self.target_rect = pygame.Rect(pos[0], pos[1], 300, 200)
        self.rect = pygame.Rect(pos[0], pos[1], 0, 0)  # Start with zero size
        self.visible = True
        self.font = pygame.font.SysFont('arial', 16)
        
        # Animation properties
        self.anim_progress = 0
        self.state = "entering"  # states: entering, visible, exiting
        self.start_time = pygame.time.get_ticks()
        self.duration = 250  # animation duration in ms
        self.opacity = 0
        
    def update(self):
        current_time = pygame.time.get_ticks()
        age = (current_time - self.start_time) / self.duration
        
        if self.state == "entering":
            self.anim_progress = min(1.0, age)
            # Animate size and opacity
            progress = self.ease_out_cubic(self.anim_progress)
            self.rect.width = int(self.target_rect.width * progress)
            self.rect.height = int(self.target_rect.height * progress)
            self.rect.center = self.target_rect.center
            self.opacity = int(255 * progress)
            
            if self.anim_progress >= 1.0:
                self.state = "visible"
                
        elif self.state == "exiting":
            self.anim_progress = min(1.0, age)
            # Animate size and opacity out
            progress = 1.0 - self.ease_out_cubic(self.anim_progress)
            self.rect.width = int(self.target_rect.width * progress)
            self.rect.height = int(self.target_rect.height * progress)
            self.rect.center = self.target_rect.center
            self.opacity = int(255 * progress)
            
            if self.anim_progress >= 1.0:
                self.visible = False
    
    def close(self):
        if self.state != "exiting":
            self.state = "exiting"
            self.start_time = pygame.time.get_ticks()
            self.anim_progress = 0
    
    def ease_out_cubic(self, x):
        return 1 - pow(1 - x, 3)
            
    def draw(self, win):
        if not self.visible:
            return
            
        self.update()
        
        # Create a surface for the popup with alpha channel
        popup_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        
        # Draw background with opacity
        bg_color = (*DARK_GRID, self.opacity)
        pygame.draw.rect(popup_surface, bg_color, popup_surface.get_rect())
        border_color = (*WHITE, self.opacity)
        pygame.draw.rect(popup_surface, border_color, popup_surface.get_rect(), 2)
        
        if self.rect.width < 50 or self.rect.height < 50:  # Skip drawing content if too small
            win.blit(popup_surface, self.rect)
            return
            
        # Draw pressure bar
        pressure_container = pygame.Rect(self.rect.width - 40, 10, 30, 150)
        pygame.draw.rect(popup_surface, (*DARK_GRID, self.opacity), pressure_container)
        pygame.draw.rect(popup_surface, border_color, pressure_container, 1)
        
        pressure_height = min(self.room.pressure() / MAX_PRESSURE, 1) * 150
        pressure_rect = pygame.Rect(
            pressure_container.x,
            pressure_container.bottom - pressure_height,
            pressure_container.width,
            pressure_height
        )
        pygame.draw.rect(popup_surface, (*ORANGE, self.opacity), pressure_rect)
        
        # Draw text information
        x = 10
        y = 10
        
        texts = [
            f"Room Size: {len(self.room.tiles)} tiles",
            f"O2: {self.room.gases.o2:.1f}",
            f"CO2: {self.room.gases.co2:.1f}",
            f"N2: {self.room.gases.n2:.1f}",
            f"Damage: {self.room.damage:.1%}",
            f"Status: {self.room.get_breathability()}",  # Add breathing status
            f"Pressure: {self.room.pressure():.1f}/{MAX_PRESSURE}"
        ]
        
        for text in texts:
            text_surface = self.font.render(text, True, (*WHITE, self.opacity))
            popup_surface.blit(text_surface, (x, y))
            y += 20
        
        # Draw colored status indicator
        status = self.room.get_breathability()
        status_color = GREEN if status == "Very Breathable" else \
                      BLUE if status == "Breathable" else \
                      YELLOW if status == "Barely Breathable" else \
                      ORANGE if status == "O2 Toxic" else RED
                      
        status_rect = pygame.Rect(x + 10, y + len(texts) * 20, 10, 10)
        pygame.draw.circle(popup_surface, (*status_color, self.opacity), 
                         status_rect.center, 5)
        
        # Draw gas composition bar
        bar_width = 200
        bar_height = 20
        x = 10
        y = self.rect.height - 40
        
        # Draw container for gas bar
        pygame.draw.rect(popup_surface, (*DARK_GRID, self.opacity), (x, y, bar_width, bar_height))
        pygame.draw.rect(popup_surface, border_color, (x, y, bar_width, bar_height), 1)
        
        total_gas = self.room.gases.total()
        if total_gas > 0:
            # O2 bar (green)
            o2_width = (self.room.gases.o2 / total_gas) * bar_width
            pygame.draw.rect(popup_surface, (*GREEN, self.opacity), (x, y, o2_width, bar_height))
            
            # CO2 bar (red)
            co2_width = (self.room.gases.co2 / total_gas) * bar_width
            pygame.draw.rect(popup_surface, (*RED, self.opacity), (x + o2_width, y, co2_width, bar_height))
            
            # N2 bar (blue)
            n2_width = (self.room.gases.n2 / total_gas) * bar_width
            pygame.draw.rect(popup_surface, (*BLUE, self.opacity), (x + o2_width + co2_width, y, n2_width, bar_height))
        
        win.blit(popup_surface, self.rect)
