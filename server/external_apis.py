"""
External API integrations for Aircraft Electrical Fault Analyzer
Includes aviation weather data and fallback mechanisms
"""

import os
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
from functools import lru_cache
import time

# Configure logging
logger = logging.getLogger(__name__)


class WeatherAPIClient:
    """
    Aviation Weather API integration with multiple providers and fallback
    Primary: AVWX (Aviation Weather eXtended) - requires API key
    Secondary: NOAA Aviation Weather Center (free, no key required)
    Fallback: Static default data
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # AVWX Aviation Weather (primary, requires key)
        self.avwx_key = os.getenv('AVIATION_WEATHER_API_KEY')
        self.avwx_base_url = "https://avwx.rest/api"

        # NOAA Aviation Weather (secondary, no key required)
        self.noaa_base_url = "https://aviationweather.gov/api/data/metar"

        # Response cache
        self.cache = {}
        self.cache_duration = 900  # 15 minutes in seconds

        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # seconds between requests

    def get_weather_for_location(self, icao_code: str = "KATL",
                                 latitude: float = None,
                                 longitude: float = None) -> Dict:
        """
        Get aviation weather data with multiple fallback options

        Args:
            icao_code: ICAO airport identifier (e.g., "KATL" for Atlanta)
            latitude: Optional latitude for OpenWeatherMap
            longitude: Optional longitude for OpenWeatherMap

        Returns:
            Dictionary with weather data
        """
        # Check cache first
        cache_key = f"{icao_code}_{latitude}_{longitude}"
        if self._is_cached(cache_key):
            self.logger.info(f"Returning cached weather for {cache_key}")
            return self.cache[cache_key]['data']

        # Apply rate limiting
        self._rate_limit()

        weather_data = None

        # Try primary: AVWX (if API key available)
        if self.avwx_key:
            try:
                self.logger.info(f"Fetching METAR data from AVWX for {icao_code}")
                weather_data = self._fetch_avwx_metar(icao_code)
                weather_data['source'] = 'AVWX Aviation Weather'
            except Exception as e:
                self.logger.warning(f"AVWX API failed: {e}")

        # Try secondary: NOAA Aviation Weather
        if not weather_data:
            try:
                self.logger.info(f"Fetching METAR data from NOAA for {icao_code}")
                weather_data = self._fetch_noaa_metar(icao_code)
                weather_data['source'] = 'NOAA Aviation Weather'
            except Exception as e:
                self.logger.warning(f"NOAA API failed: {e}")

        # Last resort: static fallback data
        if not weather_data:
            self.logger.warning("Using fallback weather data")
            weather_data = self._get_fallback_weather()

        # Cache successful result
        self.cache[cache_key] = {
            'data': weather_data,
            'timestamp': datetime.now()
        }

        return weather_data

    def _fetch_avwx_metar(self, icao_code: str) -> Dict:
        """
        Fetch METAR data from AVWX API
        """
        if not self.avwx_key:
            raise ValueError("AVWX API key not configured")

        url = f"{self.avwx_base_url}/metar/{icao_code}"

        headers = {
            'Authorization': f'BEARER {self.avwx_key}'
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if not data:
            raise ValueError(f"No METAR data available for {icao_code}")

        return self._parse_avwx_metar(data, icao_code)

    def _parse_avwx_metar(self, data: Dict, icao_code: str) -> Dict:
        """
        Parse AVWX METAR data into standardized format
        """
        # Extract temperature and dewpoint (AVWX returns nested objects)
        temp_c = data.get('temperature', {}).get('value', 25) if isinstance(data.get('temperature'), dict) else 25
        dewpoint_c = data.get('dewpoint', {}).get('value', 18) if isinstance(data.get('dewpoint'), dict) else 18

        # Calculate relative humidity (AVWX provides it directly)
        humidity = int(data.get('relative_humidity', 0.65) * 100) if data.get('relative_humidity') else self._calculate_humidity(temp_c, dewpoint_c)

        # Extract wind data
        wind_speed_data = data.get('wind_speed', {})
        wind_speed = wind_speed_data.get('value', 10) if isinstance(wind_speed_data, dict) else 10

        wind_dir_data = data.get('wind_direction', {})
        wind_dir = wind_dir_data.get('value', 270) if isinstance(wind_dir_data, dict) else 270

        # Extract pressure - AVWX gives altimeter in inHg, convert to mb
        altimeter_data = data.get('altimeter', {})
        if isinstance(altimeter_data, dict):
            altimeter_inhg = altimeter_data.get('value', 29.92)
            pressure_mb = altimeter_inhg * 33.86  # Convert inHg to mb
        else:
            pressure_mb = 1013.25

        # Extract visibility
        visibility_data = data.get('visibility', {})
        visibility = visibility_data.get('value', 10) if isinstance(visibility_data, dict) else 10

        # Extract ceiling (cloud base) - AVWX provides in feet
        clouds = data.get('clouds', [])
        ceiling = None
        if clouds:
            for cloud in clouds:
                if cloud.get('type') in ['BKN', 'OVC']:  # Broken or Overcast
                    alt_data = cloud.get('altitude')
                    if isinstance(alt_data, dict):
                        ceiling = alt_data.get('value')
                    elif isinstance(alt_data, (int, float)):
                        ceiling = alt_data
                    if ceiling:
                        break

        # Get flight rules directly from AVWX
        conditions = data.get('flight_rules', 'VFR')

        # Get raw METAR string
        raw_metar = data.get('raw', 'N/A')

        # Get observation time
        time_data = data.get('time', {})
        obs_time = time_data.get('dt', datetime.now().isoformat()) if isinstance(time_data, dict) else datetime.now().isoformat()

        return {
            'temperature_celsius': temp_c,
            'dewpoint_celsius': dewpoint_c,
            'pressure_mb': round(pressure_mb, 1),
            'wind_speed_knots': wind_speed,
            'wind_direction': wind_dir,
            'humidity_percent': humidity,
            'conditions': conditions,
            'visibility': visibility,
            'ceiling': ceiling,
            'raw_metar': raw_metar,
            'station': icao_code,
            'observation_time': obs_time
        }

    def _fetch_noaa_metar(self, icao_code: str) -> Dict:
        """
        Fetch METAR data from NOAA Aviation Weather Center
        """
        params = {
            'ids': icao_code,
            'format': 'json',
            'hours': 1
        }

        response = requests.get(
            self.noaa_base_url,
            params=params,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if not data or len(data) == 0:
            raise ValueError(f"No METAR data available for {icao_code}")

        # Parse first METAR report
        metar = data[0]
        return self._parse_noaa_metar(metar)

    def _parse_noaa_metar(self, metar: Dict) -> Dict:
        """
        Parse NOAA METAR data into standardized format
        """
        # Extract temperature and dewpoint from METAR
        temp_c = metar.get('temp', 25)
        dewpoint_c = metar.get('dewp', 18)

        # Calculate relative humidity from temp and dewpoint
        humidity = self._calculate_humidity(temp_c, dewpoint_c)

        # Extract wind data
        wind_speed = metar.get('wspd', 10)
        wind_dir = metar.get('wdir', 270)

        # Extract pressure
        pressure_mb = metar.get('altim', 29.92) * 33.86  # Convert inHg to mb

        # Determine flight conditions
        visibility = metar.get('visib', '10')
        ceiling = metar.get('ceil', None)
        conditions = self._determine_conditions(visibility, ceiling)

        return {
            'temperature_celsius': temp_c,
            'dewpoint_celsius': dewpoint_c,
            'pressure_mb': round(pressure_mb, 1),
            'wind_speed_knots': wind_speed,
            'wind_direction': wind_dir,
            'humidity_percent': humidity,
            'conditions': conditions,
            'visibility': visibility,
            'ceiling': ceiling,
            'raw_metar': metar.get('rawOb', 'N/A'),
            'station': metar.get('icaoId', 'UNKNOWN'),
            'observation_time': metar.get('obTime', datetime.now().isoformat())
        }

    def _get_fallback_weather(self) -> Dict:
        """
        Return static weather data when all APIs fail
        Standard conditions for diagnostic purposes
        """
        return {
            'temperature_celsius': 25,
            'dewpoint_celsius': 18,
            'pressure_mb': 1013.25,
            'wind_speed_knots': 10,
            'wind_direction': 270,
            'humidity_percent': 65,
            'conditions': 'VFR',
            'visibility': '10',
            'ceiling': None,
            'raw_metar': 'FALLBACK DATA - APIs Unavailable',
            'station': 'DEFAULT',
            'observation_time': datetime.now().isoformat(),
            'source': 'Static Fallback Data',
            'warning': 'Using default weather values - external APIs unavailable'
        }

    def _calculate_humidity(self, temp_c: float, dewpoint_c: float) -> int:
        """
        Calculate relative humidity from temperature and dewpoint
        Using Magnus formula approximation

        Humidity Calculation Fix (Issue 1): Corrected formula to use math.exp()
        instead of pow(10, x). Magnus formula uses natural exponential, not base-10.

        Formula: RH = 100 * exp((17.27 * Td) / (237.7 + Td) - (17.27 * T) / (237.7 + T))
        where T = temperature, Td = dewpoint
        """
        try:
            import math

            # Magnus formula constants
            a = 17.27
            b = 237.7

            # Calculate saturation vapor pressure exponents
            alpha_t = (a * temp_c) / (b + temp_c)
            alpha_d = (a * dewpoint_c) / (b + dewpoint_c)

            # Calculate relative humidity using natural exponential
            # RH = 100 * exp(alpha_d - alpha_t)
            humidity = 100 * math.exp(alpha_d - alpha_t)

            return min(100, max(0, int(humidity)))
        except Exception as e:
            logger.error(f"Humidity calculation error: {e}")
            return 65  # Default humidity

    def _determine_conditions(self, visibility: str, ceiling: int) -> str:
        """
        Determine flight conditions (VFR, MVFR, IFR, LIFR)
        """
        try:
            vis = float(visibility) if visibility else 10
            ceil = ceiling if ceiling else 10000

            if vis >= 5 and ceil >= 3000:
                return 'VFR'  # Visual Flight Rules
            elif vis >= 3 and ceil >= 1000:
                return 'MVFR'  # Marginal VFR
            elif vis >= 1 and ceil >= 500:
                return 'IFR'  # Instrument Flight Rules
            else:
                return 'LIFR'  # Low IFR
        except:
            return 'VFR'  # Default to VFR

    def _is_cached(self, key: str) -> bool:
        """
        Check if cached data is still valid
        """
        if key not in self.cache:
            return False

        cache_entry = self.cache[key]
        age = datetime.now() - cache_entry['timestamp']

        return age.total_seconds() < self.cache_duration

    def _rate_limit(self):
        """
        Apply rate limiting to prevent API abuse
        """
        current_time = time.time()

        if 'last_api_call' in self.last_request_time:
            time_since_last = current_time - self.last_request_time['last_api_call']

            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

        self.last_request_time['last_api_call'] = current_time

    def clear_cache(self):
        """Clear all cached weather data"""
        self.cache.clear()
        self.logger.info("Weather cache cleared")


class TemperatureCorrections:
    """
    Temperature correction calculations for electrical systems
    """

    @staticmethod
    def apply_battery_temp_correction(voltage: float,
                                     temperature_c: float,
                                     nominal_temp_c: float = 25) -> float:
        """
        Apply temperature correction to battery voltage
        Lead-acid batteries: ~0.5% voltage change per °C from 25°C

        Args:
            voltage: Measured battery voltage
            temperature_c: Current temperature in Celsius
            nominal_temp_c: Reference temperature (typically 25°C)

        Returns:
            Temperature-corrected voltage
        """
        temp_diff = temperature_c - nominal_temp_c

        # Battery voltage decreases in cold, increases in heat
        # Approximately -0.5% per °C below 25°C
        correction_factor = 1 + (temp_diff * 0.005)

        # Return the normalized voltage at 25°C
        return voltage / correction_factor

    @staticmethod
    def calculate_cold_cranking_impact(temperature_c: float) -> float:
        """
        Calculate battery capacity reduction in cold weather

        Args:
            temperature_c: Current temperature in Celsius

        Returns:
            Capacity factor (0.0 to 1.0)
        """
        if temperature_c >= 25:
            # Above 25°C, battery at full capacity
            return 1.0
        elif temperature_c >= 0:
            # Between 0°C and 25°C, gradual reduction
            # Approximately 1.2% capacity loss per °C below 25°C
            return 1.0 - ((25 - temperature_c) * 0.012)
        elif temperature_c >= -18:
            # Below 0°C, more severe reduction
            # At -18°C (0°F), battery at ~40% capacity
            return 0.6 + (temperature_c * 0.0111)
        else:
            # Below -18°C, severe capacity loss
            return max(0.3, 0.4 + ((temperature_c + 18) * 0.005))

    @staticmethod
    def calculate_alternator_output_correction(temperature_c: float) -> float:
        """
        Calculate alternator output efficiency based on temperature

        Args:
            temperature_c: Current temperature in Celsius

        Returns:
            Output efficiency factor (0.0 to 1.0)
        """
        if temperature_c < -20:
            # Extreme cold: reduced bearing efficiency
            return 0.85
        elif temperature_c < 0:
            # Cold: slightly reduced efficiency
            return 0.90 + (temperature_c + 20) * 0.0025
        elif temperature_c <= 40:
            # Optimal range
            return 1.0
        elif temperature_c <= 60:
            # Warm: slight reduction due to resistance
            return 1.0 - ((temperature_c - 40) * 0.005)
        else:
            # Hot: significant efficiency loss
            return max(0.75, 0.9 - ((temperature_c - 60) * 0.01))

    @staticmethod
    def calculate_wire_resistance_correction(temperature_c: float,
                                           base_resistance: float = 1.0) -> float:
        """
        Calculate wire resistance change with temperature
        Copper temperature coefficient: 0.393% per °C

        Args:
            temperature_c: Current temperature in Celsius
            base_resistance: Resistance at 20°C

        Returns:
            Temperature-corrected resistance
        """
        temp_coefficient = 0.00393  # Per °C for copper
        temp_diff = temperature_c - 20  # Reference at 20°C

        return base_resistance * (1 + temp_coefficient * temp_diff)


class AircraftDatabaseAPI:
    """
    Mock aircraft database API for aircraft specifications
    In production, this would connect to FAA database or similar
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.aircraft_db = self._load_aircraft_database()

    def _load_aircraft_database(self) -> Dict:
        """
        Load mock aircraft database
        """
        return {
            'C172': {
                'model': 'Cessna 172',
                'electrical_system': '14V',
                'battery_type': 'Lead-Acid',
                'battery_capacity': '35Ah',
                'alternator_output': '60A',
                'critical_circuits': ['Avionics Master', 'Ignition', 'Fuel Pump', 'Lights']
            },
            'PA28': {
                'model': 'Piper Cherokee',
                'electrical_system': '14V',
                'battery_type': 'Lead-Acid',
                'battery_capacity': '35Ah',
                'alternator_output': '70A',
                'critical_circuits': ['Avionics', 'Engine', 'Fuel Pump', 'Landing Gear']
            },
            'SR22': {
                'model': 'Cirrus SR22',
                'electrical_system': '28V',
                'battery_type': 'Lead-Acid',
                'battery_capacity': '24Ah',
                'alternator_output': '100A',
                'critical_circuits': ['CAPS', 'Avionics', 'AHRS', 'Air Data Computer']
            },
            'B737': {
                'model': 'Boeing 737',
                'electrical_system': '28V DC / 115V AC',
                'battery_type': 'Ni-Cd',
                'battery_capacity': '40Ah',
                'generator_output': '120KVA',
                'critical_circuits': ['Essential Bus', 'Emergency Bus', 'Standby Power']
            }
        }

    def get_aircraft_specs(self, aircraft_code: str) -> Dict:
        """
        Get aircraft electrical specifications

        Args:
            aircraft_code: Aircraft type code

        Returns:
            Dictionary with aircraft specifications
        """
        specs = self.aircraft_db.get(
            aircraft_code.upper(),
            self._get_default_specs()
        )

        self.logger.info(f"Retrieved specs for {aircraft_code}: {specs['model']}")
        return specs

    def _get_default_specs(self) -> Dict:
        """
        Return default aircraft specifications
        """
        return {
            'model': 'Generic Light Aircraft',
            'electrical_system': '14V',
            'battery_type': 'Lead-Acid',
            'battery_capacity': '35Ah',
            'alternator_output': '60A',
            'critical_circuits': ['Avionics', 'Engine', 'Fuel Pump', 'Lights']
        }

    def list_available_aircraft(self) -> List[str]:
        """
        List all available aircraft codes
        """
        return list(self.aircraft_db.keys())


# Module initialization
weather_client = WeatherAPIClient()
temp_corrections = TemperatureCorrections()
aircraft_db = AircraftDatabaseAPI()