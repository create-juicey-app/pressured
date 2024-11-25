from dataclasses import dataclass

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

    def mix_with(self, other_gas, rate: float):
        """Mix gases between two cells at the given rate"""
        for gas_type in ['o2', 'co2', 'n2']:
            current = getattr(self, gas_type)
            other = getattr(other_gas, gas_type)
            diff = (other - current) * rate
            setattr(self, gas_type, current + diff)
            setattr(other_gas, gas_type, other - diff)
