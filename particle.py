import pygame
import random

class Particle:
    def __init__(self, x, y, vx, vy, lifespan, color, reverse_fade=False):
        self.x = x
        self.y = y
        self.vx = vx + random.uniform(-0.2, 0.2)
        self.vy = vy + random.uniform(-0.2, 0.2)
        self.lifespan = lifespan
        self.color = color
        self.age = 0
        self.reverse_fade = reverse_fade

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.age += 1

    def draw(self, surface):
        if self.is_alive():
            # Calculate alpha based on age and whether to reverse the fade
            if self.reverse_fade:
                alpha = min(255, int(255 * (self.age / self.lifespan)))
            else:
                alpha = max(0, 255 - int(255 * (self.age / self.lifespan)))
                
            particle_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, (*self.color, alpha), (2, 2), 2)
            surface.blit(particle_surface, (self.x, self.y))

    def is_alive(self):
        return self.age < self.lifespan
