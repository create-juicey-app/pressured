import pygame
import time
from enums import Mode, Tool
from constants import *

class UI:
    def __init__(self, win, font):
        self.win = win
        self.font = font
        self.sidebar_visible = True
        self.sidebar_animation = 1.0  # 0.0 = hidden, 1.0 = visible
        self.sidebar_animation_start = 0
        self.sidebar_animation_duration = 0.3
        self.hover_button = None
        self.active_button = None
        self.button_animations = {}  # Store button hover/click animations
        self.game_view_offset = 0  # Offset for the game view
        
        # Add scroll view properties
        self.scroll_y = 0
        self.max_scroll = 0
        self.scroll_speed = 30
        self.visible_height = HEIGHT - 20  # 10px padding top and bottom

    def ease_out_cubic(self, x):
        return 1 - pow(1 - x, 3)

    def ease_in_out_cubic(self, x):
        return 4 * x * x * x if x < 0.5 else 1 - pow(-2 * x + 2, 3) / 2

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self.sidebar_animation_start = time.time()

    def draw_paper_container(self, rect, color, alpha=255, elevation=2, surface=None):
        surface = surface or self.win
        # Draw shadow
        shadow = pygame.Surface((rect.width + elevation * 2, rect.height + elevation * 2), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, int(20 * alpha / 255)))
        shadow_rect = shadow.get_rect(center=(rect.centerx + elevation, rect.centery + elevation))
        surface.blit(shadow, shadow_rect)

        # Draw paper background
        paper = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        paper.fill((*color, alpha))
        surface.blit(paper, rect)

        # Draw highlight edge
        highlight = pygame.Surface((rect.width, 2), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, int(30 * alpha / 255)))
        surface.blit(highlight, rect)

    def draw_button(self, rect, text, color, is_hover=False, is_active=False, alpha=255, surface=None):
        surface = surface or self.win
        button_key = (rect.x, rect.y)
        if button_key not in self.button_animations:
            self.button_animations[button_key] = {'hover': 0.0, 'click': 0.0}

        target_hover = 1.0 if is_hover else 0.0
        target_click = 1.0 if is_active else 0.0
        anim = self.button_animations[button_key]
        
        anim['hover'] += (target_hover - anim['hover']) * 0.2
        anim['click'] += (target_click - anim['click']) * 0.3

        elevation = 2 * (1 - anim['click'])
        hover_expand = 2 * anim['hover']
        animated_rect = rect.inflate(hover_expand, hover_expand)
        
        self.draw_paper_container(animated_rect, color, alpha, elevation, surface)
        
        text_surface = self.font.render(text, True, (255, 255, 255, alpha))
        text_rect = text_surface.get_rect(center=animated_rect.center)
        surface.blit(text_surface, text_rect)

        return animated_rect

    def handle_scroll(self, event):
        if event.button == 4:  # Mouse wheel up
            self.scroll_y = max(0, self.scroll_y - self.scroll_speed)
        elif event.button == 5:  # Mouse wheel down
            self.scroll_y = min(self.max_scroll, self.scroll_y + self.scroll_speed)

    def draw_sidebar(self, mode, selected_tool):
        current_time = time.time()
        if self.sidebar_animation_start > 0:
            progress = (current_time - self.sidebar_animation_start) / self.sidebar_animation_duration
            progress = min(1.0, progress)
            progress = self.ease_in_out_cubic(progress)
            
            target = 1.0 if self.sidebar_visible else 0.0
            self.sidebar_animation = target * progress + (1 - target) * (1 - progress)
            
            if progress >= 1.0:
                self.sidebar_animation_start = 0

        sidebar_x = WIDTH - (SIDEBAR_WIDTH * self.sidebar_animation)
        self.game_view_offset = (WIDTH - GRID_SIZE) * (1 - self.sidebar_animation) / 2
        
        # Draw toggle button
        toggle_x = WIDTH - 20 if not self.sidebar_visible else GRID_SIZE + self.game_view_offset - 20
        toggle_btn = pygame.Rect(toggle_x, HEIGHT // 2 - 40, 20, 80)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = toggle_btn.collidepoint(mouse_pos)
        self.draw_button(toggle_btn, "⋮" if self.sidebar_visible else "⋯", DARK_GRID, is_hover)

        # Create sidebar surface
        sidebar_surface = pygame.Surface((SIDEBAR_WIDTH, HEIGHT), pygame.SRCALPHA)
        y_pos = 10
        
        # Update the button checks
        relative_mouse_pos = (mouse_pos[0] - sidebar_x, mouse_pos[1] + self.scroll_y)

        # Draw mode buttons on sidebar surface
        for mode_option in Mode:
            button_rect = pygame.Rect(10, y_pos - self.scroll_y, SIDEBAR_WIDTH - 20, 30)
            is_hover = button_rect.collidepoint(relative_mouse_pos[0], relative_mouse_pos[1] - self.scroll_y)
            is_active = mode == mode_option
            self.draw_button(
                button_rect, 
                mode_option.value,
                PRIMARY if is_active else UI_SURFACE_LIGHT,
                is_hover,
                is_active,
                surface=sidebar_surface  # Pass surface to draw on
            )
            y_pos += 40

        if mode == Mode.CREATE:
            for category, tools in Tool.get_categories().items():
                # Category header
                header_rect = pygame.Rect(5, y_pos - self.scroll_y, SIDEBAR_WIDTH - 10, 30)
                self.draw_paper_container(header_rect, UI_SURFACE, surface=sidebar_surface)
                title_surface = self.font.render(category, True, UI_ACCENT)
                sidebar_surface.blit(title_surface, (15, y_pos - self.scroll_y + 5))
                y_pos += 35

                # Tool buttons
                for tool in tools:
                    button_rect = pygame.Rect(15, y_pos - self.scroll_y, SIDEBAR_WIDTH - 30, 25)
                    is_hover = button_rect.collidepoint(relative_mouse_pos[0], relative_mouse_pos[1] - self.scroll_y)
                    is_active = selected_tool == tool
                    self.draw_button(
                        button_rect,
                        tool.value,
                        SECONDARY if is_active else UI_SURFACE_LIGHT,
                        is_hover,
                        is_active,
                        surface=sidebar_surface  # Pass surface to draw on
                    )
                    y_pos += 30
                y_pos += 10

        # Update max scroll value
        self.max_scroll = max(0, y_pos - self.visible_height)

        # Draw the sidebar surface
        self.win.blit(sidebar_surface, (sidebar_x, 0))

        # Draw scroll indicators if needed
        if self.max_scroll > 0:
            if self.scroll_y > 0:
                pygame.draw.polygon(sidebar_surface, UI_ACCENT, [
                    (SIDEBAR_WIDTH//2 - 10, 15),
                    (SIDEBAR_WIDTH//2 + 10, 15),
                    (SIDEBAR_WIDTH//2, 5)
                ])
            if self.scroll_y < self.max_scroll:
                pygame.draw.polygon(sidebar_surface, UI_ACCENT, [
                    (SIDEBAR_WIDTH//2 - 10, HEIGHT - 15),
                    (SIDEBAR_WIDTH//2 + 10, HEIGHT - 15),
                    (SIDEBAR_WIDTH//2, HEIGHT - 5)
                ])

    def is_animating(self):
        """Return True if sidebar animation is in progress"""
        return self.sidebar_animation_start > 0

    def is_clicking_ui(self, pos):
        """Return True if the click position is on any UI element"""
        # Treat entire screen as UI during animation
        if self.is_animating():
            return True

        # Check toggle button
        toggle_x = WIDTH - 20 if not self.sidebar_visible else GRID_SIZE + self.game_view_offset - 20
        toggle_btn = pygame.Rect(toggle_x, HEIGHT // 2 - 40, 20, 80)
        if toggle_btn.collidepoint(pos):
            return True
            
        # Check sidebar area if visible
        if self.sidebar_animation > 0:
            sidebar_x = WIDTH - (SIDEBAR_WIDTH * self.sidebar_animation)
            if pos[0] >= sidebar_x:
                return True
                
        return False
