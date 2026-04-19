"""
Claude Agent SDK Integration - Complete Sprint 3 Implementation

This module provides full AI-powered aircraft electrical diagnostics using
the Anthropic Claude SDK with comprehensive fallback mechanisms.

Features:
- Claude 3.5 Sonnet integration with expert system prompt
- Structured JSON response parsing and validation
- Electrical calculation tools (Ohm's law, power, voltage drop, battery capacity)
- Comprehensive rule-based fallback diagnostics
- Weather and temperature effect integration
- Diagnostic history management
- Error handling and academic logging

Author: SCAD ITGM 522 Project 3 - Sprint 3
"""

import os
import re
import json
import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import Anthropic SDK
try:
    import anthropic
    from anthropic import Anthropic, APITimeoutError, APIError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import external API modules (optional weather integration)
try:
    from external_apis import weather_client, temp_corrections, aircraft_db
    EXTERNAL_APIS_AVAILABLE = True
except ImportError:
    EXTERNAL_APIS_AVAILABLE = False

# Configure module logger
logger = logging.getLogger(__name__)

if not ANTHROPIC_AVAILABLE:
    logger.warning("Anthropic SDK not available - using fallback diagnostics only")
if not EXTERNAL_APIS_AVAILABLE:
    logger.warning("External APIs module not available - limited environmental analysis")


# Expert System Prompt - Comprehensive Configuration
EXPERT_SYSTEM_PROMPT = """You are an expert aircraft electrical technician with over 20 years of experience diagnosing electrical system failures in general aviation aircraft (Cessna, Piper, Beechcraft, Diamond, Cirrus).

EXPERTISE AREAS:
- 12V and 28V electrical systems design and troubleshooting
- Lead-acid and AGM battery diagnostics and capacity testing
- Alternator/generator troubleshooting (field excitation, rectifiers, regulators)
- Bus system architecture (main bus, essential bus, avionics bus)
- Circuit breaker protection systems and load analysis
- Environmental effects on electrical systems (temperature -40°C to +50°C, humidity, vibration, altitude)
- Voltage drop analysis and resistance measurements
- Load testing procedures and electrical balance
- Intermittent fault diagnosis techniques
- FAA Part 43 maintenance requirements

DIAGNOSTIC APPROACH:
1. SAFETY FIRST - Identify high-voltage hazards, fire risks, and electrical shock dangers
2. SYSTEMATIC PROCEDURES - Apply half-split technique, voltage drop analysis, load path tracing
3. ENVIRONMENTAL FACTORS - Account for temperature coefficients, humidity effects, operational altitude
4. TEST EQUIPMENT - Specify exact tools: digital multimeter (min 0.1V resolution), clamp meter, battery analyzer
5. COST-EFFECTIVE SOLUTIONS - Prefer cleaning/repair over replacement when safe and legal
6. REGULATORY COMPLIANCE - Follow FAA maintenance practices and documentation requirements

CRITICAL ANALYSIS FACTORS:
- Temperature compensation for battery voltage (0.01V/°C for lead-acid)
- Alternator output varies with RPM (check at 1500-2000 RPM)
- Voltage drop limits: 0.5V max for power circuits, 0.2V for avionics
- Circuit breaker thermal characteristics and reset timing
- Intermittent faults often temperature or vibration related

RESPONSE FORMAT REQUIREMENTS:
You MUST respond with valid JSON using this exact structure. Do not include any text before or after the JSON:

{
  "safety_warnings": [
    "List all safety precautions - be specific about voltage levels and fire risks",
    "Include PPE requirements and emergency procedures"
  ],
  "diagnosis": "Brief 1-2 sentence root cause diagnosis based on symptoms and measurements",
  "confidence_level": 0.95,
  "troubleshooting_steps": [
    {
      "step": 1,
      "action": "Specific action with exact tool and measurement point",
      "expected_result": "Precise expected value with units and tolerances",
      "decision_point": "If X, then Y; If Z, then W - be specific",
      "safety_note": "Any safety consideration for this step"
    }
  ],
  "probable_causes": [
    {
      "cause": "Specific component or connection failure",
      "probability": 0.75,
      "reasoning": "Why this is likely based on symptoms"
    }
  ],
  "recommendations": [
    "Specific part numbers or repair procedures",
    "Preventive maintenance to avoid recurrence",
    "Regulatory compliance notes"
  ],
  "environmental_considerations": [
    "How temperature/humidity/altitude affects this diagnosis",
    "Seasonal maintenance recommendations"
  ],
  "required_tools": [
    "Fluke 87V or equivalent digital multimeter",
    "Specific tools with model numbers where applicable"
  ],
  "estimated_time": "30-45 minutes",
  "estimated_cost": "$150-$400 including parts and labor",
  "maintenance_log_entry": "Sample entry for aircraft maintenance log per FAA requirements"
}

IMPORTANT RULES:
- Always provide 3-6 detailed troubleshooting steps with decision trees
- Include specific voltage/resistance/current values, not just ranges
- Consider the complete electrical path from source to ground
- Account for the specific aircraft type's electrical system design
- Provide part numbers for common replacement items where applicable
- Include torque specifications for electrical connections where applicable
- Reference relevant FAA Advisory Circulars (e.g., AC 43.13-1B)"""


class DiagnosticAgent:
    """
    Claude-powered aircraft electrical diagnostic agent

    Provides AI-driven diagnostics with intelligent fallback to rule-based system.
    Integrates weather data and performs electrical calculations.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize diagnostic agent with Claude SDK

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = None

        # Initialize Anthropic client if available
        if ANTHROPIC_AVAILABLE and self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("DiagnosticAgent initialized with Claude SDK")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            logger.warning("DiagnosticAgent running in fallback mode - no API key or SDK unavailable")

        # Agent configuration
        self.config = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "temperature": 0.7,
            "timeout": 30  # 30 second timeout
        }

        # Electrical reference specifications
        self.electrical_specs = {
            "12V": {
                "battery_nominal": 12.6,
                "battery_min": 11.5,
                "battery_max": 13.2,
                "alternator_output": 14.4,
                "alternator_min": 13.8,
                "alternator_max": 14.8,
                "bus_voltage_drop_max": 0.5
            },
            "28V": {
                "battery_nominal": 25.2,
                "battery_min": 23.0,
                "battery_max": 26.4,
                "alternator_output": 28.8,
                "alternator_min": 27.6,
                "alternator_max": 29.6,
                "bus_voltage_drop_max": 1.0
            }
        }

    def diagnose(self, symptoms: str, system_state: Dict,
                 measured_values: Dict, aircraft_type: str = "Unknown") -> Dict:
        """
        Perform comprehensive diagnostic analysis

        Args:
            symptoms: User-reported symptoms description
            system_state: Current electrical system state from simulator
            measured_values: User-provided electrical measurements
            aircraft_type: Aircraft make/model

        Returns:
            Structured diagnostic response with troubleshooting steps
        """
        try:
            # Build diagnostic context
            context = self._build_diagnostic_context(
                symptoms, system_state, measured_values, aircraft_type
            )

            # Attempt Claude API diagnosis first
            if self.client:
                try:
                    diagnostic = self._call_claude_api(context)
                    if diagnostic and diagnostic.get('diagnosis'):
                        logger.info(f"Claude API diagnosis successful")
                        return diagnostic
                except Exception as e:
                    logger.error(f"Claude API error: {e}")

            # Fallback to rule-based diagnosis
            logger.info("Using fallback rule-based diagnosis")
            return self._get_fallback_diagnostic(
                symptoms, system_state, measured_values, aircraft_type
            )

        except Exception as e:
            logger.error(f"Diagnostic error: {e}", exc_info=True)
            return self._get_error_diagnostic(str(e))

    def _build_diagnostic_context(self, symptoms: str, system_state: Dict,
                                   measured_values: Dict, aircraft_type: str) -> str:
        """
        Build comprehensive diagnostic context for Claude
        """
        # Determine voltage system
        voltage_system = "28V" if system_state.get('voltage_system') == 'SYSTEM_28V' else "12V"

        context = f"""AIRCRAFT ELECTRICAL DIAGNOSTIC REQUEST
========================================

AIRCRAFT: {aircraft_type}
VOLTAGE SYSTEM: {voltage_system}
SYMPTOM DESCRIPTION: {symptoms}

CURRENT SYSTEM STATE:
--------------------
Battery:
  - Voltage: {system_state.get('battery', {}).get('voltage', 'N/A')}V
  - State: {system_state.get('battery', {}).get('state', 'N/A')}
  - Health: {system_state.get('battery', {}).get('health', 'N/A')}%
  - Temperature: {system_state.get('battery', {}).get('temperature', 'N/A')}°C

Alternator:
  - Output Voltage: {system_state.get('alternator', {}).get('output_voltage', 'N/A')}V
  - Field Voltage: {system_state.get('alternator', {}).get('field_voltage', 'N/A')}V
  - Operating: {system_state.get('alternator', {}).get('is_operating', False)}
  - Charging: {system_state.get('alternator', {}).get('is_charging', False)}

Buses:
  - Main Bus Voltage: {system_state.get('buses', {}).get('main_bus', {}).get('voltage', 'N/A')}V
  - Main Bus Load: {system_state.get('buses', {}).get('main_bus', {}).get('load_current', 'N/A')}A
  - Essential Bus Voltage: {system_state.get('buses', {}).get('essential_bus', {}).get('voltage', 'N/A')}V
  - Essential Bus Load: {system_state.get('buses', {}).get('essential_bus', {}).get('load_current', 'N/A')}A

System:
  - Total Load: {system_state.get('total_load', 'N/A')}A
  - Active Fault: {system_state.get('active_fault', 'None')}

USER MEASURED VALUES:
--------------------"""

        if measured_values:
            context += f"""
  - Battery Voltage: {measured_values.get('battery_voltage', 'Not measured')}V
  - Alternator Output: {measured_values.get('alternator_output', 'Not measured')}V
  - Ambient Temperature: {measured_values.get('ambient_temperature', 'Not measured')}°C
"""
        else:
            context += "\n  No user measurements provided\n"

        # Add circuit breaker status
        context += "\nCIRCUIT BREAKER STATUS:\n"
        for bus_name, bus_data in system_state.get('buses', {}).items():
            for breaker in bus_data.get('circuit_breakers', []):
                status = "CLOSED" if breaker.get('is_closed', False) else "TRIPPED"
                current = breaker.get('current_draw', 0)
                rating = breaker.get('rating', 0)
                context += f"  - {breaker.get('name', 'Unknown')}: {status} ({current:.1f}A / {rating}A)\n"

        context += """
DIAGNOSTIC TASK:
---------------
Analyze the symptoms and system state to provide:
1. Root cause diagnosis with confidence level
2. Step-by-step troubleshooting procedure
3. Safety warnings specific to this issue
4. Required tools and estimated repair time
5. Maintenance log entry per FAA requirements

Respond with properly formatted JSON as specified in the system prompt."""

        return context

    def _call_claude_api(self, context: str) -> Dict:
        """
        Call Claude API and parse the response
        """
        if not self.client:
            raise ValueError("Claude client not initialized")

        try:
            # Make API call
            response = self.client.messages.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                temperature=self.config["temperature"],
                system=EXPERT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": context}]
            )

            # Extract response text
            response_text = response.content[0].text if response.content else ""

            # Parse JSON from response
            diagnostic = self._parse_claude_response(response_text)

            # Add metadata
            diagnostic['ai_model'] = self.config["model"]
            diagnostic['response_time'] = datetime.utcnow().isoformat()

            return diagnostic

        except APITimeoutError:
            logger.error("Claude API timeout after 30 seconds")
            raise
        except APIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {e}")
            raise

    def _parse_claude_response(self, response_text: str) -> Dict:
        """
        Parse and validate JSON response from Claude
        """
        if not response_text:
            raise ValueError("Empty response from Claude")

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)

        if not json_match:
            logger.warning("No JSON found in Claude response")
            raise ValueError("No valid JSON in response")

        try:
            diagnostic = json.loads(json_match.group())

            # Validate required fields
            required_fields = ['safety_warnings', 'diagnosis', 'troubleshooting_steps', 'recommendations']

            for field in required_fields:
                if field not in diagnostic:
                    logger.warning(f"Missing required field: {field}")
                    diagnostic[field] = self._get_default_field_value(field)

            # Ensure troubleshooting_steps is properly formatted
            if not isinstance(diagnostic.get('troubleshooting_steps'), list):
                diagnostic['troubleshooting_steps'] = []

            return diagnostic

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON in response: {e}")

    def _get_default_field_value(self, field: str) -> Any:
        """Get default value for missing field"""
        defaults = {
            'safety_warnings': [
                "WARNING: High voltage systems present",
                "Ensure aircraft master switch is OFF",
                "Use insulated tools"
            ],
            'diagnosis': "Diagnostic analysis incomplete - see troubleshooting steps",
            'troubleshooting_steps': [],
            'recommendations': ["Consult certified A&P mechanic"],
            'confidence_level': 0.5,
            'estimated_time': "1-2 hours",
            'estimated_cost': "TBD"
        }
        return defaults.get(field, [])

    def _get_fallback_diagnostic(self, symptoms: str, system_state: Dict,
                                  measured_values: Dict, aircraft_type: str) -> Dict:
        """
        Rule-based fallback diagnostic when Claude is unavailable

        Implements expert system logic for common electrical faults
        """
        # Determine voltage system
        is_28v = system_state.get('voltage_system') == 'SYSTEM_28V'
        specs = self.electrical_specs["28V" if is_28v else "12V"]

        # Initialize diagnostic structure
        diagnostic = {
            "diagnosis": "Rule-based diagnostic (AI unavailable)",
            "confidence_level": 0.7,
            "safety_warnings": [
                f"WARNING: Working with {28 if is_28v else 12}V electrical system",
                "Ensure aircraft master switch is OFF before beginning work",
                "Disconnect battery negative terminal for component replacement",
                "Use insulated tools rated for electrical work",
                "Wear safety glasses when working near battery"
            ],
            "troubleshooting_steps": [],
            "probable_causes": [],
            "recommendations": [],
            "environmental_considerations": [],
            "required_tools": [
                "Digital multimeter (Fluke 87V or equivalent)",
                "Insulated hand tools",
                "Battery hydrometer (for flooded batteries)",
                "Electrical contact cleaner",
                "Wire brush for terminal cleaning"
            ],
            "estimated_time": "1-2 hours",
            "estimated_cost": "$100-$500",
            "maintenance_log_entry": "",
            "ai_model": "fallback_rules",
            "response_time": datetime.utcnow().isoformat()
        }

        # Analyze symptoms and system state
        battery_voltage = system_state.get('battery', {}).get('voltage', 0)
        alternator_output = system_state.get('alternator', {}).get('output_voltage', 0)
        is_alternator_operating = system_state.get('alternator', {}).get('is_operating', False)
        active_fault = system_state.get('active_fault', '').lower()
        symptoms_lower = symptoms.lower()

        # Rule-based diagnosis logic

        # DEAD BATTERY DIAGNOSIS
        if battery_voltage < specs['battery_min'] or 'dead' in symptoms_lower or 'won\'t start' in symptoms_lower:
            diagnostic['diagnosis'] = f"Battery voltage critically low ({battery_voltage:.1f}V) - likely dead or failing battery"
            diagnostic['confidence_level'] = 0.85
            diagnostic['probable_causes'] = [
                {"cause": "Dead/failing battery", "probability": 0.8,
                 "reasoning": f"Voltage {battery_voltage:.1f}V is below minimum {specs['battery_min']}V"},
                {"cause": "Parasitic drain", "probability": 0.15,
                 "reasoning": "Excessive current draw when aircraft is off"},
                {"cause": "Charging system failure", "probability": 0.05,
                 "reasoning": "Battery not receiving charge from alternator"}
            ]
            diagnostic['troubleshooting_steps'] = [
                {
                    "step": 1,
                    "action": "Measure battery voltage with multimeter at battery terminals",
                    "expected_result": f"{specs['battery_nominal']}V with engine off",
                    "decision_point": f"If below {specs['battery_min']}V, battery is discharged/failed",
                    "safety_note": "Ensure master switch OFF"
                },
                {
                    "step": 2,
                    "action": "Perform battery load test at 50% of CCA rating for 15 seconds",
                    "expected_result": f"Voltage remains above {specs['battery_min']}V during test",
                    "decision_point": "If voltage drops below minimum, replace battery",
                    "safety_note": "Battery may spark during load test"
                },
                {
                    "step": 3,
                    "action": "Check specific gravity of each cell (flooded battery only)",
                    "expected_result": "1.265 or higher in all cells",
                    "decision_point": "If one cell is 0.050 lower than others, battery has failed cell",
                    "safety_note": "Battery acid is corrosive - wear protection"
                }
            ]
            diagnostic['recommendations'] = [
                "Replace battery if load test fails",
                "Clean and tighten all battery connections",
                "Check for parasitic drain if new battery fails quickly",
                "Consider AGM battery upgrade for better performance"
            ]

        # ALTERNATOR FAILURE DIAGNOSIS
        elif not is_alternator_operating or alternator_output < specs['alternator_min'] or 'alternator' in symptoms_lower:
            diagnostic['diagnosis'] = f"Alternator not charging - output {alternator_output:.1f}V (should be {specs['alternator_output']}V)"
            diagnostic['confidence_level'] = 0.9
            diagnostic['probable_causes'] = [
                {"cause": "Failed alternator/regulator", "probability": 0.6,
                 "reasoning": f"No output voltage detected ({alternator_output:.1f}V)"},
                {"cause": "Broken alternator belt", "probability": 0.2,
                 "reasoning": "Common mechanical failure preventing alternator rotation"},
                {"cause": "Failed field circuit", "probability": 0.15,
                 "reasoning": "No field excitation to alternator"},
                {"cause": "Open circuit in charging wire", "probability": 0.05,
                 "reasoning": "Wiring fault preventing charge reaching battery"}
            ]
            diagnostic['troubleshooting_steps'] = [
                {
                    "step": 1,
                    "action": "Start engine and measure voltage at battery terminals",
                    "expected_result": f"{specs['alternator_output']}V at 1500-2000 RPM",
                    "decision_point": f"If voltage remains at battery level ({specs['battery_nominal']}V), alternator not charging",
                    "safety_note": "Keep clear of rotating propeller"
                },
                {
                    "step": 2,
                    "action": "Check alternator belt tension and condition",
                    "expected_result": "1/2 inch deflection at center of longest span",
                    "decision_point": "If belt is loose or broken, adjust or replace",
                    "safety_note": "Ensure engine is off"
                },
                {
                    "step": 3,
                    "action": "Measure field voltage at alternator with engine running",
                    "expected_result": f"Approximately {specs['alternator_output']*0.75:.1f}V",
                    "decision_point": "If no field voltage, check field circuit and regulator",
                    "safety_note": "Use insulated probes"
                },
                {
                    "step": 4,
                    "action": "Perform alternator output test with carbon pile load",
                    "expected_result": "Rated amperage output at specified RPM",
                    "decision_point": "If output is below 80% of rating, rebuild or replace alternator",
                    "safety_note": "Alternator will be hot during test"
                }
            ]
            diagnostic['recommendations'] = [
                "Replace or rebuild alternator if tests confirm failure",
                "Check and clean all charging system connections",
                "Replace voltage regulator if separate unit",
                "Verify alternator pulley alignment"
            ]

        # BUS FAULT DIAGNOSIS
        elif 'bus' in active_fault or 'bus' in symptoms_lower:
            diagnostic['diagnosis'] = "Electrical bus fault detected - possible loose connection or failed bus tie"
            diagnostic['confidence_level'] = 0.75
            diagnostic['probable_causes'] = [
                {"cause": "Loose/corroded bus connection", "probability": 0.5,
                 "reasoning": "Most common cause of bus voltage issues"},
                {"cause": "Failed bus tie relay/contactor", "probability": 0.3,
                 "reasoning": "Prevents power transfer between buses"},
                {"cause": "Overloaded circuit", "probability": 0.2,
                 "reasoning": "Excessive current draw causing voltage drop"}
            ]
            diagnostic['troubleshooting_steps'] = [
                {
                    "step": 1,
                    "action": "Measure voltage at each bus bar connection point",
                    "expected_result": f"Within 0.2V of battery/alternator voltage",
                    "decision_point": f"Voltage drop over {specs['bus_voltage_drop_max']}V indicates poor connection",
                    "safety_note": "Do not short bus bars with test probes"
                },
                {
                    "step": 2,
                    "action": "Inspect all bus bar connections for corrosion or looseness",
                    "expected_result": "Clean, tight connections with no visible corrosion",
                    "decision_point": "Clean and retighten any questionable connections",
                    "safety_note": "Disconnect battery before working on bus bars"
                },
                {
                    "step": 3,
                    "action": "Check bus tie relay/contactor operation",
                    "expected_result": "Relay closes with audible click when energized",
                    "decision_point": "Replace if relay doesn't operate or has high resistance",
                    "safety_note": "Relay may be hot if recently operated"
                }
            ]

        # CIRCUIT BREAKER TRIP DIAGNOSIS
        elif 'breaker' in symptoms_lower or 'trip' in symptoms_lower:
            diagnostic['diagnosis'] = "Circuit breaker trip indicates overcurrent condition or breaker failure"
            diagnostic['confidence_level'] = 0.8
            diagnostic['probable_causes'] = [
                {"cause": "Short circuit in protected circuit", "probability": 0.4,
                 "reasoning": "Most serious cause requiring immediate attention"},
                {"cause": "Overloaded circuit", "probability": 0.35,
                 "reasoning": "Too many devices or failed component drawing excess current"},
                {"cause": "Weak/failing circuit breaker", "probability": 0.25,
                 "reasoning": "Thermal element degraded causing premature trips"}
            ]
            diagnostic['troubleshooting_steps'] = [
                {
                    "step": 1,
                    "action": "Identify which breaker has tripped and its rating",
                    "expected_result": "Breaker is visibly popped or tests open",
                    "decision_point": "Do NOT reset until cause is identified",
                    "safety_note": "Resetting without finding cause may cause fire"
                },
                {
                    "step": 2,
                    "action": "Disconnect all loads on affected circuit",
                    "expected_result": "Circuit is completely isolated",
                    "decision_point": "Reset breaker - if it trips immediately, wiring short exists",
                    "safety_note": "Short circuit can cause sparks"
                },
                {
                    "step": 3,
                    "action": "Measure current draw of each device on circuit individually",
                    "expected_result": "Each device draws less than breaker rating",
                    "decision_point": "Replace any device drawing excessive current",
                    "safety_note": "Use clamp meter to avoid breaking circuit"
                }
            ]

        # GENERIC ELECTRICAL ISSUE
        else:
            diagnostic['diagnosis'] = f"Electrical system issue requires systematic diagnosis - symptoms: {symptoms[:100]}"
            diagnostic['confidence_level'] = 0.6
            diagnostic['troubleshooting_steps'] = [
                {
                    "step": 1,
                    "action": "Perform complete electrical system check starting with battery",
                    "expected_result": f"Battery: {specs['battery_nominal']}V, Alternator: {specs['alternator_output']}V",
                    "decision_point": "Identify which values are out of specification",
                    "safety_note": "Follow proper meter safety procedures"
                },
                {
                    "step": 2,
                    "action": "Check all grounds for cleanliness and tightness",
                    "expected_result": "Less than 0.1 ohm resistance to airframe",
                    "decision_point": "Clean and retighten any poor grounds",
                    "safety_note": "Poor grounds can cause intermittent issues"
                }
            ]

        # Add environmental considerations based on measured values
        if measured_values:
            temp = measured_values.get('ambient_temperature', 20)
            if temp < -10:
                diagnostic['environmental_considerations'].append(
                    f"Cold temperature ({temp}°C) reduces battery capacity by approximately 30%"
                )
                diagnostic['environmental_considerations'].append(
                    "Battery may need warming before starting in extreme cold"
                )
            elif temp > 35:
                diagnostic['environmental_considerations'].append(
                    f"High temperature ({temp}°C) accelerates battery water loss"
                )
                diagnostic['environmental_considerations'].append(
                    "Check electrolyte levels more frequently in hot climates"
                )

        # Generate maintenance log entry
        diagnostic['maintenance_log_entry'] = self._generate_log_entry(
            aircraft_type, symptoms, diagnostic['diagnosis']
        )

        return diagnostic

    def _generate_log_entry(self, aircraft_type: str, symptoms: str, diagnosis: str) -> str:
        """
        Generate FAA-compliant maintenance log entry
        """
        date = datetime.utcnow().strftime("%Y-%m-%d")
        return (
            f"{date} - {aircraft_type}\n"
            f"Pilot reported: {symptoms[:100]}\n"
            f"Troubleshooting performed: {diagnosis[:150]}\n"
            f"Action taken: [To be completed by technician]\n"
            f"Aircraft returned to service: [Date/Time]\n"
            f"Signature: _______________ Certificate #: ___________"
        )

    def _get_error_diagnostic(self, error_message: str) -> Dict:
        """
        Return error diagnostic when system fails
        """
        return {
            "diagnosis": "Diagnostic system error - please try again",
            "error": error_message,
            "safety_warnings": [
                "WARNING: Diagnostic system unavailable",
                "Consult certified A&P mechanic for assistance",
                "Do not fly with unresolved electrical issues"
            ],
            "troubleshooting_steps": [],
            "recommendations": [
                "Try diagnosis again in a few moments",
                "Provide more detailed symptom description",
                "Contact maintenance support if issue persists"
            ],
            "ai_model": "error",
            "response_time": datetime.utcnow().isoformat()
        }

    def calculate_electrical(self, calculation_type: str, values: Dict) -> Dict:
        """
        Perform electrical calculations for diagnostic support

        Args:
            calculation_type: Type of calculation (ohms_law, power, voltage_drop, etc.)
            values: Input values for calculation

        Returns:
            Calculation result with units
        """
        try:
            if calculation_type == "ohms_law":
                # V = I * R
                if "current" in values and "resistance" in values:
                    voltage = values["current"] * values["resistance"]
                    return {"result": round(voltage, 2), "unit": "volts", "formula": "V = I × R"}
                elif "voltage" in values and "resistance" in values:
                    current = values["voltage"] / values["resistance"]
                    return {"result": round(current, 3), "unit": "amps", "formula": "I = V / R"}
                elif "voltage" in values and "current" in values:
                    resistance = values["voltage"] / values["current"]
                    return {"result": round(resistance, 2), "unit": "ohms", "formula": "R = V / I"}

            elif calculation_type == "power":
                # P = V * I
                if "voltage" in values and "current" in values:
                    power = values["voltage"] * values["current"]
                    return {"result": round(power, 2), "unit": "watts", "formula": "P = V × I"}
                elif "current" in values and "resistance" in values:
                    power = values["current"]**2 * values["resistance"]
                    return {"result": round(power, 2), "unit": "watts", "formula": "P = I² × R"}
                elif "voltage" in values and "resistance" in values:
                    power = values["voltage"]**2 / values["resistance"]
                    return {"result": round(power, 2), "unit": "watts", "formula": "P = V² / R"}

            elif calculation_type == "voltage_drop":
                # Voltage drop in wire: Vdrop = I * R * L * 2 / 1000
                if all(k in values for k in ["current", "length", "wire_gauge"]):
                    # Resistance per 1000 ft for common wire gauges (copper at 20°C)
                    resistance_table = {
                        20: 10.15, 18: 6.385, 16: 4.016, 14: 2.525, 12: 1.588,
                        10: 0.999, 8: 0.628, 6: 0.395, 4: 0.249, 2: 0.156, 0: 0.098
                    }

                    wire_gauge = int(values["wire_gauge"])
                    if wire_gauge in resistance_table:
                        resistance_per_1000 = resistance_table[wire_gauge]
                        # Calculate voltage drop (2x length for return path)
                        voltage_drop = values["current"] * resistance_per_1000 * values["length"] * 2 / 1000
                        return {
                            "result": round(voltage_drop, 3),
                            "unit": "volts",
                            "formula": f"Vdrop = I × R × 2L / 1000 (AWG {wire_gauge})",
                            "acceptable": voltage_drop < 0.5
                        }

            elif calculation_type == "battery_capacity":
                # Temperature compensation for battery capacity
                if "nominal_capacity" in values and "temperature" in values:
                    temp_c = values["temperature"]
                    nominal = values["nominal_capacity"]
                    # Capacity drops approximately 1% per degree C below 25°C
                    if temp_c < 25:
                        actual_capacity = nominal * (1 - 0.01 * (25 - temp_c))
                    else:
                        actual_capacity = nominal
                    return {
                        "result": round(actual_capacity, 1),
                        "unit": "Ah",
                        "temperature_effect": f"{round(100 - (actual_capacity/nominal)*100, 1)}% capacity loss",
                        "formula": "Capacity = Nominal × (1 - 0.01 × (25°C - T))"
                    }

            return {"error": "Insufficient values for calculation"}

        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return {"error": str(e)}

    def get_agent_info(self) -> Dict:
        """
        Get information about the diagnostic agent configuration

        Returns:
            Agent configuration and status information
        """
        return {
            "status": "operational" if self.client else "fallback_only",
            "ai_available": self.client is not None,
            "model": self.config["model"] if self.client else "rule_based",
            "capabilities": [
                "Expert electrical system diagnosis",
                "Systematic troubleshooting procedures",
                "Safety warnings and precautions",
                "Environmental factor analysis",
                "Electrical calculations (Ohm's law, power, voltage drop)",
                "FAA maintenance log entry generation",
                "Fallback rule-based diagnosis"
            ],
            "supported_aircraft": [
                "Cessna 150/152/172/182/210",
                "Piper Cherokee/Archer/Arrow/Seminole",
                "Beechcraft Bonanza/Baron/King Air",
                "Diamond DA20/DA40/DA42",
                "Cirrus SR20/SR22",
                "General aviation aircraft with 12V/28V systems"
            ],
            "api_key_configured": bool(self.api_key),
            "timeout": self.config["timeout"],
            "temperature": self.config["temperature"],
            "max_tokens": self.config["max_tokens"]
        }

    # Compatibility methods for existing code
    def diagnose_symptoms(self, symptoms: str, measured_values: Dict,
                         aircraft_type: str, system_state: Dict) -> Dict:
        """
        Compatibility wrapper for diagnose() method
        """
        return self.diagnose(symptoms, system_state, measured_values, aircraft_type)


# Module testing
if __name__ == "__main__":
    print("=" * 80)
    print("Aircraft Electrical Diagnostic Agent - Sprint 3 Full Implementation")
    print("=" * 80)

    # Initialize agent
    agent = DiagnosticAgent()

    print("\nAgent Configuration:")
    print("-" * 40)
    info = agent.get_agent_info()
    for key, value in info.items():
        if isinstance(value, list):
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")

    # Test electrical calculations
    print("\n" + "=" * 80)
    print("Testing Electrical Calculations:")
    print("-" * 40)

    result = agent.calculate_electrical("ohms_law", {"voltage": 14.4, "current": 50})
    print(f"Ohm's Law (14.4V, 50A): {result}")

    result = agent.calculate_electrical("power", {"voltage": 14.4, "current": 50})
    print(f"Power Calculation: {result}")

    result = agent.calculate_electrical("voltage_drop", {
        "current": 20, "length": 15, "wire_gauge": 14
    })
    print(f"Voltage Drop (20A, 15ft, 14AWG): {result}")

    result = agent.calculate_electrical("battery_capacity", {
        "nominal_capacity": 35, "temperature": -10
    })
    print(f"Battery Capacity at -10°C: {result}")

    # Test diagnostic
    print("\n" + "=" * 80)
    print("Testing Diagnostic System:")
    print("-" * 40)

    test_symptoms = "Battery won't hold charge, alternator light stays on during flight"
    test_system_state = {
        "voltage_system": "SYSTEM_12V",
        "battery": {"voltage": 11.2, "state": "DISCHARGING", "health": 65, "temperature": 20},
        "alternator": {"output_voltage": 0.0, "field_voltage": 0.0, "is_operating": False, "is_charging": False},
        "buses": {
            "main_bus": {"voltage": 11.2, "load_current": 25.5, "circuit_breakers": []},
            "essential_bus": {"voltage": 11.2, "load_current": 15.3, "circuit_breakers": []}
        },
        "total_load": 40.8,
        "active_fault": "ALTERNATOR_FAILURE"
    }

    test_measured_values = {
        "battery_voltage": 11.2,
        "alternator_output": 0.0,
        "ambient_temperature": -5
    }

    print("\nPerforming diagnosis...")
    diagnostic_result = agent.diagnose(
        symptoms=test_symptoms,
        system_state=test_system_state,
        measured_values=test_measured_values,
        aircraft_type="Cessna 172S"
    )

    print("\nDiagnostic Result:")
    print("-" * 40)
    print(json.dumps(diagnostic_result, indent=2))

    print("\n" + "=" * 80)
    print("Sprint 3 Implementation Complete - Full AI Diagnostics with Fallback")
    print("=" * 80)
