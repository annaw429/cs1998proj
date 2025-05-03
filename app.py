from flask import Flask, request, jsonify
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
#
import temporary18
#from temporary18 import db, Patient, MedicalRecord, MedicalProvider
from temporary18 import Patient, MedicalRecord, MedicalProvider
import json

#db_filename="medical.db"
app = Flask(__name__)

'''app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()'''
    
# Reuse existing engine and models
engine = create_engine('sqlite:///medical.db')
Session = sessionmaker(bind=engine)
session = Session()

@app.route("/api/providers", methods=["POST"])
def create_provider():
    data = request.get_json()
    name = data.get("name")
    specialty = data.get("specialty")

    if not name or not specialty:
        return jsonify({"error": "Missing provider name or specialty"}), 400

    provider = MedicalProvider(name=name, specialty=specialty)
    session.add(provider)
    session.commit()
    return jsonify({"id": provider.id, "name": provider.name, "specialty": provider.specialty}), 201

@app.route("/api/providers/<int:provider_id>/records", methods=["POST"])
def create_record_for_provider(provider_id):
    provider = session.query(MedicalProvider).get(provider_id)
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    data = request.get_json()
    patient_name = data.get("patient_name")
    med_proc = data.get("medication_or_procedure")
    dose = data.get("dose")
    date_str = data.get("date")

    if not patient_name or not med_proc or not dose or not date_str:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

    # Check if patient exists or create new
    patient = session.query(Patient).filter_by(name=patient_name).first()
    if not patient:
        patient = Patient(name=patient_name)
        session.add(patient)
        session.commit()

    # Associate patient with provider if not already
    if provider not in patient.providers:
        patient.providers.append(provider)

    # Create medical record
    record = MedicalRecord(
        medication_or_procedure=med_proc,
        dose=dose,
        date=date,
        patient=patient,
        provider=provider  # don't append this is a many-to-one
    )
    session.add(record)
    session.commit()

    return jsonify({
        "id": record.id,
        "patient": patient.name,
        "provider": provider.name,
        "medication_or_procedure": record.medication_or_procedure,
        "dose": record.dose,
        "date": record.date.isoformat()
    }), 201

import csv
from flask import jsonify

@app.route("/api/providers/<int:provider_id>/patients/<int:patient_id>/records", methods=["DELETE"])
def delete_patient_records_with_provider(provider_id, patient_id):
    provider = session.query(MedicalProvider).get(provider_id)
    patient = session.query(Patient).get(patient_id)

    if not provider or not patient:
        return jsonify({"error": "Provider or patient not found"}), 404

    # Query records linking this patient and provider
    records = session.query(MedicalRecord).filter_by(
        provider_id=provider.id,
        patient_id=patient.id
    ).all()

    if not records:
        return jsonify({"message": "No records found for this patient with this provider"}), 200

    # Save to CSV
    filename = f"records_patient_{patient.id}_provider_{provider.id}.csv"
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Medication/Procedure", "Dose", "Date"])
        for record in records:
            writer.writerow([record.medication_or_procedure, record.dose, record.date.isoformat()])

    # Delete the records
    for record in records:
        session.delete(record)

    # Disassociate patient from provider
    if provider in patient.providers:
        patient.providers.remove(provider)

    session.commit()

    return jsonify({
        "message": f"{len(records)} record(s) deleted.",
        "csv_file": filename
    }), 200

'''@app.route("/api/providers-full", methods=["GET"])
def get_all_providers_full():
    providers = session.query(MedicalProvider).all()
    result = []

    for provider in providers:
        provider_data = {
            "id": provider.id,
            "name": provider.name,
            "specialty": provider.specialty,
            "patients": []
        }

        for patient in provider.patients:
            # Get only this patient's records associated with this provider
            records = session.query(MedicalRecord).filter_by(
                provider_id=provider.id,
                patient_id=patient.id
            ).all()

            patient_data = {
                "id": patient.id,
                "name": patient.name,
                "records": [
                    {
                        "id": record.id,
                        "medication_or_procedure": record.medication_or_procedure,
                        "dose": record.dose,
                        "date": record.date.isoformat()
                    }
                    for record in records
                ]
            }
            provider_data["patients"].append(patient_data)

        result.append(provider_data)

    return jsonify(result), 200'''

@app.route("/api/providers", methods=["GET"])
def get_all_providers():
    # Retrieve all providers from the database
    providers = session.query(MedicalProvider).all()

    result = []

    for provider in providers:
        # Get all patients associated with the provider
        patients = [patient.name for patient in provider.patients]
        
        # Get all medical records associated with the provider
        medical_records = []
        for record in provider.records:
            record_data = {
                "id": record.id,
                "medication_or_procedure": record.medication_or_procedure,
                "dose": record.dose,
                "date": record.date.isoformat(),
                "patient": record.patient.name
            }
            medical_records.append(record_data)

        # Add provider information to the result
        provider_data = {
            "id": provider.id,
            "name": provider.name,
            "specialty": provider.specialty,
            "patients": patients,
            "medical_records": medical_records
        }

        result.append(provider_data)

    return jsonify(result), 200


@app.route("/api/providers/<int:provider_id>/patients", methods=["GET"])
def get_patients_and_records_for_provider(provider_id):
    provider = session.query(MedicalProvider).get(provider_id)
    
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    result = []

    # Iterate over all patients associated with this provider
    for patient in provider.patients:
        # Get records for the patient with the specific provider
        records = session.query(MedicalRecord).join(record_providers).filter(
            record_providers.c.provider_id == provider.id,
            MedicalRecord.patient_id == patient.id
        ).all()

        patient_data = {
            "id": patient.id,
            "name": patient.name,
            "records": [
                {
                    "id": record.id,
                    "medication_or_procedure": record.medication_or_procedure,
                    "dose": record.dose,
                    "date": record.date.isoformat()
                }
                for record in records
            ]
        }

        result.append(patient_data)

    return jsonify(result), 200


@app.route("/api/patients/<int:patient_id>/records", methods=["GET"])
def get_medical_records_for_patient(patient_id):
    patient = session.query(Patient).get(patient_id)
    
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    # Get all records for the patient
    records = session.query(MedicalRecord).filter_by(patient_id=patient_id).all()

    result = []

    for record in records:
        #provider_names = [provider.name for provider in record.providers]

        record_data = {
            "id": record.id,
            "medication_or_procedure": record.medication_or_procedure,
            "dose": record.dose,
            "date": record.date.isoformat(),
            "provider": record.provider #provider_names
        }

        result.append(record_data)

    return jsonify(result), 200

if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=8000, debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
