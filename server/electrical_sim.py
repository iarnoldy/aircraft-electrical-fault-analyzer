"""
Aircraft Electrical System Simulation Engine

This module simulates a complete aircraft electrical system including:
- Battery (12V/28V systems)
- Alternator with voltage regulation
- Main and essential bus systems
- Circuit breakers with various ratings
- Fault injection capabilities for testing and training

Author: SCAD ITGM 522 Project 3
"""

import json
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import logging

# Configure logging for academic error documentation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoltageSystem(Enum):
    """Aircraft electrical system voltage standards"""
    SYSTEM_12V = 12
    SYSTEM_28V = 28


class FaultType(Enum):
    """Types of electrical faults that can be injected"""
    DEAD_BATTERY = "dead_battery"
    ALTERNATOR_FAILURE = "alternator_failure"
    BUS_FAULT = "bus_fault"
    CIRCUIT_BREAKER_TRIP = "circuit_breaker_trip"
    NONE = "none"


@dataclass
class Battery:
    """
    Aircraft battery simulation

    Attributes:
        voltage_system: 12V or 28V system type
        current_voltage: Current battery voltage
        state_of_charge: Percentage (0-100)
        health: Battery health percentage (0-100)
        temperature: Battery temperature in Celsius
    """
    voltage_system: VoltageSystem
    current_voltage: float
    state_of_charge: float = 100.0
    health: float = 100.0
    temperature: float = 25.0

    def __post_init__(self):
        """Initialize battery with system-appropriate voltage"""
        if self.voltage_system == VoltageSystem.SYSTEM_12V:
            self.nominal_voltage = 12.0
            self.min_voltage = 10.5
            self.max_voltage = 14.4
        else:  # 28V system
            self.nominal_voltage = 28.0
            self.min_voltage = 21.0
            self.max_voltage = 28.8

    def is_healthy(self) -> bool:
        """Check if battery voltage is within acceptable range"""
        return self.current_voltage >= self.min_voltage

    def get_state(self) -> str:
        """Get current battery state description"""
        if not self.is_healthy():
            return "DEAD"
        elif self.state_of_charge < 20:
            return "LOW"
        elif self.state_of_charge < 50:
            return "MODERATE"
        else:
            return "GOOD"


@dataclass
class Alternator:
    """
    Aircraft alternator simulation

    Attributes:
        voltage_system: 12V or 28V system type
        output_voltage: Current alternator output voltage
        field_voltage: Field winding voltage (typically 75% of bus voltage)
        is_operating: Whether alternator is functioning
        output_current: Current output in amperes
    """
    voltage_system: VoltageSystem
    output_voltage: float
    field_voltage: float
    is_operating: bool = True
    output_current: float = 0.0

    def __post_init__(self):
        """Initialize alternator with system-appropriate voltage"""
        if self.voltage_system == VoltageSystem.SYSTEM_12V:
            self.regulated_voltage = 14.4
            self.nominal_field_voltage = 10.8  # 75% of 14.4V
        else:  # 28V system
            self.regulated_voltage = 28.8
            self.nominal_field_voltage = 21.6  # 75% of 28.8V

    def calculate_output(self, load_current: float) -> float:
        """
        Calculate alternator output voltage based on load

        Args:
            load_current: Total electrical load in amperes

        Returns:
            Output voltage accounting for load regulation
        """
        if not self.is_operating:
            return 0.0

        # Simulate voltage drop under load (0.1V per 10A)
        voltage_drop = (load_current / 10.0) * 0.1
        self.output_voltage = max(0, self.regulated_voltage - voltage_drop)
        self.output_current = load_current

        return self.output_voltage


@dataclass
class CircuitBreaker:
    """
    Aircraft circuit breaker simulation

    Attributes:
        name: Circuit breaker identifier
        rating: Current rating in amperes
        is_closed: Whether breaker is closed (conducting)
        current_draw: Current flowing through breaker
    """
    name: str
    rating: float
    is_closed: bool = True
    current_draw: float = 0.0

    def check_overload(self, current: float) -> bool:
        """
        Check if current exceeds breaker rating

        Args:
            current: Current in amperes

        Returns:
            True if breaker should trip
        """
        self.current_draw = current
        if current > self.rating * 1.1:  # 110% of rating trips breaker
            self.is_closed = False
            logger.warning(f"Circuit breaker {self.name} tripped: {current}A exceeds {self.rating}A rating")
            return True
        return False

    def reset(self):
        """Reset (close) the circuit breaker"""
        self.is_closed = True
        self.current_draw = 0.0
        logger.info(f"Circuit breaker {self.name} reset")


@dataclass
class Bus:
    """
    Aircraft electrical bus simulation

    Attributes:
        name: Bus identifier (e.g., "Main Bus", "Essential Bus")
        voltage: Current bus voltage
        load_current: Total current draw on bus
        is_powered: Whether bus is receiving power
        circuit_breakers: List of circuit breakers on this bus
    """
    name: str
    voltage: float
    load_current: float = 0.0
    is_powered: bool = True
    circuit_breakers: List[CircuitBreaker] = None

    def __post_init__(self):
        """Initialize bus with default circuit breakers if none provided"""
        if self.circuit_breakers is None:
            self.circuit_breakers = []

    def calculate_total_load(self) -> float:
        """
        Calculate total electrical load on bus

        Performance Optimization (Issue 6-7): Optimized to avoid unnecessary iterations

        Returns:
            Total current draw in amperes
        """
        # Optimize: Use generator expression with sum (faster than manual accumulation)
        total = sum(breaker.current_draw for breaker in self.circuit_breakers if breaker.is_closed)
        self.load_current = total
        return total

    def update_voltage(self, source_voltage: float, has_fault: bool = False) -> float:
        """
        Update bus voltage based on source and faults

        Args:
            source_voltage: Voltage from power source
            has_fault: Whether bus has intermittent fault

        Returns:
            Updated bus voltage
        """
        if not self.is_powered:
            self.voltage = 0.0
            return 0.0

        # Simulate voltage drop from wiring resistance (0.05V per 10A)
        voltage_drop = (self.load_current / 10.0) * 0.05

        # Add intermittent fault effects
        if has_fault:
            # Intermittent faults cause voltage fluctuations
            import random
            fault_drop = random.uniform(0.5, 2.0)
            voltage_drop += fault_drop

        self.voltage = max(0, source_voltage - voltage_drop)
        return self.voltage


class ElectricalSystem:
    """
    Complete aircraft electrical system simulation

    This class orchestrates the entire electrical system including battery,
    alternator, buses, and circuit protection. It provides fault injection
    capabilities for testing and training purposes.
    """

    def __init__(self, voltage_system: VoltageSystem = VoltageSystem.SYSTEM_12V):
        """
        Initialize electrical system

        Args:
            voltage_system: Either 12V or 28V system
        """
        self.voltage_system = voltage_system

        # Initialize battery
        if voltage_system == VoltageSystem.SYSTEM_12V:
            initial_voltage = 12.6
            regulated_voltage = 14.4
            field_voltage = 10.8
        else:
            initial_voltage = 25.2
            regulated_voltage = 28.8
            field_voltage = 21.6

        self.battery = Battery(
            voltage_system=voltage_system,
            current_voltage=initial_voltage
        )

        # Initialize alternator
        self.alternator = Alternator(
            voltage_system=voltage_system,
            output_voltage=regulated_voltage,
            field_voltage=field_voltage
        )

        # Initialize buses
        self.main_bus = Bus(
            name="Main Bus",
            voltage=initial_voltage,
            circuit_breakers=[
                CircuitBreaker("AVIONICS", 15.0),
                CircuitBreaker("LIGHTS", 10.0),
                CircuitBreaker("FUEL_PUMP", 20.0),
                CircuitBreaker("PITOT_HEAT", 10.0),
            ]
        )

        self.essential_bus = Bus(
            name="Essential Bus",
            voltage=initial_voltage,
            circuit_breakers=[
                CircuitBreaker("INSTRUMENTS", 10.0),
                CircuitBreaker("RADIOS", 15.0),
                CircuitBreaker("BEACON", 5.0),
            ]
        )

        # Fault state
        self.active_fault = FaultType.NONE
        self.fault_parameters: Dict = {}

        logger.info(f"Electrical system initialized: {voltage_system.name}")

    def inject_dead_battery(self):
        """Inject dead battery fault (voltage below minimum threshold)"""
        self.active_fault = FaultType.DEAD_BATTERY
        self.battery.current_voltage = self.battery.min_voltage - 0.5
        self.battery.state_of_charge = 0.0
        self.battery.health = 20.0
        logger.warning("FAULT INJECTED: Dead battery")

    def inject_alternator_failure(self):
        """Inject alternator failure (no charging output)"""
        self.active_fault = FaultType.ALTERNATOR_FAILURE
        self.alternator.is_operating = False
        self.alternator.output_voltage = 0.0
        self.alternator.output_current = 0.0
        logger.warning("FAULT INJECTED: Alternator failure")

    def inject_bus_fault(self, bus_name: str = "Main Bus"):
        """
        Inject bus fault (intermittent power, voltage drops)

        Args:
            bus_name: Name of bus to fault ("Main Bus" or "Essential Bus")
        """
        self.active_fault = FaultType.BUS_FAULT
        self.fault_parameters = {"affected_bus": bus_name}
        logger.warning(f"FAULT INJECTED: Bus fault on {bus_name}")

    def inject_circuit_breaker_trip(self, breaker_name: str = "AVIONICS"):
        """
        Inject circuit breaker trip

        Args:
            breaker_name: Name of circuit breaker to trip
        """
        self.active_fault = FaultType.CIRCUIT_BREAKER_TRIP

        # Find and trip the breaker
        for bus in [self.main_bus, self.essential_bus]:
            for breaker in bus.circuit_breakers:
                if breaker.name == breaker_name:
                    breaker.is_closed = False
                    self.fault_parameters = {
                        "tripped_breaker": breaker_name,
                        "bus": bus.name
                    }
                    logger.warning(f"FAULT INJECTED: Circuit breaker {breaker_name} tripped")
                    return

        logger.error(f"Circuit breaker {breaker_name} not found")

    def clear_faults(self):
        """Clear all active faults and restore system to normal operation"""
        self.active_fault = FaultType.NONE
        self.fault_parameters = {}

        # Restore battery
        if self.voltage_system == VoltageSystem.SYSTEM_12V:
            self.battery.current_voltage = 12.6
        else:
            self.battery.current_voltage = 25.2
        self.battery.state_of_charge = 100.0
        self.battery.health = 100.0

        # Restore alternator
        self.alternator.is_operating = True

        # Reset all circuit breakers
        for bus in [self.main_bus, self.essential_bus]:
            bus.is_powered = True
            for breaker in bus.circuit_breakers:
                breaker.reset()

        logger.info("All faults cleared, system restored to normal")

    def calculate_load(self) -> float:
        """
        Calculate total electrical load on system

        Returns:
            Total current draw in amperes
        """
        main_load = self.main_bus.calculate_total_load()
        essential_load = self.essential_bus.calculate_total_load()
        return main_load + essential_load

    def update_voltages(self):
        """Update all system voltages based on current state and active faults"""
        total_load = self.calculate_load()

        # Determine power source voltage
        if self.alternator.is_operating:
            source_voltage = self.alternator.calculate_output(total_load)
        else:
            source_voltage = self.battery.current_voltage
            # Battery depletes under load when alternator not operating
            depletion_rate = total_load * 0.001  # Simplified depletion model
            self.battery.current_voltage = max(
                self.battery.min_voltage - 1.0,
                self.battery.current_voltage - depletion_rate
            )
            self.battery.state_of_charge = max(
                0,
                ((self.battery.current_voltage - self.battery.min_voltage) /
                 (self.battery.max_voltage - self.battery.min_voltage)) * 100
            )

        # Update bus voltages
        main_has_fault = (
            self.active_fault == FaultType.BUS_FAULT and
            self.fault_parameters.get("affected_bus") == "Main Bus"
        )
        essential_has_fault = (
            self.active_fault == FaultType.BUS_FAULT and
            self.fault_parameters.get("affected_bus") == "Essential Bus"
        )

        self.main_bus.update_voltage(source_voltage, main_has_fault)
        self.essential_bus.update_voltage(source_voltage, essential_has_fault)

        # Update alternator field voltage (75% of bus voltage when operating)
        if self.alternator.is_operating:
            self.alternator.field_voltage = self.main_bus.voltage * 0.75

    def get_status(self) -> Dict:
        """
        Get complete electrical system status

        Performance Optimization (Issue 6-7): Optimized to minimize redundant calculations
        and dictionary constructions. Combines update_voltages and calculate_load calls.

        Returns:
            Dictionary containing all system state information
        """
        # Update system state
        self.update_voltages()

        # Cache total load calculation (used in response)
        total_load = self.calculate_load()

        # Performance optimization: Build circuit breaker lists using list comprehensions
        # This is faster than building them inline in the dict literal
        main_breakers = [
            {
                "name": cb.name,
                "rating": cb.rating,
                "is_closed": cb.is_closed,
                "current_draw": round(cb.current_draw, 2)
            }
            for cb in self.main_bus.circuit_breakers
        ]

        essential_breakers = [
            {
                "name": cb.name,
                "rating": cb.rating,
                "is_closed": cb.is_closed,
                "current_draw": round(cb.current_draw, 2)
            }
            for cb in self.essential_bus.circuit_breakers
        ]

        return {
            "voltage_system": self.voltage_system.value,
            "battery": {
                "voltage": round(self.battery.current_voltage, 2),
                "state_of_charge": round(self.battery.state_of_charge, 1),
                "health": round(self.battery.health, 1),
                "temperature": round(self.battery.temperature, 1),
                "state": self.battery.get_state(),
                "is_healthy": self.battery.is_healthy()
            },
            "alternator": {
                "output_voltage": round(self.alternator.output_voltage, 2),
                "output_current": round(self.alternator.output_current, 2),
                "field_voltage": round(self.alternator.field_voltage, 2),
                "is_operating": self.alternator.is_operating,
                "regulated_voltage": self.alternator.regulated_voltage
            },
            "buses": {
                "main_bus": {
                    "name": self.main_bus.name,
                    "voltage": round(self.main_bus.voltage, 2),
                    "load_current": round(self.main_bus.load_current, 2),
                    "is_powered": self.main_bus.is_powered,
                    "circuit_breakers": main_breakers
                },
                "essential_bus": {
                    "name": self.essential_bus.name,
                    "voltage": round(self.essential_bus.voltage, 2),
                    "load_current": round(self.essential_bus.load_current, 2),
                    "is_powered": self.essential_bus.is_powered,
                    "circuit_breakers": essential_breakers
                }
            },
            "active_fault": self.active_fault.value,
            "fault_parameters": self.fault_parameters,
            "total_load": round(total_load, 2)
        }

    def set_load(self, breaker_name: str, current: float):
        """
        Set electrical load on a specific circuit breaker

        Args:
            breaker_name: Name of circuit breaker
            current: Current draw in amperes
        """
        for bus in [self.main_bus, self.essential_bus]:
            for breaker in bus.circuit_breakers:
                if breaker.name == breaker_name:
                    breaker.current_draw = current
                    # Check if this causes overload
                    breaker.check_overload(current)
                    logger.info(f"Load set on {breaker_name}: {current}A")
                    return

        logger.error(f"Circuit breaker {breaker_name} not found")

    def to_json(self) -> str:
        """
        Serialize system state to JSON

        Returns:
            JSON string representation of system state
        """
        return json.dumps(self.get_status(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ElectricalSystem':
        """
        Deserialize system state from JSON

        Args:
            json_str: JSON string representation of system state

        Returns:
            ElectricalSystem instance with restored state
        """
        data = json.loads(json_str)

        # Determine voltage system
        voltage_value = data.get("voltage_system", 12)
        voltage_system = VoltageSystem.SYSTEM_12V if voltage_value == 12 else VoltageSystem.SYSTEM_28V

        # Create new system
        system = cls(voltage_system=voltage_system)

        # Restore battery state
        battery_data = data.get("battery", {})
        system.battery.current_voltage = battery_data.get("voltage", system.battery.current_voltage)
        system.battery.state_of_charge = battery_data.get("state_of_charge", 100.0)
        system.battery.health = battery_data.get("health", 100.0)
        system.battery.temperature = battery_data.get("temperature", 25.0)

        # Restore alternator state
        alt_data = data.get("alternator", {})
        system.alternator.is_operating = alt_data.get("is_operating", True)
        system.alternator.output_voltage = alt_data.get("output_voltage", system.alternator.regulated_voltage)

        # Restore fault state
        fault_str = data.get("active_fault", "none")
        system.active_fault = FaultType(fault_str)
        system.fault_parameters = data.get("fault_parameters", {})

        logger.info("System state restored from JSON")
        return system


# Example usage and testing
if __name__ == "__main__":
    print("Aircraft Electrical System Simulation Engine")
    print("=" * 60)

    # Create a 12V system
    system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

    # Set some loads
    system.set_load("AVIONICS", 8.5)
    system.set_load("LIGHTS", 6.2)
    system.set_load("FUEL_PUMP", 12.0)
    system.set_load("INSTRUMENTS", 5.5)

    print("\nNormal Operation:")
    print(json.dumps(system.get_status(), indent=2))

    print("\n" + "=" * 60)
    print("Injecting Dead Battery Fault...")
    system.inject_dead_battery()
    print(json.dumps(system.get_status(), indent=2))

    print("\n" + "=" * 60)
    print("Clearing faults and injecting Alternator Failure...")
    system.clear_faults()
    system.inject_alternator_failure()
    print(json.dumps(system.get_status(), indent=2))
