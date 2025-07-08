# Test input
sample_input = {
    "patient_age": 65,
    "medications": [
        {"name": "Warfarin", "dose": 5, "unit": "mg"},
        {"name": "Aspirin", "dose": 150, "unit": "mg"},
        {"name": "Amiodarone", "dose": 200, "unit": "mg"},
        {"name": "Ibuprofen", "dose": 600, "unit": "mg"},
        {"name": "Lisinopril", "dose": 20, "unit": "mg"}
    ]
}

res = evaluate_medication_list(sample_input)
print("\n📋 Final Report:")
print(generate_summary_report(res))
