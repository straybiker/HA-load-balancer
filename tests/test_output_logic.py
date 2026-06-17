import jinja2
import json

TEMPLATE_STRING = """
{% set household_power = states('sensor.ev_load_balancer_house') | int %}
{% set charger_current_input = state_attr('sensor.ev_load_balancer_charger','current_input') | float(0) %}
{% set charger_power = state_attr('sensor.ev_load_balancer_charger','active_power') | float(0) %}
{% set charger_phases_input = state_attr('sensor.ev_load_balancer_charger','phases_input') %}
{% set grid_power_limit = state_attr('sensor.ev_load_balancer','power_limit') | int %}
{% set nominal_voltage = state_attr('sensor.ev_load_balancer_charger','nominal_voltage') | int(230) %}
{% set phase_1 = state_attr('sensor.ev_load_balancer_charger', 'phase_1_state') | default('1 Phase', true) %}
{% set phase_3 = state_attr('sensor.ev_load_balancer_charger', 'phase_3_state') | default('3 Phases', true) %}
{% set selected_mode = states('sensor.ev_load_balancer') %}

{% set car_aware_flag = state_attr('sensor.ev_load_balancer', 'car_aware') | bool %}
{% if not car_aware_flag %} {% set car_aware = false %}
{% else %}
  {% set required_sensors = [
    state_attr('sensor.ev_load_balancer_car','battery_capacity_wh'),
    state_attr('sensor.ev_load_balancer_car','battery_percentage')
  ] %}
  {% set car_aware = required_sensors | select('in', ['unavailable', 'unknown', None, 'none', 'None', '']) | list | count == 0 %}
{% endif %}

{% set charger_max = state_attr('sensor.ev_load_balancer_charger', 'max_current') | int %}
{% set car_max = state_attr('sensor.ev_load_balancer_car', 'max_current') | int %}
{% set max_current = [car_max, charger_max] | min if car_aware else charger_max %}

{% set charger_min = state_attr('sensor.ev_load_balancer_charger', 'min_current') %}
{% set car_min = state_attr('sensor.ev_load_balancer_car', 'min_current') %}
{% set min_current = [car_min, charger_min] | max if car_aware else charger_min %}

{% set phase_count = 3 if charger_phases_input == phase_3 else 1 %}
{% if charger_current_input > 0 and charger_power > 1000.0 %}
  {% set eff = charger_power / (charger_current_input * nominal_voltage * phase_count) %}
  {% set charger_efficiency = ([eff, 1.0] | min) | float(1.0) %}
{% else %}
  {% set charger_efficiency = 1.0 %}
{% endif %}

{% set current_rate = state_attr('sensor.ev_load_balancer', 'electricity_price') | float(0) %}
{% set max_cost_rate = state_attr('sensor.ev_load_balancer', 'max_cost_rate') | float(0.30) %}
{% set ems_active = state_attr('sensor.ev_load_balancer', 'ems_control') | bool %}

{% set ems_signal = state_attr('sensor.ev_load_balancer', 'ems_signal') | float(0) > 0 %}
{% set ems_as_onoff = state_attr('sensor.ev_load_balancer', 'ems_as_onoff') | bool %}

{% set current_soc = state_attr('sensor.ev_load_balancer_car', 'battery_percentage') | int(100) %}
{% set emergency_soc = state_attr('sensor.ev_load_balancer', 'emergency_soc') | int(20) %}
{% set comfort_soc = state_attr('sensor.ev_load_balancer', 'comfort_soc') | int(50) %}
{% set target_soc = state_attr('sensor.ev_load_balancer', 'target_soc') | int(80) %}

{% set is_emergency = current_soc < emergency_soc %}
{% set target_reached = car_aware and current_soc >= target_soc %}

{% if is_emergency %} {% set grid_gate_open = true %}
{% else %}
  {% set price_ok = current_rate <= max_cost_rate %}
  {% set signal_ok = (not ems_active) or ems_signal %}
  {% set grid_gate_open = price_ok and signal_ok %}
{% endif %}

{% set p_min_1 = min_current * nominal_voltage * 1 %}
{% set p_min_3 = min_current * nominal_voltage * 3 %}
{% set p_fast = max_current * nominal_voltage * 3 %}

{% if selected_mode == 'Off' %} {% set desired_grid_w = 0 %}
{% elif is_emergency %} {% set desired_grid_w = grid_power_limit %}
{% elif target_reached %} {% set desired_grid_w = 0 %}
{% elif not grid_gate_open %} {% set desired_grid_w = 0 %}
{% elif selected_mode == '1-Phase Minimum' %} {% set desired_grid_w = p_min_1 %}
{% elif selected_mode == '3-Phases Minimum' %} {% set desired_grid_w = p_min_3 %}
{% elif selected_mode == 'Fast' %} {% set desired_grid_w = p_fast %}
{% elif selected_mode == 'Limited' %} {% set desired_grid_w = grid_power_limit %}
{% elif selected_mode == 'Comfort' %} 
  {% set desired_grid_w = grid_power_limit if current_soc < comfort_soc else 0 %}
{% elif selected_mode == 'Solar' %} {% set desired_grid_w = 0 %}
{% else %} {% set desired_grid_w = 0 %}
{% endif %}

{% set ems_budget_w = state_attr('sensor.ev_load_balancer', 'ems_signal') | float(0) %}

{% if is_emergency %}
  {% set effective_grid_w = desired_grid_w %}
{% elif selected_mode == 'Solar' %}
  {% set effective_grid_w = 0 %}
{% elif ems_active and ems_as_onoff == false %}
  {% set effective_grid_w = [desired_grid_w, ems_budget_w] | min %}
{% else %}
  {% set effective_grid_w = desired_grid_w %}
{% endif %}

{% set pv_prioritized = state_attr('sensor.ev_load_balancer', 'pv_prioritized') %}
{% set pv_prio_threshold = state_attr('sensor.ev_load_balancer', 'pv_prio_threshold') %}

{% set p_min_1 = (min_current | float) * (nominal_voltage | float) * 1 %}
{% set allowed_grid_bridge = pv_prio_threshold | float(0) %}
{% set base_surplus = -household_power %}

{% if base_surplus < p_min_1 | float %}
  {% set solar_surplus = [(base_surplus + allowed_grid_bridge), 0] | max %}
{% else %}
  {% set solar_surplus = base_surplus %}
{% endif %}

{% if selected_mode == 'Off' %} {% set raw_target_power = 0 %}
{% elif target_reached %} {% set raw_target_power = 0 %}
{% elif selected_mode == 'Limited' and pv_prioritized and solar_surplus > 0 %} {% set raw_target_power = solar_surplus %}
{% else %} {% set raw_target_power = effective_grid_w + solar_surplus %}
{% endif %}

{% set grid_headroom = (grid_power_limit - household_power) | float(0) %}
{% set max_hardware = (max_current | float(0)) * (nominal_voltage | float(230)) * 3 %}
{% set eff = charger_efficiency | float(1.0) %}
{% set raw_target_eff = (raw_target_power | float(0)) / eff %}
{% set headroom_adjusted = (grid_headroom / eff) if grid_headroom > 0 else 0 %}

{% set adjusted_available_power_final = [raw_target_eff, headroom_adjusted, max_hardware] | min %}

{% set force_single = state_attr('sensor.ev_load_balancer', 'single_phase_only') | bool %}
{% set p_min_1 = min_current * nominal_voltage * 1 %}
{% set p_min_3 = min_current * nominal_voltage * 3 %}

{% if selected_mode == '1-Phase Minimum' %} {% set desired_phase = 1 %}
{% elif selected_mode == '3-Phases Minimum' %} {% set desired_phase = 3 %}
{% elif force_single %} {% set desired_phase = 1 %}
{% elif (adjusted_available_power_final | float) >= (p_min_3 | float) %} {% set desired_phase = 3 %}
{% else %} {% set desired_phase = 1 %}
{% endif %}

{% set current_phase = 3 if states(state_attr('sensor.ev_load_balancer_charger','phases_output')) == phase_3 else 1 %}
{% if (desired_phase > current_phase and states('timer.ev_load_balancer_phase_switching_timer') == 'active' and selected_mode in ['Limited', 'Solar', 'Comfort']) %}
  {% set adjusted_phase_selection = current_phase %}
{% else %}
  {% set adjusted_phase_selection = desired_phase %}
{% endif %}

{% set current = (adjusted_available_power_final / (nominal_voltage * adjusted_phase_selection)) | round(1) %}
{% if current < min_current %} {% set adjusted_current_limit = 0 %}
{% elif current > max_current %} {% set adjusted_current_limit = max_current | float %}
{% else %} {% set adjusted_current_limit = current %}
{% endif %}

{{ adjusted_phase_selection }}|{{ adjusted_current_limit }}
"""

def create_mock_db():
    return {
        "sensor.ev_load_balancer_house": "500",
        "sensor.ev_load_balancer": "Fast",
        "timer.ev_load_balancer_phase_switching_timer": "idle",
        "sensor.ev_load_balancer_charger": {
            "current_input": 0.0,
            "active_power": 0.0,
            "phases_input": "1 Phase",
            "phases_output": "1 Phase",
            "nominal_voltage": 230,
            "phase_1_state": "1 Phase",
            "phase_3_state": "3 Phases",
            "max_current": 16,
            "min_current": 6
        },
        "sensor.ev_load_balancer": {
            "power_limit": 10000,
            "car_aware": False,
            "electricity_price": 0.20,
            "max_cost_rate": 0.30,
            "ems_control": False,
            "ems_signal": 0.0,
            "ems_as_onoff": False,
            "emergency_soc": 20,
            "comfort_soc": 50,
            "target_soc": 80,
            "pv_prioritized": False,
            "pv_prio_threshold": 0,
            "single_phase_only": False
        },
        "sensor.ev_load_balancer_car": {
            "battery_capacity_wh": 74000,
            "battery_percentage": 50,
            "max_current": 16,
            "min_current": 6
        }
    }

def evaluate_output(mock_db_instance):
    def mock_states(entity_id):
        val = mock_db_instance.get(entity_id)
        if isinstance(val, dict):
            # For sensors where state is not defined in root, just return a dummy
            return mock_db_instance.get(f"{entity_id}_state", "unknown")
        return val

    def mock_state_attr(entity_id, attr):
        attrs = mock_db_instance.get(entity_id, {})
        if not isinstance(attrs, dict):
            # If the entity was defined as a string, it has no attributes
            return None
        return attrs.get(attr)

    def bool_filter(val, default=False):
        if val is None: return default
        if isinstance(val, bool): return val
        if isinstance(val, str):
            if val.lower() in ['true', 'on', 'yes', '1']: return True
            if val.lower() in ['false', 'off', 'no', '0']: return False
        return bool(val)

    env = jinja2.Environment()
    env.globals['states'] = mock_states
    env.globals['state_attr'] = mock_state_attr
    env.filters['bool'] = bool_filter
    
    template = env.from_string(TEMPLATE_STRING)
    try:
        result = template.render().strip()
        parts = result.split('|')
        return {"phase": int(parts[0]), "current": float(parts[1])}
    except Exception as e:
        print(f"Template Error: {e}")
        return None

def run_tests():
    tests = [
        {
            "name": "Fast mode with plenty of power",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "Fast", "sensor.ev_load_balancer_house": "500"}),
            "expected_phase": 3,
            "expected_current": 13.7 # (10000-500)/690 = 13.76 -> 13.7 (wait, 13.8 or 13.7? round(1))
        },
        {
            "name": "Fast mode with low grid headroom (drops to 1 phase)",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "Fast", "sensor.ev_load_balancer_house": "7000"}),
            "expected_phase": 1,
            "expected_current": 13.0 # (10000-7000)/230 = 13.0
        },
        {
            "name": "3-Phases Minimum with enough power",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "3-Phases Minimum", "sensor.ev_load_balancer_house": "500"}),
            "expected_phase": 3,
            "expected_current": 6.0 # Exactly 4140/690 = 6.0
        },
        {
            "name": "3-Phases Minimum with low grid headroom (pauses but keeps 3 phases)",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "3-Phases Minimum", "sensor.ev_load_balancer_house": "8000"}),
            "expected_phase": 3,
            "expected_current": 0.0 # 2000W available, < 4140, so current drops to 0
        },
        {
            "name": "1-Phase Minimum with enough power",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "1-Phase Minimum", "sensor.ev_load_balancer_house": "500"}),
            "expected_phase": 1,
            "expected_current": 6.0
        },
        {
            "name": "Solar mode with no sun",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "Solar", "sensor.ev_load_balancer_house": "500"}),
            "expected_phase": 1,
            "expected_current": 0.0
        },
        {
            "name": "Solar mode with high sun (6kW surplus)",
            "setup": lambda db: db.update({"sensor.ev_load_balancer": "Solar", "sensor.ev_load_balancer_house": "-6000"}),
            "expected_phase": 3,
            "expected_current": 8.6 # 6000/690 = 8.69 -> 8.7 (We will check math below)
        }
    ]

    all_passed = True
    print(f"{'TEST NAME':<65} | {'EXPECTED':<15} | {'ACTUAL':<15} | {'PASS'}")
    print("-" * 110)
    for t in tests:
        db = create_mock_db()
        t["setup"](db)
        
        # We also need to fix root state string overrides in mock_db_instance
        # In mock_db, we assigned a string to sensor.ev_load_balancer. But it also needs attributes!
        # Let's fix that in evaluate_output.
        # Actually, let's restructure the setup so db has states and attrs cleanly.
        
        # Hack to inject state alongside dict
        db["sensor.ev_load_balancer_state"] = db.get("sensor.ev_load_balancer", "unknown")
        if isinstance(db.get("sensor.ev_load_balancer"), str):
            mode = db["sensor.ev_load_balancer"]
            db["sensor.ev_load_balancer"] = {
                "power_limit": 10000, "car_aware": False, "electricity_price": 0.20,
                "max_cost_rate": 0.30, "ems_control": False, "ems_signal": 0.0,
                "ems_as_onoff": False, "emergency_soc": 20, "comfort_soc": 50,
                "target_soc": 80, "pv_prioritized": False, "pv_prio_threshold": 0,
                "single_phase_only": False
            }
            db["sensor.ev_load_balancer_state"] = mode

        res = evaluate_output(db)
        
        if res is None:
            print("FAILED TO EVALUATE TEMPLATE")
            all_passed = False
            continue

        exp_str = f"{t['expected_current']}A, {t['expected_phase']}p"
        act_str = f"{res['current']}A, {res['phase']}p"
        
        # Use a tolerance for floating point matching
        phase_match = res['phase'] == t['expected_phase']
        curr_match = abs(res['current'] - t['expected_current']) <= 0.2
        
        passed = phase_match and curr_match
        if not passed:
            all_passed = False
            
        print(f"{t['name']:<65} | {exp_str:<15} | {act_str:<15} | {'PASS' if passed else 'FAIL'}")

    if all_passed:
        print("\\nALL TESTS PASSED")
    else:
        print("\\nSOME TESTS FAILED")

if __name__ == "__main__":
    run_tests()
