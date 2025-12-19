import jinja2

# The Jinja2 template from the automation
TEMPLATE_STRING = """
{% set phases_entity = state_attr('sensor.ev_load_balancer_charger', 'phases_output') %}
{% set phase_1 = state_attr('sensor.ev_load_balancer_charger', 'phase_1_state') | default('1 Phase', true) %}
{% set phase_3 = state_attr('sensor.ev_load_balancer_charger', 'phase_3_state') | default('3 Phases', true) %}
{{ states(phases_entity) == phase_1 and trigger is defined and trigger.from_state is defined and trigger.from_state.state == phase_3 }}
"""

class MockState:
    def __init__(self, state):
        self.state = state

class MockTrigger:
    def __init__(self, from_state_value):
        self.from_state = MockState(from_state_value) if from_state_value is not None else None

# Mock data store
mock_db = {
    "sensor.ev_load_balancer_charger": {
        "phases_output": "select.my_charger_phases",
        "phase_1_state": "1 Phase",
        "phase_3_state": "3 Phases",
    },
    "select.my_charger_phases": "1 Phase" # Current State
}

def mock_states(entity_id):
    # Retrieve mock state
    # If the entity is the charger selection, return string
    # If the entity is the sensor setup, return dict to simulate attributes
    val = mock_db.get(entity_id)
    if isinstance(val, dict):
        # In HA, states('sensor.x') returns the state string. 
        # Here we only need attributes for the config sensor, so let's check
        # if the template calls states() on it. It doesn't. 
        # It calls states(phases_entity).
        return "mock_state" 
    return val

def mock_state_attr(entity_id, attr):
    attrs = mock_db.get(entity_id, {})
    return attrs.get(attr)

def evaluate(previous_state, current_state="1 Phase", p1="1 Phase", p3="3 Phases"):
    # Update Mock DB
    mock_db["sensor.ev_load_balancer_charger"]["phase_1_state"] = p1
    mock_db["sensor.ev_load_balancer_charger"]["phase_3_state"] = p3
    mock_db["select.my_charger_phases"] = current_state

    # Setup Environment
    env = jinja2.Environment()
    env.globals['states'] = mock_states
    env.globals['state_attr'] = mock_state_attr
    
    # Render
    template = env.from_string(TEMPLATE_STRING)
    trigger = MockTrigger(previous_state)
    
    try:
        if trigger is None:
             result = template.render() # Simulate no trigger variable passed
        else:
             result = template.render(trigger=trigger)
        return result.strip() == "True"
    except Exception as e:
        print(f"Error: {e}")
        return False

# Setup tests
tests = [
    {
        "name": "Standard Transition (3 -> 1)",
        "prev": "3 Phases", "curr": "1 Phase", "p1": "1 Phase", "p3": "3 Phases",
        "expected": True
    },
    {
        "name": "Invalid Transition (Unavailable -> 1)",
        "prev": "unavailable", "curr": "1 Phase", "p1": "1 Phase", "p3": "3 Phases",
        "expected": False
    },
    {
        "name": "No Change (1 -> 1)",
        "prev": "1 Phase", "curr": "1 Phase", "p1": "1 Phase", "p3": "3 Phases",
        "expected": False
    },
    {
        "name": "Custom Config Transition (Three -> One)",
        "prev": "Phase Three", "curr": "Phase One", "p1": "Phase One", "p3": "Phase Three",
        "expected": True
    },
     {
        "name": "Custom Config Mismatch (Three -> One but expected 3 Phases)",
        "prev": "Phase Three", "curr": "Phase One", "p1": "Phase One", "p3": "3 Phases", # Config mismatch
        "expected": False
    },
    {
        "name": "Startup/Reload (Trigger is Undefined)",
        "prev": None, "curr": "1 Phase", "p1": "1 Phase", "p3": "3 Phases",
        "expected": False
    },
]

# Run tests
print(f"{'TEST NAME':<60} | {'RESULT':<10} | {'PASS/FAIL'}")
print("-" * 85)
all_passed = True
for t in tests:
    actual = evaluate(t["prev"], t["curr"], t["p1"], t["p3"])
    passed = actual == t["expected"]
    if not passed: all_passed = False
    print(f"{t['name']:<60} | {str(actual):<10} | {'PASS' if passed else 'FAIL'}")

if all_passed:
    print("\nALL TESTS PASSED")
    exit(0)
else:
    print("\nSOME TESTS FAILED")
    exit(1)
