import pygame
from constants import WHITE, GRAY
import math

class SnackbarMessage:
    def __init__(self, message, width, target_y):
        self.full_message = message
        self.current_message = ""
        self.start_time = pygame.time.get_ticks()
        self.visible = True
        self.width = width
        
        # Simplified animation properties
        self.x = -width - 10  # Start closer
        self.y = target_y
        self.target_x = 10
        self.target_y = target_y
        self.current_y = target_y
        self.opacity = 0
        self.scale = 0.95  # Start closer to final size
        
        # Remove spring physics
        self.anim_progress = 0
        self.duration = 0.3  # Short animation duration
        
        # Typewriter effect
        self.char_index = 0
        self.last_char_time = pygame.time.get_ticks()
        self.char_delay = 30
        
        # Animation states
        self.state = "entering"  # States: entering, active, moving, exiting
        self.anim_progress = 0
        
    def update_animation(self, current_time):
        age = (current_time - self.start_time) / 1000.0
        
        if self.state == "entering":
            # Simple linear movement with cubic easing
            self.anim_progress = min(1.0, age / self.duration)
            self.x = self.lerp(-self.width, self.target_x, self.ease_out_cubic(self.anim_progress))
            self.opacity = min(255, int(255 * self.anim_progress))
            self.scale = self.lerp(0.95, 1.0, self.ease_out_cubic(self.anim_progress))
            
            if self.anim_progress >= 1.0:
                self.state = "active"
                self.start_time = current_time
                
        elif self.state == "active":
            # No floating animation, just stay in place
            self.x = self.target_x
            self.scale = 1.0
            if age > 3.0:
                self.state = "exiting"
                self.start_time = current_time
                
        elif self.state == "moving":
            # Smooth movement to new position
            self.anim_progress = min(1.0, age * 3)  # 0.33 seconds movement
            self.current_y = self.lerp(self.y, self.target_y, self.ease_out_cubic(self.anim_progress))
            
            if self.anim_progress >= 1.0:
                self.state = "active"
                self.y = self.target_y
                self.start_time = current_time
                
        elif self.state == "exiting":
            # Simple fade out
            self.anim_progress = min(1.0, age / self.duration)
            self.opacity = max(0, int(255 * (1 - self.anim_progress)))
            if self.anim_progress >= 1.0:
                self.visible = False

    def update_typewriter(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_char_time > self.char_delay:
            if self.char_index < len(self.full_message):
                self.current_message += self.full_message[self.char_index]
                self.char_index += 1
                self.last_char_time = current_time

    def move_to(self, new_y):
        if self.target_y != new_y:
            self.target_y = new_y
            self.state = "moving"
            self.start_time = pygame.time.get_ticks()
            self.anim_progress = 0

    # Keep only necessary easing functions
    def lerp(self, start, end, progress):
        return start + (end - start) * progress

    def ease_out_cubic(self, x):
        return 1 - pow(1 - x, 3)

class Snackbar:
    def __init__(self, width, height):
        self.messages = []
        try:
            self.font = pygame.font.Font('./fonts/fontalt.ttf', 16)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"Could not load snackbar font: {e}")
            self.font = pygame.font.SysFont('arial', 16)
        self.max_messages = 5
        self.message_height = 25
        self.message_width = 250
        self.padding = 10
        self.base_y = height - (self.message_height + self.padding)
        self.message_queue = []  # Queue for pending messages

    def show(self, message):
        if len(self.messages) >= self.max_messages:
            # Queue the message if we're at max capacity
            self.message_queue.append(message)
            return

        target_y = self.base_y - (len(self.messages) * (self.message_height + 5))
        new_message = SnackbarMessage(message, self.message_width, target_y)
        self.messages.append(new_message)
        self.update_message_positions()

    def update_message_positions(self):
        visible_count = sum(1 for msg in self.messages if msg.state != "exiting")
        current_index = 0
        
        for msg in self.messages:
            if msg.state != "exiting":
                target_y = self.base_y - (current_index * (self.message_height + 5))
                msg.move_to(target_y)
                current_index += 1

    def draw(self, win):
        current_time = pygame.time.get_ticks()
        remaining_messages = []
        
        # Remove invisible messages
        for msg in self.messages:
            if msg.visible:
                msg.update_animation(current_time)
                msg.update_typewriter()
                
                # Only keep visible messages
                remaining_messages.append(msg)
            elif msg.state == "exiting" and msg.opacity <= 0:
                # Message has completed exit animation
                continue
            else:
                remaining_messages.append(msg)

        self.messages = remaining_messages

        # Check if we can show queued messages
        if self.message_queue and len(self.messages) < self.max_messages:
            self.show(self.message_queue.pop(0))

        # Draw remaining messages
        for msg in self.messages:
            if not msg.visible:
                continue
                
            scaled_width = int(self.message_width * msg.scale)
            scaled_height = int(self.message_height * msg.scale)
            
            msg_surface = pygame.Surface((max(1, scaled_width), max(1, scaled_height)), pygame.SRCALPHA)
            
            # Draw background
            background_color = (*GRAY, msg.opacity)
            pygame.draw.rect(msg_surface, background_color, 
                           (0, 0, scaled_width, scaled_height), 
                           border_radius=4)
            
            # Draw text
            text_color = (*WHITE, msg.opacity)
            text_surface = self.font.render(msg.current_message, False, text_color)  # False = no antialiasing
            text_rect = text_surface.get_rect(
                left=5,
                centery=scaled_height // 2
            )
            msg_surface.blit(text_surface, text_rect)
            
            win.blit(msg_surface, (int(msg.x), int(msg.current_y)))

        # Update positions if any messages were removed
        if len(remaining_messages) != len(self.messages):
            self.update_message_positions()
