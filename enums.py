from enum import Enum

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
    VENT_IN = "Input Vent"  # Change this
    VENT_OUT = "Output Vent"  # Add this
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
            "Life Support": [Tool.OXYGEN, Tool.VENT_IN, Tool.VENT_OUT, Tool.PIPE, Tool.PLANT, Tool.SPAC],  # Update this
            "Utility": [Tool.DELETE]
        }
