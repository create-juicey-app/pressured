from gas import GasCell
from constants import (
    MIN_N2_FOR_ENGINE, PLANT_O2_RATE, PLANT_CO2_CONSUMPTION, 
    SPAC_N2_RATE, ROWS, COLS, TILE_SIZE, CYAN  # Add TILE_SIZE here
)
from particle import Particle  # Add this import
import random
import math

class Engine:
    def __init__(self, room):
        self.room = room
        self.n2_consumption = 8  # N2 consumption rate
        self.o2_consumption = 4  # O2 consumption rate when running
        self.powered = False
        
    def run(self):
        if not hasattr(self, 'tile'):
            self.powered = False
            return
            
        # First check if we have both gases above minimum thresholds
        if (self.tile.gases.n2 > 0 and self.tile.gases.o2 > 0 and
            self.tile.gases.n2 >= MIN_N2_FOR_ENGINE and 
            self.tile.gases.o2 >= self.o2_consumption):
            # We have enough gas, consume it and generate power
            self.tile.gases.consume_gas('N2', self.n2_consumption)
            self.tile.gases.consume_gas('O2', self.o2_consumption)
            self.powered = True
        else:
            # Not enough gas, no power
            self.powered = False

class OxygenGenerator:
    def __init__(self, room):
        self.room = room
        self.generation_rate = 10  # Increased for better visibility

    def generate(self):
        if hasattr(self, 'tile') and self.tile.powered:
            self.tile.gases.add_gas('O2', self.generation_rate)

class PipeNetwork:
    def __init__(self):
        self.gases = GasCell()
        self.tiles = []

    def add_tile(self, tile):
        self.tiles.append(tile)
        tile.pipe_network = self

    def remove_tile(self, tile):
        self.tiles.remove(tile)
        tile.pipe_network = None

    def total_pressure(self):
        return self.gases.pressure()

class BaseVentilation:
    def __init__(self, room):
        self.room = room
        self.transfer_rate = 1.0
        self.last_search_time = 0
        self.search_interval = 30
        self.connected_pipes = []

    def find_connected_pipes(self):
        """Find connected pipes and assign them to the same PipeNetwork."""
        visited = set()
        to_check = [(self.tile.row, self.tile.col)]
        self.pipe_network = None

        while to_check:
            row, col = to_check.pop()
            if (row, col) in visited:
                continue

            visited.add((row, col))
            tile = self.tile.simulator.grid[row][col]

            if tile.pipe:
                if tile.pipe_network:
                    self.pipe_network = tile.pipe_network
                else:
                    if not self.pipe_network:
                        self.pipe_network = PipeNetwork()
                    self.pipe_network.add_tile(tile)

                # Add neighboring pipes to check
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < ROWS and 0 <= nc < COLS:
                        neighbor = self.tile.simulator.grid[nr][nc]
                        if neighbor.pipe and (nr, nc) not in visited:
                            to_check.append((nr, nc))

class InputVent(BaseVentilation):
    """Pulls gases from local environment into pipes"""
    def update(self):
        if not hasattr(self, 'tile'):
            return

        self.find_connected_pipes()  # Always find connected pipes

        if self.pipe_network and self.tile.room:
            # Transfer gases from room to pipe network
            for gas_type in ['O2', 'CO2', 'N2']:
                gas_amount = getattr(self.tile.room.gases, gas_type.lower())
                if gas_amount > 0:
                    transfer_amount = min(gas_amount, self.transfer_rate)
                    # Remove gas from each room tile
                    gas_per_tile = transfer_amount / len(self.tile.room.tiles)
                    for tile in self.tile.room.tiles:
                        tile.gases.consume_gas(gas_type, gas_per_tile)
                    # Add gas to pipe network
                    self.pipe_network.gases.add_gas(gas_type, transfer_amount)

            # Only spawn particles if actual gas transfer occurred
            if self.pipe_network.gases.total() > 0:
                self.spawn_particles(aspiring=True)

    def spawn_particles(self, aspiring):
        simulator = self.tile.simulator
        x = self.tile.x + TILE_SIZE // 2
        y = self.tile.y + TILE_SIZE // 2

        # Get gas composition from surrounding tiles
        total_gas = 0
        o2_ratio = co2_ratio = n2_ratio = 0
        
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                new_row = self.tile.row + dr
                new_col = self.tile.col + dc
                if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                    source_tile = self.tile.simulator.grid[new_row][new_col]
                    total_gas += source_tile.gases.total()
                    o2_ratio += source_tile.gases.o2
                    co2_ratio += source_tile.gases.co2
                    n2_ratio += source_tile.gases.n2

        # Only spawn particles if there are gases present
        if total_gas > 0:
            # Determine predominant gas color
            if max(o2_ratio, co2_ratio, n2_ratio) == o2_ratio:
                color = (100, 200, 255)  # Blue for O2
            elif max(o2_ratio, co2_ratio, n2_ratio) == co2_ratio:
                color = (255, 100, 100)  # Red for CO2
            else:
                color = (200, 200, 200)  # Gray for N2

            for _ in range(2):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(0.5, 1.0)
                vx = math.cos(angle) * speed * (-1 if aspiring else 1)
                vy = math.sin(angle) * speed * (-1 if aspiring else 1)
                particle = Particle(
                    x + vx * 5, y + vy * 5, vx, vy, 
                    lifespan=30, color=color, reverse_fade=True)
                simulator.particles.append(particle)

class OutputVent(BaseVentilation):
    """Pushes gases from pipes into room"""
    def update(self):
        if not hasattr(self, 'tile'):
            return

        self.find_connected_pipes()

        if self.pipe_network and self.tile.room:
            gas_transferred = False  # Flag to track if any gas was transferred
            
            # Push gases from pipe network to room
            for gas_type in ['O2', 'CO2', 'N2']:
                gas_amount = getattr(self.pipe_network.gases, gas_type.lower())
                if gas_amount > 0:
                    # Transfer a portion of the gas
                    transfer_amount = min(gas_amount, self.transfer_rate)
                    if transfer_amount > 0:
                        # Remove gas from pipe network
                        self.pipe_network.gases.consume_gas(gas_type, transfer_amount)
                        
                        # Evenly distribute gas to all room tiles
                        gas_per_tile = transfer_amount / len(self.tile.room.tiles)
                        for room_tile in self.tile.room.tiles:
                            room_tile.gases.add_gas(gas_type, gas_per_tile)
                            
                        gas_transferred = True  # Set flag if gas was transferred

            # Spawn particles if any gas was transferred
            if gas_transferred:
                self.spawn_particles(aspiring=False)

    def spawn_particles(self, aspiring):
        simulator = self.tile.simulator
        x = self.tile.x + TILE_SIZE // 2
        y = self.tile.y + TILE_SIZE // 2

        # Get gas composition from pipe network
        if self.pipe_network:
            o2_amount = self.pipe_network.gases.o2
            co2_amount = self.pipe_network.gases.co2
            n2_amount = self.pipe_network.gases.n2
            total_gas = o2_amount + co2_amount + n2_amount

            if total_gas > 0:  # Only spawn if there's gas in the network
                # Determine predominant gas color based on pipe network gases
                if max(o2_amount, co2_amount, n2_amount) == o2_amount:
                    color = (100, 200, 255)  # Blue for O2
                elif max(o2_amount, co2_amount, n2_amount) == co2_amount:
                    color = (255, 100, 100)  # Red for CO2
                else:
                    color = (200, 200, 200)  # Gray for N2

                # Spawn multiple particles for better visibility
                for _ in range(3):  # Increased number of particles
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(1.0, 2.0)  # Increased speed range
                    vx = math.cos(angle) * speed * (-1 if aspiring else 1)
                    vy = math.sin(angle) * speed * (-1 if aspiring else 1)
                    particle = Particle(
                        x, y, vx, vy, 
                        lifespan=45,  # Increased lifespan
                        color=color, 
                        reverse_fade=False)
                    simulator.particles.append(particle)

class Plant:
    def __init__(self, room):
        self.room = room
        self.generation_rate = PLANT_O2_RATE
        self.co2_consumption = PLANT_CO2_CONSUMPTION
        self.n2_consumption = 0.1  # Rate at which plant consumes N2

    def generate(self):
        if hasattr(self, 'tile'):
            # Check both CO2 and N2 levels
            if self.tile.gases.co2 >= self.co2_consumption:
                self.tile.gases.consume_gas('CO2', self.co2_consumption)
                self.tile.gases.add_gas('O2', self.generation_rate)
            # Additional N2 to O2 conversion
            if self.tile.gases.n2 >= self.n2_consumption:
                self.tile.gases.consume_gas('N2', self.n2_consumption)
                self.tile.gases.add_gas('O2', self.generation_rate * 0.5)

class Spac12(BaseVentilation):
    def __init__(self, room):
        super().__init__(room)
        self.generation_rate = SPAC_N2_RATE

    def generate(self):
        if not hasattr(self, 'tile') or self.tile.room:
            return

        self.find_connected_pipes()  # Always find connected pipes

        if self.pipe_network:
            # Generate N2 and add it to the pipe network
            self.pipe_network.gases.add_gas('N2', self.generation_rate)
