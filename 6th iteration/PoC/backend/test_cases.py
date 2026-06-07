from __future__ import annotations

from typing import Any

import pandas as pd

TEST_CASE_TOPICS: dict[str, dict[str, Any]] = {
    "BRK": {
        "base_name": "Brake Control Verification",
        "test_type": "Functional Safety",
        "duration_base": 28,
        "descriptions": [
            "Verify commanded brake force accuracy under normal braking conditions.",
            "Verify brake pressure sensor fault detection within the required diagnostic time.",
            "Verify degraded braking mode entry when hydraulic pressure is below the safe threshold.",
            "Verify driver warning when regenerative braking is unavailable.",
            "Verify friction braking priority when regenerative braking torque is insufficient.",
            "Verify unintended brake release prevention during emergency braking.",
            "Verify stable brake force distribution during split-mu road conditions.",
            "Verify diagnostic trouble code storage when brake actuator response is delayed.",
            "Verify automatic hold release behavior above the configured speed threshold.",
            "Verify brake pedal plausibility using redundant pedal position signals.",
            "Verify brake actuator response timing during repeated braking events.",
            "Verify brake fault safe-state transition after communication timeout.",
            "Verify brake warning indicator request after critical braking fault detection.",
            "Verify brake control recovery behavior after transient voltage disturbance.",
            "Verify brake system traceability from safety requirement to executable test case.",
        ],
    },
    "STR": {
        "base_name": "Steering Assist Verification",
        "test_type": "Fault Injection",
        "duration_base": 32,
        "descriptions": [
            "Verify steering assist manual fallback after steering angle sensor fault detection.",
            "Verify assistance torque limitation when steering torque sensor values are inconsistent.",
            "Verify driver warning when electric power steering enters degraded mode.",
            "Verify unintended steering torque prevention during ignition-on self-test.",
            "Verify diagnostic trouble code storage when steering motor current exceeds the safe limit.",
            "Verify smooth assistance reduction when battery voltage is below the operating threshold.",
            "Verify steering angle sensor plausibility before lane keeping support activation.",
            "Verify manual steering availability after power assist failure.",
            "Verify assistance output suppression when calibration data is invalid.",
            "Verify steering motor overheating detection and torque derating request.",
            "Verify steering fallback timing under intermittent sensor communication loss.",
            "Verify steering control safe state after watchdog timeout.",
            "Verify steering diagnostic response after redundant signal mismatch.",
            "Verify steering assist availability after ignition cycle reset.",
            "Verify steering requirement traceability to fallback and diagnostic test cases.",
        ],
    },
    "LGT": {
        "base_name": "Lighting System Verification",
        "test_type": "Electrical Validation",
        "duration_base": 18,
        "descriptions": [
            "Verify headlamp beam intensity compliance during supply voltage fluctuation.",
            "Verify low beam fallback when high beam actuator feedback is invalid.",
            "Verify driver alert when adaptive headlamp leveling fails.",
            "Verify beam angle lowering under rear axle load increase to prevent glare.",
            "Verify safe default lighting mode when ambient light sensor input is unavailable.",
            "Verify left and right lamp synchronization during automatic beam adjustment.",
            "Verify diagnostic trouble code storage when LED driver temperature exceeds threshold.",
            "Verify daytime running lamp continuity after non-critical adaptive lighting failure.",
            "Verify open circuit failure detection in the low beam output channel.",
            "Verify adaptive bending function disablement when steering angle input is implausible.",
            "Verify headlamp recovery after transient electrical disturbance.",
            "Verify lighting fault communication to the instrument cluster.",
            "Verify lamp output status consistency during ignition cycle transition.",
            "Verify lighting control behavior under reduced battery voltage.",
            "Verify lighting requirement traceability to electrical validation evidence.",
        ],
    },
    "TRQ": {
        "base_name": "Powertrain Torque Verification",
        "test_type": "Dynamic Control",
        "duration_base": 40,
        "descriptions": [
            "Verify engine torque limitation to prevent wheel spin on low-traction surfaces.",
            "Verify torque reduction when accelerator pedal signals are inconsistent.",
            "Verify limp-home mode entry when throttle actuator feedback is invalid.",
            "Verify unintended acceleration prevention during startup initialization.",
            "Verify throttle response timing and delayed actuator movement detection.",
            "Verify torque request suppression when brake override is active.",
            "Verify torque reduction when coolant temperature exceeds the thermal protection threshold.",
            "Verify freeze-frame storage after safety-relevant torque monitoring fault detection.",
            "Verify torque request plausibility before forwarding output to the powertrain actuator.",
            "Verify torque command reset to safe default after watchdog timeout.",
            "Verify torque command arbitration during conflicting driver inputs.",
            "Verify powertrain diagnostic response after actuator communication timeout.",
            "Verify torque control stability during rapid pedal input change.",
            "Verify torque fallback behavior after invalid calibration detection.",
            "Verify torque requirement traceability to powertrain safety test cases.",
        ],
    },
    "SRS": {
        "base_name": "Airbag and Restraint Verification",
        "test_type": "Safety Critical Timing",
        "duration_base": 38,
        "descriptions": [
            "Verify frontal airbag deployment timing after confirmed crash detection.",
            "Verify passenger airbag suppression when occupant weight is below the threshold.",
            "Verify crash sensor plausibility before deployment decision.",
            "Verify deployment event data recording after crash-triggered activation.",
            "Verify driver alert when restraint control module memory corruption is detected.",
            "Verify deployment output disablement when squib resistance is outside the allowed range.",
            "Verify power-on self-test before enabling deployment readiness.",
            "Verify deployment readiness during transient battery voltage drop.",
            "Verify side-impact sensor failure detection and diagnostic trouble code setting.",
            "Verify unintended deployment prevention during normal driving vibration events.",
            "Verify restraint system safe state after internal watchdog reset.",
            "Verify crash signal confirmation logic using redundant sensor inputs.",
            "Verify airbag warning request to the instrument cluster after restraint degradation.",
            "Verify restraint diagnostic response for squib circuit open load condition.",
            "Verify restraint requirement traceability to deployment and suppression test evidence.",
        ],
    },
    "CLU": {
        "base_name": "Instrument Cluster Verification",
        "test_type": "HMI Verification",
        "duration_base": 16,
        "descriptions": [
            "Verify coolant temperature display accuracy across normal operating conditions.",
            "Verify brake system warning display after receiving critical brake fault signal.",
            "Verify airbag warning display when restraint system status is degraded.",
            "Verify battery thermal warning display after battery management system alert request.",
            "Verify steering assist warning display when electric power steering enters fallback mode.",
            "Verify safety-critical warning priority over infotainment notifications.",
            "Verify warning indicator visibility under day and night brightness settings.",
            "Verify safe warning display mode after display communication timeout.",
            "Verify last active warning state storage after ignition cycle reset.",
            "Verify telltale lamp operation during startup self-check.",
            "Verify cluster warning latency for high-priority safety messages.",
            "Verify cluster fault indication consistency during communication recovery.",
            "Verify cluster message display when multiple ECU warnings are active.",
            "Verify cluster fallback screen after invalid display data reception.",
            "Verify instrument cluster requirement traceability to HMI evidence.",
        ],
    },
    "LOCK": {
        "base_name": "Door Lock Control Verification",
        "test_type": "Body Control",
        "duration_base": 14,
        "descriptions": [
            "Verify door unlock prevention when vehicle speed is above the configured threshold.",
            "Verify automatic door unlock after crash event confirmation.",
            "Verify unlock request rejection when child lock safety mode is active.",
            "Verify door latch sensor inconsistency detection and driver notification.",
            "Verify locked state retention after transient communication loss with body control module.",
            "Verify diagnostic trouble code storage when lock actuator movement is incomplete.",
            "Verify driver door closed status before enabling drive-away locking.",
            "Verify unintended unlocking prevention during remote key authentication failure.",
            "Verify passive unlock disablement when key signal strength is below the security threshold.",
            "Verify audible feedback after successful remote lock command.",
            "Verify lock actuator response timing during repeated lock and unlock cycles.",
            "Verify crash unlock priority over normal lock state control.",
            "Verify door lock state consistency after ignition cycle reset.",
            "Verify body control diagnostic response after actuator short circuit detection.",
            "Verify door lock requirement traceability to body control test evidence.",
        ],
    },
    "BMS": {
        "base_name": "Battery Management Verification",
        "test_type": "Thermal Safety",
        "duration_base": 30,
        "descriptions": [
            "Verify driver alert when battery temperature exceeds safe thermal thresholds.",
            "Verify charging current limitation when cell temperature exceeds warning threshold.",
            "Verify high-voltage contactor opening when isolation resistance is below safe threshold.",
            "Verify cell voltage imbalance detection above the configured diagnostic threshold.",
            "Verify discharge power reduction when battery state of charge is critically low.",
            "Verify fault data storage when thermal runaway risk condition is detected.",
            "Verify current sensor plausibility using redundant measurement paths.",
            "Verify vehicle shutdown request when high-voltage interlock loop is open.",
            "Verify charging limitation status communication to the instrument cluster.",
            "Verify battery management safe state after internal watchdog failure.",
            "Verify battery thermal derating under sustained high-load discharge.",
            "Verify contactor command suppression after high-voltage diagnostic fault detection.",
            "Verify battery fault traceability from sensor input to driver warning request.",
            "Verify BMS communication timeout handling during charging operation.",
            "Verify battery requirement traceability to thermal and electrical safety evidence.",
        ],
    },
    "CC": {
        "base_name": "Cruise Control Verification",
        "test_type": "Driver Assistance",
        "duration_base": 17,
        "descriptions": [
            "Verify cruise control disengagement when the brake pedal is pressed.",
            "Verify cruise control disengagement when accelerator pedal override threshold is exceeded.",
            "Verify cruise control activation rejection below the minimum configured vehicle speed.",
            "Verify driver alert when radar input required for adaptive cruise is unavailable.",
            "Verify target speed maintenance within tolerance on level road.",
            "Verify activation request rejection when brake switch status is invalid.",
            "Verify smooth set-speed reduction when following distance becomes unsafe.",
            "Verify control output cancellation after communication timeout with powertrain controller.",
            "Verify diagnostic data storage when speed control actuator response is delayed.",
            "Verify visual indication when cruise control is active.",
            "Verify cruise control fallback after sensor plausibility failure.",
            "Verify cruise control state reset after ignition cycle transition.",
            "Verify cruise control driver override priority during active control.",
            "Verify adaptive cruise warning display after object detection loss.",
            "Verify cruise control requirement traceability to driver assistance evidence.",
        ],
    },
    "RVC": {
        "base_name": "Rearview Camera Verification",
        "test_type": "HMI Timing",
        "duration_base": 12,
        "descriptions": [
            "Verify rearview camera feed display within the required time after reverse gear selection.",
            "Verify driver warning when camera video signal is unavailable.",
            "Verify guide line overlay alignment within configured tolerance.",
            "Verify rear display switch-off after reverse gear is disengaged.",
            "Verify fallback warning screen after camera communication timeout.",
            "Verify image brightness adjustment during low-light reverse operation.",
            "Verify frozen image prevention during active reverse mode.",
            "Verify video frame freshness before rendering the image to the display.",
            "Verify diagnostic trouble code storage when camera module self-test fails.",
            "Verify dynamic guide line disablement when steering angle input is invalid.",
            "Verify rearview camera recovery after transient video signal interruption.",
            "Verify reverse gear input plausibility before camera activation.",
            "Verify rearview camera message display after camera calibration error.",
            "Verify camera feed timing during repeated gear shift cycles.",
            "Verify rearview camera requirement traceability to HMI timing evidence.",
        ],
    },
}

CONSTRAINT_PROFILES: list[dict[str, Any]] = [
    {
        "label": "Timing and latency constraint",
        "detail": "Constraint focus: response latency, diagnostic detection interval, debounce time, and timeout handling.",
        "duration_hours": 1,
    },
    {
        "label": "Voltage and electrical disturbance constraint",
        "detail": "Constraint focus: undervoltage, overvoltage, transient supply drop, short circuit, open load, and recovery after electrical disturbance.",
        "duration_hours": 3,
    },
    {
        "label": "Thermal operating constraint",
        "detail": "Constraint focus: high-temperature derating, cold-start behavior, thermal runaway prevention, overheating detection, and cooling recovery.",
        "duration_hours": 6,
    },
    {
        "label": "Sensor plausibility and redundancy constraint",
        "detail": "Constraint focus: redundant sensor mismatch, implausible signal range, stuck-at value, noisy signal filtering, and cross-check logic.",
        "duration_hours": 10,
    },
    {
        "label": "Communication and network constraint",
        "detail": "Constraint focus: CAN message loss, delayed message arrival, invalid payload, gateway routing failure, bus-off recovery, and stale signal handling.",
        "duration_hours": 14,
    },
    {
        "label": "Calibration and configuration constraint",
        "detail": "Constraint focus: invalid calibration data, variant coding mismatch, missing configuration parameter, and software baseline incompatibility.",
        "duration_hours": 22,
    },
    {
        "label": "Mechanical and actuator constraint",
        "detail": "Constraint focus: actuator saturation, limited movement range, mechanical backlash, incomplete movement, degraded output authority, and stuck actuator detection.",
        "duration_hours": 30,
    },
    {
        "label": "Environmental and road-load constraint",
        "detail": "Constraint focus: vibration, low-friction surface, slope, load variation, humidity, glare, ambient light shift, and harsh operating condition.",
        "duration_hours": 40,
    },
    {
        "label": "Human-machine interface constraint",
        "detail": "Constraint focus: warning priority, visibility, telltale consistency, driver acknowledgement, display fallback, and competing alert suppression.",
        "duration_hours": 52,
    },
    {
        "label": "Cybersecurity and access-control constraint",
        "detail": "Constraint focus: unauthorized diagnostic request, failed authentication, replayed command, invalid session transition, and secure fallback behavior.",
        "duration_hours": 64,
    },
    {
        "label": "Data integrity and memory constraint",
        "detail": "Constraint focus: corrupted memory, invalid checksum, freeze-frame consistency, event data recording, persistent fault storage, and recovery after reset.",
        "duration_hours": 78,
    },
    {
        "label": "Endurance and regression stability constraint",
        "detail": "Constraint focus: repeated operating cycles, long-duration stress, accumulated state drift, regression stability, and evidence consistency across reruns.",
        "duration_hours": 96,
    },
]


def duration_minutes_for_test_case(global_index: int) -> int:
    # Keep the full generated test portfolio below 720 hours total while still
    # including selected long-running tests up to 4 days for realistic regression planning.
    long_running_hours = {
        1: 96,
        2: 72,
        3: 48,
        4: 36,
        5: 24,
        6: 18,
        7: 12,
        8: 10,
        9: 8,
        10: 6,
    }
    if global_index in long_running_hours:
        return long_running_hours[global_index] * 60

    short_to_medium_hours = [1, 2, 3, 4, 5, 6]
    return short_to_medium_hours[(global_index - 11) % len(short_to_medium_hours)] * 60


def build_test_cases() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    global_index = 0
    for topic_position, (topic_code, topic_data) in enumerate(TEST_CASE_TOPICS.items()):
        for index, description in enumerate(topic_data["descriptions"], start=1):
            global_index += 1
            profile = CONSTRAINT_PROFILES[(topic_position * 3 + index - 1) % len(CONSTRAINT_PROFILES)]
            duration_minutes = duration_minutes_for_test_case(global_index)
            description_with_constraints = f"{description} {profile['detail']}"

            rows.append(
                {
                    "test_case_id": f"TC-{topic_code}-{index:03d}",
                    "test_case_name": f"{topic_data['base_name']} {index:03d}",
                    "description": description_with_constraints,
                    "constraint_category": profile["label"],
                    "duration_minutes": duration_minutes,
                    "test_type": topic_data["test_type"],
                }
            )
    return pd.DataFrame(rows)


TEST_CASES = build_test_cases()
