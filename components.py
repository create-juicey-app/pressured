from gas import GasCell
from constants import (
    MIN_O2_FOR_ENGINE, PLANT_O2_RATE, PLANT_CO2_CONSUMPTION, 
    SPAC_CO2_RATE, ROWS, COLS  # Add ROWS and COLS
)

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

class BaseVentilation:
    def __init__(self, room):
        self.room = room
        self.transfer_rate = 1.0
        self.last_search_time = 0
        self.search_interval = 30
        self.connected_pipes = []

    def find_connected_pipes(self):
        """Find all pipe tiles connected to the vent"""
        self.connected_pipes = []
        visited = set()
        to_check = [(self.tile.row, self.tile.col)]
        
        while to_check:
            row, col = to_check.pop()
            if (row, col) in visited:
                continue
                
            visited.add((row, col))
            tile = self.tile.simulator.grid[row][col]
            
            # If we find a pipe, add it
            if tile.pipe:
                self.connected_pipes.append(tile)
            
            # Check neighbors with pipes
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                    next_tile = self.tile.simulator.grid[new_row][new_col]
                    if next_tile.pipe and (new_row, new_col) not in visited:
                        to_check.append((new_row, new_col))

class InputVent(BaseVentilation):
    """Pulls gases from local environment into pipes"""
    def update(self):
        if not hasattr(self, 'tile') or not self.tile.powered:
            return

        if self.tile.simulator.update_counter - self.last_search_time >= self.search_interval:
            self.find_connected_pipes()
            self.last_search_time = self.tile.simulator.update_counter

        # Get gases from surrounding tiles (including diagonals)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:  # Skip the vent's own tile
                    continue
                    
                new_row = self.tile.row + dr
                new_col = self.tile.col + dc
                
                if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                    source_tile = self.tile.simulator.grid[new_row][new_col]
                    
                    # Pull gases from surrounding tiles if they have any
                    if source_tile.gases.total() > 0 and self.connected_pipes:
                        # Pull all types of gases
                        for gas_type in ['O2', 'CO2', 'N2']:
                            current_amount = getattr(source_tile.gases, gas_type.lower())
                            if current_amount > 0:
                                transfer_amount = min(current_amount, self.transfer_rate / 8)  # Divide by 8 for surrounding tiles
                                
                                # Remove gas from source tile
                                source_tile.gases.consume_gas(gas_type, transfer_amount)
                                
                                # Distribute to connected pipes
                                gas_per_pipe = transfer_amount / len(self.connected_pipes)
                                for pipe in self.connected_pipes:
                                    pipe.gases.add_gas(gas_type, gas_per_pipe)

class OutputVent(BaseVentilation):
    """Pushes gases from pipes into room"""
    def update(self):
        if not hasattr(self, 'tile') or not self.tile.powered:
            return

        if self.tile.simulator.update_counter - self.last_search_time >= self.search_interval:
            self.find_connected_pipes()
            self.last_search_time = self.tile.simulator.update_counter

        # Push gases from pipes into room
        for pipe in self.connected_pipes:
            if pipe.gases.co2 > 0:
                transfer_amount = min(pipe.gases.co2, self.transfer_rate)
                # Remove gas from pipe
                pipe.gases.consume_gas('CO2', transfer_amount)
                # Add to room tiles
                gas_per_tile = transfer_amount / len(self.room.tiles)
                for tile in self.room.tiles:
                    tile.gases.add_gas('CO2', gas_per_tile)

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
        self.last_search_time = 0
        self.search_interval = 30
        self.connected_pipes = []

    def find_connected_pipes(self):
        """Find all pipe tiles connected to the SPAC-12"""
        self.connected_pipes = []
        visited = set()
        to_check = [(self.tile.row, self.tile.col)]
        
        while to_check:
            row, col = to_check.pop()
            if (row, col) in visited:
                continue
                
            visited.add((row, col))
            tile = self.tile.simulator.grid[row][col]
            
            # If we find a pipe, add it to our list
            if tile.pipe:
                self.connected_pipes.append(tile)
            
            # Check neighbors with pipes
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < ROWS and 0 <= new_col < COLS):
                    next_tile = self.tile.simulator.grid[new_row][new_col]
                    if next_tile.pipe and (new_row, new_col) not in visited:
                        to_check.append((new_row, new_col))

    def generate(self):
        if not hasattr(self, 'tile') or self.tile.room:  # Don't work if in a room
            return

        # Periodically search for connected pipes
        if self.tile.simulator.update_counter - self.last_search_time >= self.search_interval:
            self.find_connected_pipes()
            self.last_search_time = self.tile.simulator.update_counter

        # If we have connected pipes, distribute CO2 among them
        if self.connected_pipes:
            co2_per_pipe = self.generation_rate / len(self.connected_pipes)
            for pipe_tile in self.connected_pipes:
                pipe_tile.gases.add_gas('CO2', co2_per_pipe)
# genuine piece of shit
# fuck this.
