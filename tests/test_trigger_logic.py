import jinja2

# The Jinja2 template representing the combined conditions for the timer trigger
TEMPLATE_STRING = """
{% set phase_1 = state_attr('sensor.ev_load_balancer_charger', 'phase_1_state') | default('1 Phase', true) %}
{% set phase_3 = state_attr('sensor.ev_load_balancer_charger', 'phase_3_state') | default('3 Phases', true) %}

{% set c1 = trigger.to_state is defined and trigger.to_state.state == phase_1 and (trigger.from_state is not defined or trigger.from_state is none or trigger.from_state.state != phase_1) %}
{% set c2 = states('sensor.ev_load_balancer') in ['Limited', 'Solar', 'Comfort'] %}
{% set c3 = state_attr('sensor.ev_load_balancer_charger', 'connection_state') == 'Connected' %}

{{ c1 and c2 and c3 }}
"""

class MockState:
    def __init__(self, state):
        self.state = state

class MockTrigger:
    def __init__(self, from_state_value, to_state_value):
        self.from_state = MockState(from_state_value) if from_state_value is not None else None
        self.to_state = MockState(to_state_value) if to_state_value is not None else None

# Mock data store
mock_db = {
    "sensor.ev_load_balancer_charger": {
        "phases_output": "select.my_charger_phases",
        "phase_1_state": "1 Phase",
        "phase_3_state": "3 Phases",
        "connection_state": "Connected"
    },
    "sensor.ev_load_balancer": "Solar",
    "select.my_charger_phases": "1 Phase" # Current State
}

def mock_states(entity_id):
    val = mock_db.get(entity_id)
    if isinstance(val, dict):
        return "mock_state" 
    return val

def mock_state_attr(entity_id, attr):
    attrs = mock_db.get(entity_id, {})
    return attrs.get(attr)

def evaluate(prev_state, curr_state="1 Phase", p1="1 Phase", p3="3 Phases", mode="Solar", connection="Connected"):
    # Update Mock DB
    mock_db["sensor.ev_load_balancer_charger"]["phase_1_state"] = p1
    mock_db["sensor.ev_load_balancer_charger"]["phase_3_state"] = p3
    mock_db["sensor.ev_load_balancer_charger"]["connection_state"] = connection
    mock_db["sensor.ev_load_balancer"] = mode
    mock_db["select.my_charger_phases"] = curr_state

    # Setup Environment
    env = jinja2.Environment()
    env.globals['states'] = mock_states
    env.globals['state_attr'] = mock_state_attr
    
    # Render
    template = env.from_string(TEMPLATE_STRING)
    trigger = MockTrigger(prev_state, curr_state)
    
    try:
        if trigger is None:
             result = template.render() # Simulate no trigger variable passed
        else:
             result = template.render(trigger=trigger)
        return result.strip().lower() == "true"
    except Exception as e:
        print(f"Error: {e}")
        return False

# Setup tests
tests = [
    {
        "name": "Standard Transition in Solar (3 -> 1)",
        "prev": "3 Phases", "curr": "1 Phase", "mode": "Solar", "conn": "Connected",
        "expected": True
    },
    {
        "name": "Transition to 3-phases (1 -> 3)",
        "prev": "1 Phase", "curr": "3 Phases", "mode": "Solar", "conn": "Connected",
        "expected": False
    },
    {
        "name": "Transition in Fast mode (3 -> 1) - Should bypass timer",
        "prev": "3 Phases", "curr": "1 Phase", "mode": "Fast", "conn": "Connected",
        "expected": False
    },
    {
        "name": "Disconnected reset to 1-phase (3 -> 1) - Should bypass timer",
        "prev": "3 Phases", "curr": "1 Phase", "mode": "Solar", "conn": "Disconnected",
        "expected": False
    },
    {
        "name": "Invalid Transition (Unavailable -> 1)",
        "prev": "unavailable", "curr": "1 Phase", "mode": "Solar", "conn": "Connected",
        "expected": True
    },
    {
        "name": "No Change (1 -> 1)",
        "prev": "1 Phase", "curr": "1 Phase", "mode": "Solar", "conn": "Connected",
        "expected": False
    },
    {
        "name": "Startup/Reload (Trigger from_state is Undefined)",
        "prev": None, "curr": "1 Phase", "mode": "Solar", "conn": "Connected",
        "expected": True
    },
    {
        "name": "Transition in 1-Phase Minimum (3 -> 1) - Should bypass timer",
        "prev": "3 Phases", "curr": "1 Phase", "mode": "1-Phase Minimum", "conn": "Connected",
        "expected": False
    },
    {
        "name": "Transition in 3-Phases Minimum (3 -> 1) - Should bypass timer",
        "prev": "3 Phases", "curr": "1 Phase", "mode": "3-Phases Minimum", "conn": "Connected",
        "expected": False
    },
]

# Run tests
print(f"{'TEST NAME':<70} | {'RESULT':<10} | {'PASS/FAIL'}")
print("-" * 95)
all_passed = True
for t in tests:
    actual = evaluate(t["prev"], t["curr"], "1 Phase", "3 Phases", t["mode"], t["conn"])
    passed = actual == t["expected"]
    if not passed: all_passed = False
    print(f"{t['name']:<70} | {str(actual):<10} | {'PASS' if passed else 'FAIL'}")

if all_passed:
    print("\\nALL TESTS PASSED")
    exit(0)
else:
    print("\\nSOME TESTS FAILED")
    exit(1)
