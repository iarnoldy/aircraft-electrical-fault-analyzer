"""
Aircraft Electrical Fault Analyzer - Flask Application

Main Flask server providing REST API endpoints for:
- Electrical system status monitoring
- AI-powered diagnostic analysis (placeholder for Sprint 3)
- Fault injection for testing
- Diagnostic history tracking

Author: SCAD ITGM 522 Project 3
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from electrical_sim import ElectricalSystem, VoltageSystem, FaultType
from claude_agent import DiagnosticAgent

# Load environment variables
load_dotenv()

# Configure logging for academic error documentation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('electrical_fault_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Simple in-memory cache for system status (Performance optimization - Issue 6-7)
# Cache duration: 250ms TTL to balance performance vs. real-time accuracy
STATUS_CACHE = {
    'data': None,
    'timestamp': 0
}
CACHE_TTL_MS = 250  # milliseconds

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Data directory paths
DATA_DIR = Path(__file__).parent.parent / 'data'
HISTORY_FILE = DATA_DIR / 'diagnostic_history.json'
STATE_FILE = DATA_DIR / 'system_state.json'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Initialize electrical system (global instance for this sprint)
electrical_system = ElectricalSystem(VoltageSystem.SYSTEM_12V)

# Set initial realistic loads
electrical_system.set_load("AVIONICS", 8.5)
electrical_system.set_load("LIGHTS", 6.2)
electrical_system.set_load("FUEL_PUMP", 12.0)
electrical_system.set_load("INSTRUMENTS", 5.5)
electrical_system.set_load("RADIOS", 7.8)

# Initialize diagnostic agent (Sprint 3)
diagnostic_agent = DiagnosticAgent()

logger.info("Flask application initialized with AI diagnostic agent")


def invalidate_status_cache():
    """
    Invalidate the system status cache
    Called when any operation modifies system state (fault injection, load changes, etc.)

    Performance Optimization (Issue 6-7): Ensures cache consistency while maintaining
    fast response times for read-heavy polling workloads.
    """
    global STATUS_CACHE
    STATUS_CACHE['data'] = None
    STATUS_CACHE['timestamp'] = 0
    logger.debug("System status cache invalidated")


def load_diagnostic_history() -> List[Dict]:
    """
    Load diagnostic history from JSON file

    Returns:
        List of diagnostic session records
    """
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading diagnostic history: {str(e)}")
        return []


def save_diagnostic_history(history: List[Dict]):
    """
    Save diagnostic history to JSON file

    Args:
        history: List of diagnostic session records
    """
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving diagnostic history: {str(e)}")


def add_diagnostic_record(symptoms: str, measured_values: Dict, aircraft_type: str, diagnosis: Dict):
    """
    Add a diagnostic record to history

    Args:
        symptoms: User-reported symptoms
        measured_values: Measured electrical values
        aircraft_type: Aircraft type/model
        diagnosis: Diagnostic results
    """
    try:
        history = load_diagnostic_history()
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "aircraft_type": aircraft_type,
            "symptoms": symptoms,
            "measured_values": measured_values,
            "diagnosis": diagnosis,
            "system_state": electrical_system.get_status()
        }
        history.append(record)
        save_diagnostic_history(history)
        logger.info(f"Diagnostic record added to history")
    except Exception as e:
        logger.error(f"Error adding diagnostic record: {str(e)}")


@app.route('/', methods=['GET'])
def index():
    """Root endpoint - API information"""
    return jsonify({
        "name": "Aircraft Electrical Fault Analyzer API",
        "version": "1.0.0",
        "project": "SCAD ITGM 522 Project 3",
        "endpoints": {
            "GET /api/system/status": "Get current electrical system status",
            "POST /api/diagnose": "Submit symptoms for AI diagnostic analysis",
            "POST /api/system/inject-fault": "Inject electrical fault for testing",
            "POST /api/system/clear-faults": "Clear all active faults",
            "POST /api/system/set-load": "Set electrical load on circuit breaker",
            "GET /api/history": "Retrieve diagnostic session history"
        },
        "status": "operational"
    })


@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """
    Get current electrical system status with caching

    Performance Optimization (Issue 6-7): Implements 250ms cache to reduce response time
    from ~2071ms to <1000ms for polling workloads. Cache is invalidated on any POST
    operation that modifies system state.

    Returns:
        JSON response with complete system state including battery, alternator,
        buses, and circuit breakers
    """
    try:
        global STATUS_CACHE
        current_time_ms = time.time() * 1000

        # Check if cache is valid (within TTL)
        cache_age_ms = current_time_ms - STATUS_CACHE['timestamp']
        if STATUS_CACHE['data'] is not None and cache_age_ms < CACHE_TTL_MS:
            logger.debug(f"Returning cached system status (age: {cache_age_ms:.1f}ms)")
            return jsonify(STATUS_CACHE['data'])

        # Cache miss or expired - fetch fresh data
        status = electrical_system.get_status()
        logger.info("System status retrieved successfully (cache miss)")

        # Build response
        response_data = {
            "success": True,
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Update cache
        STATUS_CACHE['data'] = response_data
        STATUS_CACHE['timestamp'] = current_time_ms

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error retrieving system status: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    """
    Submit symptoms for AI diagnostic analysis

    Request body:
        {
            "symptoms": "Description of electrical issues",
            "measured_values": {
                "battery_voltage": 11.2,
                "alternator_output": 0.0,
                "ambient_temperature": -15
            },
            "aircraft_type": "Cessna 172"
        }

    Returns:
        JSON response with diagnostic results, safety warnings, and troubleshooting steps
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        symptoms = data.get('symptoms', '')
        measured_values = data.get('measured_values', {})
        aircraft_type = data.get('aircraft_type', 'Unknown')

        if not symptoms:
            return jsonify({
                "success": False,
                "error": "Symptoms are required"
            }), 400

        logger.info(f"Diagnostic request received - Aircraft: {aircraft_type}, Symptoms: {symptoms[:50]}...")

        # Get current system state
        system_state = electrical_system.get_status()

        # Call diagnostic agent (Sprint 3 - Full AI Integration)
        diagnosis = diagnostic_agent.diagnose(
            symptoms=symptoms,
            system_state=system_state,
            measured_values=measured_values,
            aircraft_type=aircraft_type
        )

        # Add to diagnostic history
        add_diagnostic_record(symptoms, measured_values, aircraft_type, diagnosis)

        logger.info("Diagnostic analysis completed successfully")
        return jsonify({
            "success": True,
            "data": diagnosis,
            "system_state": electrical_system.get_status(),
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error during diagnostic analysis: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/system/inject-fault', methods=['POST'])
def inject_fault():
    """
    Inject electrical fault for testing and training

    Request body:
        {
            "fault_type": "dead_battery" | "alternator_failure" | "bus_fault" | "circuit_breaker_trip",
            "parameters": {
                "bus_name": "Main Bus",  // for bus_fault
                "breaker_name": "AVIONICS"  // for circuit_breaker_trip
            }
        }

    Returns:
        JSON response with new system state
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        fault_type_str = data.get('fault_type', '')
        parameters = data.get('parameters', {})

        # Validate fault type
        valid_faults = ['dead_battery', 'alternator_failure', 'bus_fault', 'circuit_breaker_trip']
        if fault_type_str not in valid_faults:
            return jsonify({
                "success": False,
                "error": f"Invalid fault type. Must be one of: {', '.join(valid_faults)}"
            }), 400

        logger.info(f"Injecting fault: {fault_type_str}")

        # Inject the specified fault
        if fault_type_str == 'dead_battery':
            electrical_system.inject_dead_battery()
        elif fault_type_str == 'alternator_failure':
            electrical_system.inject_alternator_failure()
        elif fault_type_str == 'bus_fault':
            bus_name = parameters.get('bus_name', 'Main Bus')
            electrical_system.inject_bus_fault(bus_name)
        elif fault_type_str == 'circuit_breaker_trip':
            breaker_name = parameters.get('breaker_name', 'AVIONICS')
            electrical_system.inject_circuit_breaker_trip(breaker_name)

        # Invalidate cache since system state changed
        invalidate_status_cache()

        new_state = electrical_system.get_status()

        logger.info(f"Fault injected successfully: {fault_type_str}")
        return jsonify({
            "success": True,
            "message": f"Fault '{fault_type_str}' injected successfully",
            "new_state": new_state,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error injecting fault: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/system/clear-faults', methods=['POST'])
def clear_faults():
    """
    Clear all active faults and restore system to normal operation

    Returns:
        JSON response with restored system state
    """
    try:
        logger.info("Clearing all faults")
        electrical_system.clear_faults()

        # Restore initial loads
        electrical_system.set_load("AVIONICS", 8.5)
        electrical_system.set_load("LIGHTS", 6.2)
        electrical_system.set_load("FUEL_PUMP", 12.0)
        electrical_system.set_load("INSTRUMENTS", 5.5)
        electrical_system.set_load("RADIOS", 7.8)

        # Invalidate cache since system state changed
        invalidate_status_cache()

        new_state = electrical_system.get_status()

        logger.info("Faults cleared successfully")
        return jsonify({
            "success": True,
            "message": "All faults cleared, system restored to normal operation",
            "new_state": new_state,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error clearing faults: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/system/set-load', methods=['POST'])
def set_load():
    """
    Set electrical load on a specific circuit breaker

    Request body:
        {
            "breaker_name": "AVIONICS",
            "current": 12.5
        }

    Returns:
        JSON response with updated system state
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400

        breaker_name = data.get('breaker_name', '')
        current = data.get('current', 0.0)

        if not breaker_name:
            return jsonify({
                "success": False,
                "error": "breaker_name is required"
            }), 400

        logger.info(f"Setting load on {breaker_name}: {current}A")
        electrical_system.set_load(breaker_name, float(current))

        # Invalidate cache since system state changed
        invalidate_status_cache()

        new_state = electrical_system.get_status()

        return jsonify({
            "success": True,
            "message": f"Load set on {breaker_name}: {current}A",
            "new_state": new_state,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error setting load: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """
    Retrieve diagnostic session history

    Query parameters:
        limit: Maximum number of records to return (default: 50)

    Returns:
        JSON response with diagnostic history
    """
    try:
        limit = request.args.get('limit', 50, type=int)

        history = load_diagnostic_history()

        # Return most recent records first, limited by limit parameter
        recent_history = history[-limit:] if len(history) > limit else history
        recent_history.reverse()

        logger.info(f"Retrieved {len(recent_history)} diagnostic history records")
        return jsonify({
            "success": True,
            "data": {
                "total_records": len(history),
                "returned_records": len(recent_history),
                "history": recent_history
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/weather', methods=['GET'])
def get_weather():
    """
    Get current weather conditions for a location

    Query parameters:
        icao: ICAO airport code (e.g., KATL for Atlanta)

    Returns:
        JSON response with weather data
    """
    try:
        from external_apis import weather_client, temp_corrections

        icao = request.args.get('icao', 'KATL')

        logger.info(f"Fetching weather for {icao}")
        weather_data = weather_client.get_weather_for_location(icao)

        # Add temperature corrections for current system state
        battery_voltage = electrical_system.battery.current_voltage
        temp = weather_data.get('temperature_celsius', 25)

        # Calculate temperature effects
        corrected_voltage = temp_corrections.apply_battery_temp_correction(battery_voltage, temp)
        capacity_factor = temp_corrections.calculate_cold_cranking_impact(temp)
        alt_efficiency = temp_corrections.calculate_alternator_output_correction(temp)

        weather_data['temperature_effects'] = {
            'corrected_battery_voltage': round(corrected_voltage, 2),
            'battery_capacity_percent': round(capacity_factor * 100, 1),
            'alternator_efficiency_percent': round(alt_efficiency * 100, 1)
        }

        logger.info(f"Weather data retrieved for {icao}")
        return jsonify({
            "success": True,
            "data": weather_data,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching weather: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "requested_url": request.url
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(error)}", exc_info=True)
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "details": str(error)
    }), 500


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    logger.info(f"Starting Flask server on port {port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
