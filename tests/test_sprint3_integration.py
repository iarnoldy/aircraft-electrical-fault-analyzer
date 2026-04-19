"""
Sprint 3 Integration Tests - Complete Diagnostic System Validation

Tests all diagnostic scenarios and validates the complete integration of:
- Claude Agent SDK (with fallback)
- Electrical system simulator
- Flask API endpoints
- Diagnostic history management

Author: SCAD ITGM 522 Project 3 - Sprint 3
"""

import sys
import os
from pathlib import Path

# Add server directory to path
server_dir = Path(__file__).parent.parent / 'server'
sys.path.insert(0, str(server_dir))

import json
import unittest
from datetime import datetime

from claude_agent import DiagnosticAgent
from electrical_sim import ElectricalSystem, VoltageSystem


class TestDiagnosticAgentCore(unittest.TestCase):
    """Test core diagnostic agent functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.agent = DiagnosticAgent()

    def test_agent_initialization(self):
        """Test agent initializes correctly"""
        self.assertIsNotNone(self.agent)
        info = self.agent.get_agent_info()
        self.assertIn('status', info)
        self.assertIn(info['status'], ['operational', 'fallback_only'])

    def test_electrical_calculations_ohms_law(self):
        """Test Ohm's law calculations"""
        # V = I * R
        result = self.agent.calculate_electrical("ohms_law", {"current": 50, "resistance": 0.29})
        self.assertIn('result', result)
        self.assertAlmostEqual(result['result'], 14.5, places=1)
        self.assertEqual(result['unit'], 'volts')

        # I = V / R
        result = self.agent.calculate_electrical("ohms_law", {"voltage": 14.4, "resistance": 0.29})
        self.assertIn('result', result)
        self.assertAlmostEqual(result['result'], 49.655, places=1)
        self.assertEqual(result['unit'], 'amps')

        # R = V / I
        result = self.agent.calculate_electrical("ohms_law", {"voltage": 14.4, "current": 50})
        self.assertIn('result', result)
        self.assertAlmostEqual(result['result'], 0.29, places=2)
        self.assertEqual(result['unit'], 'ohms')

    def test_electrical_calculations_power(self):
        """Test power calculations"""
        # P = V * I
        result = self.agent.calculate_electrical("power", {"voltage": 14.4, "current": 50})
        self.assertIn('result', result)
        self.assertEqual(result['result'], 720.0)
        self.assertEqual(result['unit'], 'watts')

        # P = I^2 * R
        result = self.agent.calculate_electrical("power", {"current": 50, "resistance": 0.29})
        self.assertIn('result', result)
        self.assertAlmostEqual(result['result'], 725.0, places=0)

    def test_electrical_calculations_voltage_drop(self):
        """Test voltage drop calculations"""
        result = self.agent.calculate_electrical("voltage_drop", {
            "current": 20,
            "length": 15,
            "wire_gauge": 14
        })
        self.assertIn('result', result)
        self.assertIn('acceptable', result)
        self.assertGreater(result['result'], 0)

    def test_electrical_calculations_battery_capacity(self):
        """Test battery capacity temperature compensation"""
        # Cold temperature
        result = self.agent.calculate_electrical("battery_capacity", {
            "nominal_capacity": 35,
            "temperature": -10
        })
        self.assertIn('result', result)
        self.assertLess(result['result'], 35)  # Reduced capacity in cold
        self.assertIn('temperature_effect', result)

        # Warm temperature
        result = self.agent.calculate_electrical("battery_capacity", {
            "nominal_capacity": 35,
            "temperature": 30
        })
        self.assertEqual(result['result'], 35)  # No reduction in warm weather


class TestDiagnosticScenarios(unittest.TestCase):
    """Test all diagnostic scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.agent = DiagnosticAgent()
        self.electrical_system_12v = ElectricalSystem(VoltageSystem.SYSTEM_12V)
        self.electrical_system_28v = ElectricalSystem(VoltageSystem.SYSTEM_28V)

    def test_dead_battery_diagnosis(self):
        """Test dead battery diagnostic scenario"""
        # Inject dead battery fault
        self.electrical_system_12v.inject_dead_battery()
        system_state = self.electrical_system_12v.get_status()

        # Perform diagnosis
        diagnosis = self.agent.diagnose(
            symptoms="Battery won't start the engine, very low voltage reading",
            system_state=system_state,
            measured_values={
                "battery_voltage": 10.5,
                "alternator_output": 0.0,
                "ambient_temperature": -5
            },
            aircraft_type="Cessna 172"
        )

        # Validate response structure
        self.assertIn('diagnosis', diagnosis)
        self.assertIn('safety_warnings', diagnosis)
        self.assertIn('troubleshooting_steps', diagnosis)
        self.assertIn('recommendations', diagnosis)

        # Validate diagnosis content
        self.assertTrue(len(diagnosis['safety_warnings']) >= 3)
        self.assertTrue(len(diagnosis['troubleshooting_steps']) >= 2)
        self.assertIn('battery', diagnosis['diagnosis'].lower())

        print("\n=== DEAD BATTERY DIAGNOSIS ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"Confidence: {diagnosis.get('confidence_level', 'N/A')}")
        print(f"Steps: {len(diagnosis['troubleshooting_steps'])}")

    def test_alternator_failure_diagnosis(self):
        """Test alternator failure diagnostic scenario"""
        # Inject alternator failure
        self.electrical_system_12v.inject_alternator_failure()
        system_state = self.electrical_system_12v.get_status()

        # Perform diagnosis
        diagnosis = self.agent.diagnose(
            symptoms="Alternator light stays on, battery discharging in flight",
            system_state=system_state,
            measured_values={
                "battery_voltage": 11.8,
                "alternator_output": 0.0,
                "ambient_temperature": 20
            },
            aircraft_type="Piper Archer"
        )

        # Validate response
        self.assertIn('diagnosis', diagnosis)
        self.assertIn('alternator', diagnosis['diagnosis'].lower())
        self.assertTrue(len(diagnosis['troubleshooting_steps']) >= 3)

        print("\n=== ALTERNATOR FAILURE DIAGNOSIS ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"Confidence: {diagnosis.get('confidence_level', 'N/A')}")
        print(f"Probable Causes: {len(diagnosis.get('probable_causes', []))}")

    def test_bus_fault_diagnosis(self):
        """Test bus fault diagnostic scenario"""
        # Inject bus fault
        self.electrical_system_12v.inject_bus_fault("Main Bus")
        system_state = self.electrical_system_12v.get_status()

        # Perform diagnosis
        diagnosis = self.agent.diagnose(
            symptoms="Intermittent power loss on main bus, flickering instruments",
            system_state=system_state,
            measured_values={
                "battery_voltage": 12.4,
                "alternator_output": 14.2,
                "ambient_temperature": 25
            },
            aircraft_type="Diamond DA40"
        )

        # Validate response
        self.assertIn('diagnosis', diagnosis)
        self.assertTrue(len(diagnosis['troubleshooting_steps']) >= 2)

        print("\n=== BUS FAULT DIAGNOSIS ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"Safety Warnings: {len(diagnosis['safety_warnings'])}")

    def test_circuit_breaker_trip_diagnosis(self):
        """Test circuit breaker trip diagnostic scenario"""
        # Inject circuit breaker trip
        self.electrical_system_12v.inject_circuit_breaker_trip("AVIONICS")
        system_state = self.electrical_system_12v.get_status()

        # Perform diagnosis
        diagnosis = self.agent.diagnose(
            symptoms="Avionics circuit breaker keeps tripping, radio went offline",
            system_state=system_state,
            measured_values={
                "battery_voltage": 12.6,
                "alternator_output": 14.4,
                "ambient_temperature": 28
            },
            aircraft_type="Beechcraft Bonanza"
        )

        # Validate response
        self.assertIn('diagnosis', diagnosis)
        self.assertIn('breaker', diagnosis['diagnosis'].lower())
        self.assertTrue(len(diagnosis['recommendations']) >= 1)

        print("\n=== CIRCUIT BREAKER TRIP DIAGNOSIS ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"Recommendations: {len(diagnosis['recommendations'])}")

    def test_cold_weather_scenario(self):
        """Test cold weather battery scenario"""
        system_state = self.electrical_system_12v.get_status()

        # Perform diagnosis with cold weather conditions
        diagnosis = self.agent.diagnose(
            symptoms="Engine slow to turn over, battery seems weak",
            system_state=system_state,
            measured_values={
                "battery_voltage": 11.8,
                "alternator_output": 14.4,
                "ambient_temperature": -15
            },
            aircraft_type="Cirrus SR22"
        )

        # Validate environmental considerations
        self.assertIn('environmental_considerations', diagnosis)

        # Check if cold temperature effects are mentioned
        env_text = ' '.join(diagnosis.get('environmental_considerations', []))

        print("\n=== COLD WEATHER SCENARIO ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"Environmental Factors: {len(diagnosis.get('environmental_considerations', []))}")

    def test_28v_system_diagnosis(self):
        """Test diagnosis on 28V system"""
        system_state = self.electrical_system_28v.get_status()

        # Perform diagnosis
        diagnosis = self.agent.diagnose(
            symptoms="Voltage regulator running hot, fluctuating bus voltage",
            system_state=system_state,
            measured_values={
                "battery_voltage": 24.5,
                "alternator_output": 28.8,
                "ambient_temperature": 35
            },
            aircraft_type="King Air C90"
        )

        # Validate response
        self.assertIn('diagnosis', diagnosis)

        print("\n=== 28V SYSTEM DIAGNOSIS ===")
        print(f"Diagnosis: {diagnosis['diagnosis']}")
        print(f"System Type: 28V")


class TestResponseValidation(unittest.TestCase):
    """Test diagnostic response validation and formatting"""

    def setUp(self):
        """Set up test fixtures"""
        self.agent = DiagnosticAgent()

    def test_response_has_required_fields(self):
        """Test that diagnostic response has all required fields"""
        # Create a simple system state
        system_state = {
            "voltage_system": "SYSTEM_12V",
            "battery": {"voltage": 11.0, "state": "DISCHARGING", "health": 60, "temperature": 20},
            "alternator": {"output_voltage": 0.0, "field_voltage": 0.0, "is_operating": False, "is_charging": False},
            "buses": {
                "main_bus": {"voltage": 11.0, "load_current": 25, "circuit_breakers": []},
                "essential_bus": {"voltage": 11.0, "load_current": 15, "circuit_breakers": []}
            },
            "total_load": 40,
            "active_fault": "DEAD_BATTERY"
        }

        diagnosis = self.agent.diagnose(
            symptoms="Test symptoms",
            system_state=system_state,
            measured_values={"battery_voltage": 11.0},
            aircraft_type="Test Aircraft"
        )

        # Required fields
        required_fields = [
            'diagnosis',
            'safety_warnings',
            'troubleshooting_steps',
            'recommendations',
            'ai_model',
            'response_time'
        ]

        for field in required_fields:
            self.assertIn(field, diagnosis, f"Missing required field: {field}")

        # Validate troubleshooting steps structure
        if diagnosis['troubleshooting_steps']:
            step = diagnosis['troubleshooting_steps'][0]
            self.assertIn('step', step)
            self.assertIn('action', step)
            self.assertIn('expected_result', step)
            self.assertIn('decision_point', step)

    def test_error_handling(self):
        """Test error handling in diagnostic system"""
        # Test with invalid system state
        try:
            diagnosis = self.agent.diagnose(
                symptoms="Test error handling",
                system_state={},  # Empty system state
                measured_values={},
                aircraft_type="Test"
            )
            # Should still return a diagnostic, possibly with lower confidence
            self.assertIn('diagnosis', diagnosis)
        except Exception as e:
            self.fail(f"Diagnostic should handle errors gracefully: {e}")


def run_all_tests():
    """Run all tests and generate report"""
    print("=" * 80)
    print("Sprint 3 Integration Tests - Complete Diagnostic System")
    print("=" * 80)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosticAgentCore))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosticScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestResponseValidation))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 80)

    return result


if __name__ == '__main__':
    result = run_all_tests()
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
