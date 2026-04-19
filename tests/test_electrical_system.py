"""
Unit Tests for Aircraft Electrical System Simulation

Tests electrical system components including:
- Battery voltage and state management
- Alternator output and regulation
- Circuit breaker protection
- Fault injection mechanisms
- System state serialization

Author: SCAD ITGM 522 Project 3
"""

import sys
import os
from pathlib import Path

# Add server directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'server'))

import pytest
import json
from electrical_sim import (
    ElectricalSystem,
    VoltageSystem,
    FaultType,
    Battery,
    Alternator,
    CircuitBreaker,
    Bus
)


class TestBattery:
    """Test Battery class functionality"""

    def test_battery_initialization_12v(self):
        """Test 12V battery initialization"""
        battery = Battery(
            voltage_system=VoltageSystem.SYSTEM_12V,
            current_voltage=12.6
        )

        assert battery.voltage_system == VoltageSystem.SYSTEM_12V
        assert battery.current_voltage == 12.6
        assert battery.nominal_voltage == 12.0
        assert battery.min_voltage == 10.5
        assert battery.max_voltage == 14.4
        assert battery.state_of_charge == 100.0
        assert battery.health == 100.0

    def test_battery_initialization_28v(self):
        """Test 28V battery initialization"""
        battery = Battery(
            voltage_system=VoltageSystem.SYSTEM_28V,
            current_voltage=25.2
        )

        assert battery.voltage_system == VoltageSystem.SYSTEM_28V
        assert battery.current_voltage == 25.2
        assert battery.nominal_voltage == 28.0
        assert battery.min_voltage == 21.0
        assert battery.max_voltage == 28.8

    def test_battery_is_healthy(self):
        """Test battery health check"""
        battery = Battery(
            voltage_system=VoltageSystem.SYSTEM_12V,
            current_voltage=12.6
        )

        assert battery.is_healthy() is True

        battery.current_voltage = 10.0
        assert battery.is_healthy() is False

    def test_battery_get_state(self):
        """Test battery state descriptions"""
        battery = Battery(
            voltage_system=VoltageSystem.SYSTEM_12V,
            current_voltage=12.6
        )

        assert battery.get_state() == "GOOD"

        battery.state_of_charge = 45.0
        assert battery.get_state() == "MODERATE"

        battery.state_of_charge = 15.0
        assert battery.get_state() == "LOW"

        battery.current_voltage = 10.0
        assert battery.get_state() == "DEAD"


class TestAlternator:
    """Test Alternator class functionality"""

    def test_alternator_initialization_12v(self):
        """Test 12V alternator initialization"""
        alternator = Alternator(
            voltage_system=VoltageSystem.SYSTEM_12V,
            output_voltage=14.4,
            field_voltage=10.8
        )

        assert alternator.voltage_system == VoltageSystem.SYSTEM_12V
        assert alternator.regulated_voltage == 14.4
        assert alternator.nominal_field_voltage == 10.8
        assert alternator.is_operating is True

    def test_alternator_initialization_28v(self):
        """Test 28V alternator initialization"""
        alternator = Alternator(
            voltage_system=VoltageSystem.SYSTEM_28V,
            output_voltage=28.8,
            field_voltage=21.6
        )

        assert alternator.voltage_system == VoltageSystem.SYSTEM_28V
        assert alternator.regulated_voltage == 28.8
        assert alternator.nominal_field_voltage == 21.6

    def test_alternator_output_calculation(self):
        """Test alternator output voltage under load"""
        alternator = Alternator(
            voltage_system=VoltageSystem.SYSTEM_12V,
            output_voltage=14.4,
            field_voltage=10.8
        )

        # Test with no load
        output = alternator.calculate_output(0.0)
        assert output == 14.4

        # Test with 10A load (should drop 0.1V)
        output = alternator.calculate_output(10.0)
        assert output == 14.3

        # Test with 20A load (should drop 0.2V)
        output = alternator.calculate_output(20.0)
        assert abs(output - 14.2) < 0.01  # Use approximate comparison for floating point

    def test_alternator_failure(self):
        """Test alternator failure condition"""
        alternator = Alternator(
            voltage_system=VoltageSystem.SYSTEM_12V,
            output_voltage=14.4,
            field_voltage=10.8
        )

        alternator.is_operating = False
        output = alternator.calculate_output(10.0)
        assert output == 0.0


class TestCircuitBreaker:
    """Test CircuitBreaker class functionality"""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization"""
        breaker = CircuitBreaker("AVIONICS", 15.0)

        assert breaker.name == "AVIONICS"
        assert breaker.rating == 15.0
        assert breaker.is_closed is True
        assert breaker.current_draw == 0.0

    def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker under normal load"""
        breaker = CircuitBreaker("AVIONICS", 15.0)

        # Normal load (80% of rating)
        tripped = breaker.check_overload(12.0)
        assert tripped is False
        assert breaker.is_closed is True

    def test_circuit_breaker_trip(self):
        """Test circuit breaker trip on overload"""
        breaker = CircuitBreaker("AVIONICS", 15.0)

        # Overload (120% of rating)
        tripped = breaker.check_overload(18.0)
        assert tripped is True
        assert breaker.is_closed is False

    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset"""
        breaker = CircuitBreaker("AVIONICS", 15.0)

        # Trip the breaker
        breaker.check_overload(20.0)
        assert breaker.is_closed is False

        # Reset
        breaker.reset()
        assert breaker.is_closed is True
        assert breaker.current_draw == 0.0


class TestBus:
    """Test Bus class functionality"""

    def test_bus_initialization(self):
        """Test bus initialization"""
        bus = Bus("Main Bus", 14.0)

        assert bus.name == "Main Bus"
        assert bus.voltage == 14.0
        assert bus.is_powered is True
        assert bus.load_current == 0.0

    def test_bus_load_calculation(self):
        """Test bus total load calculation"""
        bus = Bus("Main Bus", 14.0)
        bus.circuit_breakers = [
            CircuitBreaker("AVIONICS", 15.0),
            CircuitBreaker("LIGHTS", 10.0),
            CircuitBreaker("FUEL_PUMP", 20.0)
        ]

        # Set loads
        bus.circuit_breakers[0].current_draw = 8.5
        bus.circuit_breakers[1].current_draw = 6.2
        bus.circuit_breakers[2].current_draw = 12.0

        total_load = bus.calculate_total_load()
        assert total_load == 8.5 + 6.2 + 12.0
        assert bus.load_current == total_load

    def test_bus_voltage_update(self):
        """Test bus voltage update with load"""
        bus = Bus("Main Bus", 14.0)
        bus.circuit_breakers = [CircuitBreaker("TEST", 10.0)]
        bus.circuit_breakers[0].current_draw = 10.0

        bus.calculate_total_load()
        voltage = bus.update_voltage(14.4, has_fault=False)

        # Should have slight voltage drop from wiring resistance
        assert voltage < 14.4
        assert voltage > 14.0


class TestElectricalSystem:
    """Test complete ElectricalSystem functionality"""

    def test_system_initialization(self):
        """Test electrical system initialization"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        assert system.voltage_system == VoltageSystem.SYSTEM_12V
        assert system.battery is not None
        assert system.alternator is not None
        assert system.main_bus is not None
        assert system.essential_bus is not None
        assert system.active_fault == FaultType.NONE

    def test_system_get_status(self):
        """Test system status retrieval"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        status = system.get_status()

        assert 'battery' in status
        assert 'alternator' in status
        assert 'buses' in status
        assert 'active_fault' in status
        assert status['voltage_system'] == 12

    def test_fault_injection_dead_battery(self):
        """Test dead battery fault injection"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        system.inject_dead_battery()

        assert system.active_fault == FaultType.DEAD_BATTERY
        assert system.battery.current_voltage < system.battery.min_voltage
        assert system.battery.state_of_charge == 0.0
        assert system.battery.health == 20.0

    def test_fault_injection_alternator_failure(self):
        """Test alternator failure fault injection"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        system.inject_alternator_failure()

        assert system.active_fault == FaultType.ALTERNATOR_FAILURE
        assert system.alternator.is_operating is False
        assert system.alternator.output_voltage == 0.0

    def test_fault_injection_bus_fault(self):
        """Test bus fault injection"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        system.inject_bus_fault("Main Bus")

        assert system.active_fault == FaultType.BUS_FAULT
        assert system.fault_parameters.get("affected_bus") == "Main Bus"

    def test_fault_injection_circuit_breaker_trip(self):
        """Test circuit breaker trip fault injection"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        system.inject_circuit_breaker_trip("AVIONICS")

        assert system.active_fault == FaultType.CIRCUIT_BREAKER_TRIP

        # Find the AVIONICS breaker and verify it's open
        avionics_breaker = None
        for bus in [system.main_bus, system.essential_bus]:
            for breaker in bus.circuit_breakers:
                if breaker.name == "AVIONICS":
                    avionics_breaker = breaker
                    break

        assert avionics_breaker is not None
        assert avionics_breaker.is_closed is False

    def test_clear_faults(self):
        """Test fault clearing"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        # Inject a fault
        system.inject_dead_battery()
        assert system.active_fault != FaultType.NONE

        # Clear faults
        system.clear_faults()
        assert system.active_fault == FaultType.NONE
        assert system.battery.is_healthy() is True
        assert system.alternator.is_operating is True

    def test_calculate_load(self):
        """Test total system load calculation"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        system.set_load("AVIONICS", 8.5)
        system.set_load("LIGHTS", 6.2)
        system.set_load("FUEL_PUMP", 12.0)

        total_load = system.calculate_load()
        assert total_load >= 8.5 + 6.2 + 12.0  # May include other loads

    def test_set_load(self):
        """Test setting load on circuit breaker"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        system.set_load("AVIONICS", 10.0)

        # Find the AVIONICS breaker and verify load
        for bus in [system.main_bus, system.essential_bus]:
            for breaker in bus.circuit_breakers:
                if breaker.name == "AVIONICS":
                    assert breaker.current_draw == 10.0

    def test_update_voltages(self):
        """Test voltage update across system"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        system.set_load("AVIONICS", 8.5)
        system.set_load("LIGHTS", 6.2)

        system.update_voltages()

        # Verify alternator is providing power
        assert system.alternator.output_voltage > 0
        assert system.main_bus.voltage > 0
        assert system.essential_bus.voltage > 0

    def test_state_serialization(self):
        """Test JSON serialization and deserialization"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

        system.set_load("AVIONICS", 8.5)
        system.inject_alternator_failure()

        # Serialize to JSON
        json_str = system.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data['active_fault'] == 'alternator_failure'
        assert data['voltage_system'] == 12

    def test_system_28v(self):
        """Test 28V system operation"""
        system = ElectricalSystem(VoltageSystem.SYSTEM_28V)

        status = system.get_status()
        assert status['voltage_system'] == 28
        assert system.battery.nominal_voltage == 28.0
        assert system.alternator.regulated_voltage == 28.8


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
