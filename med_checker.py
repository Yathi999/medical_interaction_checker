!pip install requests

import requests
import time
import json
import pandas as pd
from itertools import combinations

# Load fallback interaction dataset
fallback_df = pd.read_csv("fallback_interactions.csv")

def check_local_dataset(drug1, drug2):
    d1, d2 = drug1.lower(), drug2.lower()
    for _, row in fallback_df.iterrows():
        pair = {row["drug1"].lower(), row["drug2"].lower()}
        if {d1, d2} == pair:
            return row["severity"]
    return "Unknown"

def fetch_rxnorm_code(medication_name):
    try:
        response = requests.get("https://rxnav.nlm.nih.gov/REST/rxcui.json", params={"name": medication_name}, timeout=5)
        return response.json().get("idGroup", {}).get("rxnormId", [None])[0]
    except:
        return None

def retrieve_interactions(rxnorm_ids):
    interaction_data = []
    for combo in combinations(rxnorm_ids, 2):
        url = f"https://rxnav.nlm.nih.gov/REST/interaction/list.json?rxcuis={combo[0]}+{combo[1]}"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.text.strip():
                group_data = res.json().get("fullInteractionTypeGroup", [])
                interaction_data.extend(group_data)
        except:
            continue
        time.sleep(0.2)
    return interaction_data

def adjust_severity_based_on_dosage(d1, d2, severity, meds):
    d1 = d1.lower()
    d2 = d2.lower()
    med1 = next((m for m in meds if m["name"].lower() == d1), None)
    med2 = next((m for m in meds if m["name"].lower() == d2), None)

    if not med1 or not med2:
        return severity

    if {"aspirin", "warfarin"} <= {d1, d2}:
        if (d1 == "aspirin" and med1["dose"] > 100) or (d2 == "aspirin" and med2["dose"] > 100):
            return "High"

    if {"ibuprofen", "lisinopril"} <= {d1, d2}:
        if med1["dose"] > 400 or med2["dose"] > 400:
            return "High"

    return severity

def interpret_interactions(raw, meds):
    results = []
    for group in raw:
        for i_type in group.get("fullInteractionType", []):
            for pair in i_type.get("interactionPair", []):
                drugs = [c["name"].lower() for c in pair["interactionConcept"]]
                severity = pair.get("severity", "Unknown")
                note = pair.get("description", "")
                severity = adjust_severity_based_on_dosage(drugs[0], drugs[1], severity, meds)
                results.append({"drugs": drugs, "severity": severity, "description": note})
    return results

def evaluate_medication_list(patient):
    meds = patient["medications"]
    age = patient.get("patient_age", "?")
    rxcuis = []

    print("🧬 Resolving RXNorm codes...")
    for med in meds:
        code = fetch_rxnorm_code(med["name"])
        print(f"  {med['name']} → RXCUI: {code}")
        if code:
            rxcuis.append(code)
        time.sleep(0.2)

    raw = retrieve_interactions(rxcuis)

    if not raw:
        print("⚠️ RxNav returned nothing. Checking fallback dataset...")
        alerts = []
        for a, b in combinations(meds, 2):
            sev = check_local_dataset(a["name"], b["name"])
            if sev != "Unknown":
                sev = adjust_severity_based_on_dosage(a["name"], b["name"], sev, meds)
                alerts.append({
                    "drugs": [a["name"], b["name"]],
                    "severity": sev,
                    "description": "From fallback dataset"
                })
        return {"age": age, "interactions": alerts}

    return {"age": age, "interactions": interpret_interactions(raw, meds)}

def generate_summary_report(data):
    if not data["interactions"]:
        return "✅ No significant drug interactions found."
    lines = [f"⚠️ Interactions for patient age {data['age']}:"]
    for i, alert in enumerate(data["interactions"], 1):
        drugs = ", ".join(alert["drugs"])
        lines.append(f"\n{i}. {drugs}\n   Severity: {alert['severity']}\n   Note: {alert['description']}")
    return "\n".join(lines)
