"""
Unit Tests for External API Integration
Tests weather API, temperature corrections, and aircraft database
SCAD ITGM 522 Project 3 - Sprint 4
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from external_apis import (
    WeatherAPIClient,
    TemperatureCorrections,
    AircraftDatabaseAPI
)


class TestWeatherAPIClient(unittest.TestCase):
    """Test WeatherAPIClient class"""

    def setUp(self):
        """Set up test fixtures"""
        self.weather_client = WeatherAPIClient()

    def test_initialization(self):
        """Test that weather client initializes correctly"""
        self.assertIsNotNone(self.weather_client)
        self.assertEqual(self.weather_client.cache_duration, 900)
        self.assertEqual(self.weather_client.min_request_interval, 1.0)

    def test_fallback_weather(self):
        """Test that fallback weather data is returned when API fails"""
        fallback = self.weather_client._get_fallback_weather()

        self.assertIn('temperature_celsius', fallback)
        self.assertIn('humidity_percent', fallback)
        self.assertIn('pressure_mb', fallback)
        self.assertIn('source', fallback)

        # Verify sensible defaults
        self.assertEqual(fallback['temperature_celsius'], 25)
        self.assertEqual(fallback['humidity_percent'], 65)
        self.assertEqual(fallback['pressure_mb'], 1013.25)

    def test_humidity_calculation(self):
        """Test humidity calculation from temperature and dewpoint"""
        # Test case: Temp=25°C, Dewpoint=18°C should give ~65% humidity
        humidity = self.weather_client._calculate_humidity(25, 18)

        self.assertIsInstance(humidity, int)
        self.assertGreaterEqual(humidity, 0)
        self.assertLessEqual(humidity, 100)
        self.assertAlmostEqual(humidity, 65, delta=10)

    def test_humidity_calculation_edge_cases(self):
        """Test humidity calculation edge cases"""
        # Saturated air (temp = dewpoint)
        humidity_saturated = self.weather_client._calculate_humidity(20, 20)
        self.assertEqual(humidity_saturated, 100)

        # Very dry air
        humidity_dry = self.weather_client._calculate_humidity(30, 0)
        self.assertLess(humidity_dry, 30)

    def test_flight_conditions_vfr(self):
        """Test VFR conditions determination"""
        conditions = self.weather_client._determine_conditions('10', 5000)
        self.assertEqual(conditions, 'VFR')

    def test_flight_conditions_mvfr(self):
        """Test MVFR conditions determination"""
        conditions = self.weather_client._determine_conditions('4', 2000)
        self.assertEqual(conditions, 'MVFR')

    def test_flight_conditions_ifr(self):
        """Test IFR conditions determination"""
        conditions = self.weather_client._determine_conditions('2', 800)
        self.assertEqual(conditions, 'IFR')

    def test_flight_conditions_lifr(self):
        """Test LIFR conditions determination"""
        conditions = self.weather_client._determine_conditions('0.5', 300)
        self.assertEqual(conditions, 'LIFR')

    def test_cache_functionality(self):
        """Test that caching works correctly"""
        cache_key = "TEST_KEY"
        test_data = {'temperature_celsius': 22}

        # Store in cache
        self.weather_client.cache[cache_key] = {
            'data': test_data,
            'timestamp': datetime.now()
        }

        # Verify cache hit
        self.assertTrue(self.weather_client._is_cached(cache_key))

    def test_cache_expiration(self):
        """Test that cache expires correctly"""
        from datetime import timedelta

        cache_key = "OLD_KEY"
        test_data = {'temperature_celsius': 22}

        # Store old data in cache
        old_time = datetime.now() - timedelta(seconds=1000)
        self.weather_client.cache[cache_key] = {
            'data': test_data,
            'timestamp': old_time
        }

        # Verify cache miss due to expiration
        self.assertFalse(self.weather_client._is_cached(cache_key))

    def test_clear_cache(self):
        """Test cache clearing"""
        self.weather_client.cache['test'] = {'data': {}, 'timestamp': datetime.now()}
        self.weather_client.clear_cache()
        self.assertEqual(len(self.weather_client.cache), 0)

    @patch('external_apis.requests.get')
    def test_noaa_metar_fetch(self, mock_get):
        """Test NOAA METAR data fetching"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = [{
            'icaoId': 'KATL',
            'temp': 25,
            'dewp': 18,
            'altim': 29.92,
            'wspd': 10,
            'wdir': 270,
            'visib': '10',
            'ceil': None,
            'rawOb': 'KATL 121856Z 27010KT 10SM FEW250 25/18 A2992',
            'obTime': '2025-10-11T18:56:00Z'
        }]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Test fetch
        weather_data = self.weather_client._fetch_noaa_metar('KATL')

        self.assertIsNotNone(weather_data)
        self.assertEqual(weather_data['temperature_celsius'], 25)
        self.assertEqual(weather_data['station'], 'KATL')

    @patch('external_apis.requests.get')
    def test_api_timeout_handling(self, mock_get):
        """Test handling of API timeouts"""
        import requests

        # Simulate timeout
        mock_get.side_effect = requests.Timeout("Connection timeout")

        # Should return fallback data without raising exception
        weather_data = self.weather_client.get_weather_for_location('KATL')

        self.assertIsNotNone(weather_data)
        self.assertEqual(weather_data['source'], 'Static Fallback Data')


class TestTemperatureCorrections(unittest.TestCase):
    """Test temperature correction calculations"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_corr = TemperatureCorrections()

    def test_battery_temp_correction_normal(self):
        """Test battery voltage correction at normal temperature"""
        # At 25°C (reference temp), no correction should be applied
        voltage = 12.6
        corrected = self.temp_corr.apply_battery_temp_correction(voltage, 25)

        self.assertAlmostEqual(corrected, voltage, places=2)

    def test_battery_temp_correction_cold(self):
        """Test battery voltage correction in cold weather"""
        # At 0°C, voltage should be lower than measured
        voltage = 12.6
        corrected = self.temp_corr.apply_battery_temp_correction(voltage, 0)

        # Corrected voltage should be higher (indicating battery health is better than cold reading)
        self.assertGreater(corrected, voltage)

    def test_battery_temp_correction_hot(self):
        """Test battery voltage correction in hot weather"""
        # At 40°C, voltage should be higher than measured
        voltage = 12.6
        corrected = self.temp_corr.apply_battery_temp_correction(voltage, 40)

        # Corrected voltage should be lower (indicating battery is actually lower than hot reading)
        self.assertLess(corrected, voltage)

    def test_cold_cranking_impact_normal(self):
        """Test cold cranking impact at normal temperature"""
        impact = self.temp_corr.calculate_cold_cranking_impact(25)
        self.assertEqual(impact, 1.0)

    def test_cold_cranking_impact_mild_cold(self):
        """Test cold cranking impact in mild cold"""
        impact = self.temp_corr.calculate_cold_cranking_impact(10)

        self.assertLess(impact, 1.0)
        self.assertGreater(impact, 0.7)

    def test_cold_cranking_impact_freezing(self):
        """Test cold cranking impact at freezing"""
        impact = self.temp_corr.calculate_cold_cranking_impact(-18)

        self.assertLess(impact, 0.5)
        self.assertGreater(impact, 0.3)

    def test_cold_cranking_impact_extreme_cold(self):
        """Test cold cranking impact in extreme cold"""
        impact = self.temp_corr.calculate_cold_cranking_impact(-30)

        self.assertLess(impact, 0.4)
        self.assertGreaterEqual(impact, 0.3)

    def test_cold_cranking_impact_hot(self):
        """Test cold cranking impact in hot weather"""
        impact = self.temp_corr.calculate_cold_cranking_impact(35)
        self.assertEqual(impact, 1.0)

    def test_alternator_efficiency_normal(self):
        """Test alternator efficiency at normal temperature"""
        efficiency = self.temp_corr.calculate_alternator_output_correction(25)
        self.assertEqual(efficiency, 1.0)

    def test_alternator_efficiency_cold(self):
        """Test alternator efficiency in cold weather"""
        efficiency = self.temp_corr.calculate_alternator_output_correction(-10)

        self.assertLess(efficiency, 1.0)
        self.assertGreater(efficiency, 0.85)

    def test_alternator_efficiency_hot(self):
        """Test alternator efficiency in hot weather"""
        efficiency = self.temp_corr.calculate_alternator_output_correction(55)

        self.assertLess(efficiency, 1.0)
        self.assertGreater(efficiency, 0.75)

    def test_wire_resistance_correction(self):
        """Test wire resistance temperature correction"""
        base_resistance = 1.0  # 1 ohm at 20°C

        # At reference temperature
        resistance_20c = self.temp_corr.calculate_wire_resistance_correction(20, base_resistance)
        self.assertEqual(resistance_20c, base_resistance)

        # In cold weather, resistance should decrease
        resistance_cold = self.temp_corr.calculate_wire_resistance_correction(-10, base_resistance)
        self.assertLess(resistance_cold, base_resistance)

        # In hot weather, resistance should increase
        resistance_hot = self.temp_corr.calculate_wire_resistance_correction(50, base_resistance)
        self.assertGreater(resistance_hot, base_resistance)

    def test_wire_resistance_copper_coefficient(self):
        """Test that wire resistance uses correct copper coefficient"""
        # Copper coefficient is 0.393% per °C
        base_resistance = 10.0
        temp_diff = 30  # 30°C above reference

        corrected = self.temp_corr.calculate_wire_resistance_correction(50, base_resistance)

        expected = base_resistance * (1 + 0.00393 * temp_diff)
        self.assertAlmostEqual(corrected, expected, places=4)


class TestAircraftDatabaseAPI(unittest.TestCase):
    """Test aircraft database API"""

    def setUp(self):
        """Set up test fixtures"""
        self.aircraft_db = AircraftDatabaseAPI()

    def test_initialization(self):
        """Test database initialization"""
        self.assertIsNotNone(self.aircraft_db.aircraft_db)
        self.assertGreater(len(self.aircraft_db.aircraft_db), 0)

    def test_get_cessna_specs(self):
        """Test retrieving Cessna 172 specifications"""
        specs = self.aircraft_db.get_aircraft_specs('C172')

        self.assertIsNotNone(specs)
        self.assertEqual(specs['model'], 'Cessna 172')
        self.assertEqual(specs['electrical_system'], '14V')
        self.assertIn('critical_circuits', specs)

    def test_get_piper_specs(self):
        """Test retrieving Piper Cherokee specifications"""
        specs = self.aircraft_db.get_aircraft_specs('PA28')

        self.assertIsNotNone(specs)
        self.assertEqual(specs['model'], 'Piper Cherokee')
        self.assertEqual(specs['electrical_system'], '14V')

    def test_get_cirrus_specs(self):
        """Test retrieving Cirrus SR22 specifications"""
        specs = self.aircraft_db.get_aircraft_specs('SR22')

        self.assertIsNotNone(specs)
        self.assertEqual(specs['model'], 'Cirrus SR22')
        self.assertEqual(specs['electrical_system'], '28V')
        self.assertIn('CAPS', specs['critical_circuits'])

    def test_get_boeing_specs(self):
        """Test retrieving Boeing 737 specifications"""
        specs = self.aircraft_db.get_aircraft_specs('B737')

        self.assertIsNotNone(specs)
        self.assertEqual(specs['model'], 'Boeing 737')
        self.assertIn('28V', specs['electrical_system'])

    def test_unknown_aircraft(self):
        """Test handling of unknown aircraft type"""
        specs = self.aircraft_db.get_aircraft_specs('UNKNOWN')

        self.assertIsNotNone(specs)
        self.assertEqual(specs['model'], 'Generic Light Aircraft')

    def test_case_insensitive(self):
        """Test that aircraft lookup is case-insensitive"""
        specs_upper = self.aircraft_db.get_aircraft_specs('C172')
        specs_lower = self.aircraft_db.get_aircraft_specs('c172')

        self.assertEqual(specs_upper['model'], specs_lower['model'])

    def test_list_available_aircraft(self):
        """Test listing available aircraft"""
        aircraft_list = self.aircraft_db.list_available_aircraft()

        self.assertIsInstance(aircraft_list, list)
        self.assertGreater(len(aircraft_list), 0)
        self.assertIn('C172', aircraft_list)
        self.assertIn('PA28', aircraft_list)


class TestIntegration(unittest.TestCase):
    """Integration tests for combined API functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.weather_client = WeatherAPIClient()
        self.temp_corr = TemperatureCorrections()
        self.aircraft_db = AircraftDatabaseAPI()

    def test_complete_diagnostic_context(self):
        """Test building complete diagnostic context with all APIs"""
        # Get weather data
        weather = self.weather_client._get_fallback_weather()

        # Get aircraft specs
        aircraft = self.aircraft_db.get_aircraft_specs('C172')

        # Calculate temperature effects
        temperature = weather['temperature_celsius']
        battery_capacity = self.temp_corr.calculate_cold_cranking_impact(temperature)
        alternator_eff = self.temp_corr.calculate_alternator_output_correction(temperature)

        # Verify all components work together
        self.assertIsNotNone(weather)
        self.assertIsNotNone(aircraft)
        self.assertIsInstance(battery_capacity, float)
        self.assertIsInstance(alternator_eff, float)

    def test_cold_weather_scenario(self):
        """Test complete cold weather scenario"""
        cold_temp = -15

        # Calculate impacts
        battery_capacity = self.temp_corr.calculate_cold_cranking_impact(cold_temp)
        alternator_eff = self.temp_corr.calculate_alternator_output_correction(cold_temp)

        measured_voltage = 11.8
        corrected_voltage = self.temp_corr.apply_battery_temp_correction(
            measured_voltage,
            cold_temp
        )

        # In cold weather, battery appears weaker
        self.assertLess(battery_capacity, 0.7)
        self.assertLess(alternator_eff, 1.0)
        self.assertGreater(corrected_voltage, measured_voltage)

    def test_hot_weather_scenario(self):
        """Test complete hot weather scenario"""
        hot_temp = 45

        # Calculate impacts
        battery_capacity = self.temp_corr.calculate_cold_cranking_impact(hot_temp)
        alternator_eff = self.temp_corr.calculate_alternator_output_correction(hot_temp)

        measured_voltage = 13.2
        corrected_voltage = self.temp_corr.apply_battery_temp_correction(
            measured_voltage,
            hot_temp
        )

        # In hot weather, battery appears stronger but may be degrading
        self.assertEqual(battery_capacity, 1.0)  # Capacity unaffected
        self.assertLess(alternator_eff, 1.0)  # Alternator less efficient
        self.assertLess(corrected_voltage, measured_voltage)


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWeatherAPIClient))
    suite.addTests(loader.loadTestsFromTestCase(TestTemperatureCorrections))
    suite.addTests(loader.loadTestsFromTestCase(TestAircraftDatabaseAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_tests()

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 70)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)