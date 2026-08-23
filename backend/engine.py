import hashlib
from typing import Dict, List, Tuple
import pandas as pd

def compute_event_hash(prev_hash: str, payload: Dict) -> str:
    """
    Computes a deterministic SHA-256 hash chaining the previous block hash
    with the current facility transaction telemetry.
    """
    serialized = (
        f"{prev_hash}|"
        f"{payload.get('facility_id')}|"
        f"{payload.get('item_id')}|"
        f"{payload.get('quantity')}|"
        f"{payload.get('action_type')}|"
        f"{payload.get('patient_token') or 'ANON'}"
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def evaluate_event_rules(event: Dict, historical_df: pd.DataFrame) -> Tuple[List[str], str]:
    """
    Evaluates incoming PHC logs against deterministic fraud & anomaly rules.
    Returns (violations_list, severity_level).
    """
    violations: List[str] = []
    severity: str = "LOW"
    
    qty = int(event.get("quantity", 0))
    footfall = int(event.get("patient_footfall", 0))
    action = str(event.get("action_type", "")).upper()
    patient_token = str(event.get("patient_token") or "").strip()
    
    # Rule 1: Ghost Dispensation (Stock draw without patient encounter record)
    if action == "DISPENSE" and not patient_token:
        violations.append("RULE_GHOST_DISPENSE: Critical stock drawdown without valid patient encounter token.")
        severity = "HIGH"

    # Rule 2: High Dispensation vs Low Footfall Outlier
    if action == "DISPENSE" and qty > 20 and footfall < 5:
        violations.append(f"RULE_FOOTFALL_MISMATCH: Outlier draw ({qty} units) registered against minimal footfall ({footfall} patients).")
        severity = "CRITICAL"

    # Rule 3: Abnormal Cold-Chain Spoilage Loss
    if action == "SPOILAGE":
        if qty >= 25:
            violations.append(f"RULE_SPOILAGE_SPIKE: Cold-chain batch loss ({qty} units) exceeds permissible threshold.")
            severity = "HIGH"

    # Rule 4: Bulk Depletion Drawdown
    if action == "DISPENSE" and qty >= 50:
        violations.append(f"RULE_BULK_DEPLETION: Single transaction volume ({qty} units) exceeds clinical safety baseline.")
        severity = "CRITICAL"

    return violations, severity