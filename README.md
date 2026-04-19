# Aircraft Electrical Fault Analyzer

An intelligent aircraft electrical diagnostic system using Claude Agent SDK for expert-level troubleshooting guidance.

## Demo

Watch the full demo on YouTube: https://youtu.be/TM6NtLLu6C8

## Academic Attribution

**Institution**: Savannah College of Art and Design (SCAD)
**Course**: ITGM 522 - Advanced Programming for Interactive Media
**Project**: Project 3 - Multi-Language Application with AI Integration
**Timeline**: 10 days (5 Sprints x 2 days each)

## Project Overview

The Aircraft Electrical Fault Analyzer is an AI-powered diagnostic system that allows users to input aircraft electrical system symptoms and receive expert-level troubleshooting guidance. The system simulates a complete aircraft electrical system and uses the Claude Agent SDK to provide systematic diagnostic procedures.

### Core Features

- Real-time electrical system simulation (12V/28V systems)
- Battery, alternator, and bus system monitoring
- Circuit breaker protection modeling
- Fault injection for testing and training
- AI-powered diagnostic analysis (Sprint 3)
- Environmental factor consideration
- Diagnostic history tracking

## Technology Stack

### Backend (Python)
- Flask web framework
- Claude Agent SDK (Anthropic)
- Python 3.8+

### Frontend (JavaScript)
- Vanilla JavaScript (ES6+)
- HTML5/CSS3
- REST API communication

### Data Storage
- JSON file-based storage
- No database required

## Project Structure

```
Aircraft-Electrical-Fault-Analyzer/
 server/                          # Python Flask backend
    app.py                      # Main Flask application
    electrical_sim.py           # Electrical system simulation engine
    claude_agent.py             # Claude Agent SDK integration (Sprint 3)
 client/                          # JavaScript frontend (Sprint 2)
    index.html                  # Main dashboard
    styles.css                  # UI styling
    app.js                      # Main application logic
    api-client.js               # Backend communication
 data/                            # JSON data storage
    diagnostic_history.json     # Diagnostic session history
    system_state.json           # Current system state
 tests/                           # Unit tests
    test_electrical_system.py   # Electrical system tests
 docs/                            # Documentation
    CLAUDE.md                   # Project instructions
    PRD-Aircraft-Electrical-Fault-Analyzer.md
 .gitignore                       # Git ignore rules
 .env.example                     # Environment variable template
 requirements.txt                 # Python dependencies
 README.md                        # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Step-by-Step Installation (Windows)

1. Clone the repository:
```bash
git clone https://github.com/iarnoldy/aircraft-electrical-fault-analyzer.git
cd aircraft-electrical-fault-analyzer
```

2. Create a Python virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows Command Prompt
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1

# Git Bash or WSL
source venv/Scripts/activate
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Create environment configuration:
```bash
# Copy the example environment file
copy .env.example .env

# Edit .env file and add your API keys
# ANTHROPIC_API_KEY=your_api_key_here
# AVIATION_WEATHER_API_KEY=your_key_here (optional)
```

6. Verify installation:
```bash
python server/electrical_sim.py
```

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Anthropic API Configuration
ANTHROPIC_API_KEY=your_api_key_here

# Aviation Weather API Configuration (Optional)
AVIATION_WEATHER_API_KEY=your_key_here

# Flask Configuration
FLASK_ENV=development
FLASK_PORT=5000
FLASK_DEBUG=True
```

### Getting API Keys

**Anthropic API Key** (Required for Sprint 3):
1. Visit https://console.anthropic.com/
2. Create an account or log in
3. Navigate to API Keys section
4. Generate a new API key
5. Copy the key to your `.env` file

**Aviation Weather API Key** (Optional):
- Will be configured in Sprint 4
- System works without weather API using fallback data

## Running the Application

### Start the Flask Backend Server

```bash
# Make sure virtual environment is activated
python server/app.py
```

The backend server will start on http://localhost:5000

### Start the Frontend Dashboard

Option 1: Using Python HTTP Server (Recommended for development)
```bash
# In a new terminal window
cd client
python -m http.server 8080
```

Then open your browser to: http://localhost:8080

Option 2: Direct file access
```bash
# Open the HTML file directly in your browser
start client/index.html  # Windows
open client/index.html   # Mac
xdg-open client/index.html  # Linux
```

Note: The dashboard requires the backend server to be running for full functionality.

### Verify Application is Running

1. Backend API: http://localhost:5000/api/system/status
2. Frontend Dashboard: http://localhost:8080
3. You should see the aviation-themed dashboard with real-time electrical system monitoring

### Test API Endpoints

**Get System Status**:
```bash
curl http://localhost:5000/api/system/status
```

**Inject a Fault**:
```bash
curl -X POST http://localhost:5000/api/system/inject-fault \
  -H "Content-Type: application/json" \
  -d "{\"fault_type\": \"dead_battery\"}"
```

**Request Diagnosis** (Placeholder in Sprint 1):
```bash
curl -X POST http://localhost:5000/api/diagnose \
  -H "Content-Type: application/json" \
  -d "{\"symptoms\": \"Battery voltage drops when starting\", \"aircraft_type\": \"Cessna 172\", \"measured_values\": {\"battery_voltage\": 11.2}}"
```

## API Documentation

### GET /api/system/status

Returns current electrical system status.

**Response**:
```json
{
  "success": true,
  "data": {
    "voltage_system": 12,
    "battery": {
      "voltage": 12.6,
      "state_of_charge": 100.0,
      "health": 100.0,
      "temperature": 25.0,
      "state": "GOOD",
      "is_healthy": true
    },
    "alternator": {
      "output_voltage": 14.38,
      "output_current": 40.2,
      "field_voltage": 10.73,
      "is_operating": true,
      "regulated_voltage": 14.4
    },
    "buses": {
      "main_bus": {...},
      "essential_bus": {...}
    },
    "active_fault": "none",
    "total_load": 40.2
  }
}
```

### POST /api/diagnose

Submit symptoms for AI diagnostic analysis.

**Request Body**:
```json
{
  "symptoms": "Battery voltage drops to 11V when starting, alternator light stays on",
  "measured_values": {
    "battery_voltage": 11.2,
    "alternator_output": 0.0,
    "ambient_temperature": -15
  },
  "aircraft_type": "Cessna 172"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "diagnosis": "Preliminary analysis...",
    "safety_warnings": [...],
    "steps": [...],
    "recommendations": [...],
    "required_tools": [...]
  }
}
```

### POST /api/system/inject-fault

Inject electrical fault for testing.

**Request Body**:
```json
{
  "fault_type": "dead_battery",
  "parameters": {}
}
```

**Fault Types**:
- `dead_battery` - Voltage below minimum threshold
- `alternator_failure` - No charging output
- `bus_fault` - Intermittent power, voltage drops
- `circuit_breaker_trip` - Overcurrent protection activated

### POST /api/system/clear-faults

Clear all active faults and restore normal operation.

### POST /api/system/set-load

Set electrical load on a circuit breaker.

**Request Body**:
```json
{
  "breaker_name": "AVIONICS",
  "current": 12.5
}
```

### GET /api/history

Retrieve diagnostic session history.

**Query Parameters**:
- `limit` (optional): Maximum number of records to return (default: 50)

## Running Tests

The project includes comprehensive unit tests for the electrical system simulation.

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_electrical_system.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_electrical_system.py::TestBattery -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=server --cov-report=html
```

### Expected Test Output

```
tests/test_electrical_system.py::TestBattery::test_battery_initialization_12v PASSED
tests/test_electrical_system.py::TestBattery::test_battery_initialization_28v PASSED
tests/test_electrical_system.py::TestBattery::test_battery_is_healthy PASSED
...
===================== XX passed in X.XXs =====================
```

## Electrical System Simulation

### Components Modeled

**Battery**:
- 12V system: 10.5V - 14.4V range
- 28V system: 21.0V - 28.8V range
- State of charge tracking
- Health monitoring
- Temperature effects

**Alternator**:
- Voltage regulation (14.4V / 28.8V)
- Field voltage (75% of bus voltage)
- Load-dependent output
- Failure modes

**Bus Systems**:
- Main Bus: Primary electrical distribution
- Essential Bus: Critical systems backup
- Voltage drop modeling
- Load calculation

**Circuit Breakers**:
- Ratings: 5A, 10A, 15A, 20A, 30A
- Overload protection (trips at 110% rating)
- Reset capability

### Fault Types

1. **Dead Battery**: Voltage below minimum threshold, often caused by:
   - Age and wear
   - Excessive discharge
   - Cold temperature effects
   - Internal cell failure

2. **Alternator Failure**: No charging output, symptoms include:
   - Battery discharge during flight
   - Low voltage indication
   - Alternator warning light
   - Possible causes: field winding failure, regulator fault

3. **Bus Fault**: Intermittent power and voltage drops, causes:
   - Loose connections
   - Corrosion
   - Damaged wiring
   - Poor ground connections

4. **Circuit Breaker Trip**: Overcurrent protection activated:
   - Overloaded circuit
   - Short circuit
   - Equipment malfunction

## Development Workflow

### Sprint Status

- **Sprint 1 (Days 1-2)**:  Backend Foundation - COMPLETE
  - Project structure established
  - Electrical system simulation implemented
  - Flask API endpoints operational
  - Unit tests passing

- **Sprint 2 (Days 3-4)**: Frontend Foundation - ✅ COMPLETE
  - Aviation-themed dashboard UI (374 lines HTML, 1045 lines CSS)
  - Real-time system monitoring (2-second polling)
  - Canvas-based gauge visualizations
  - API integration (241 lines API client, 838 lines app logic)
  - Fault injection controls
  - Responsive design (mobile/tablet/desktop)
  - Frontend integration tests (14 tests)

- **Sprint 3 (Days 5-6)**: AI Integration - ✅ COMPLETE
  - Claude Agent SDK integration (`server/claude_agent.py`, `server/claude_agent_sprint3_full.py`)
  - Diagnostic pipeline with structured response formatting
  - Safety warnings, procedural steps, tool requirements

- **Sprint 4 (Days 7-8)**: APIs & Polish - ✅ COMPLETE
  - Weather API integration (`server/external_apis.py`, `client/weather-module.js`)
  - Error handler module (`server/error_handler.py`)
  - UI v2 theme, notifications, test harnesses for gauges/loading/hover states

- **Sprint 5 (Days 9-10)**: Testing & Demo - ✅ COMPLETE
  - Comprehensive project documentation (`Documentation/COMPREHENSIVE_PROJECT_DOCUMENTATION.md`)
  - Reflection and learnings write-up
  - Presentation deck and demo video

## Troubleshooting

### Common Issues

**Virtual Environment Not Activating**:
```bash
# Make sure you're in the project directory
cd Aircraft-Electrical-Fault-Analyzer

# Try alternate activation method
python -m venv venv --clear
venv\Scripts\activate
```

**Module Import Errors**:
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

**Port Already in Use**:
```bash
# Change port in .env file
FLASK_PORT=5001
```

**API Key Errors**:
- Verify `.env` file exists in project root
- Check API key format (should start with `sk-ant-`)
- Ensure no extra spaces or quotes around key

## Contributing

This is an academic project. For questions or issues:
1. Check existing documentation in `docs/` directory
2. Review CLAUDE.md for project guidelines
3. Consult with course instructor

## License

Academic project for SCAD ITGM 522. Not licensed for commercial use.

## Acknowledgments

- Anthropic for Claude AI and Agent SDK
- SCAD ITGM 522 course materials
- Aviation electrical system references and standards

## Project Status

**Status**: All 5 sprints complete — final submission
**Stack delivered**: Python 3.8+ / Flask 3.0 / Claude Agent SDK / Vanilla JS ES6+ / HTML5 Canvas / pytest
**Documentation**: See `Documentation/COMPREHENSIVE_PROJECT_DOCUMENTATION.md` and `Documentation/REFLECTION_AND_LEARNINGS.md`

---

**Academic Project** | SCAD ITGM 522 | Aircraft Electrical Fault Analyzer
