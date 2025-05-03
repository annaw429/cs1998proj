import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import csv
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
#
from flask_sqlalchemy import SQLAlchemy

Base = declarative_base()

#db = SQLAlchemy()

#tracks for refreshing
open_provider_tables = {}
open_patient_tables = {}

class Patient(Base):#(db.Model):#(Base):
    __tablename__ = 'patients'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    records = relationship("MedicalRecord", cascade="delete")
    providers = relationship("MedicalProvider", secondary="patient_providers", back_populates="patients")

# Many-to-many relationship between Patient and MedicalProvider
patient_providers = Table(
    'patient_providers', Base.metadata, #db.Model.metadata, #Base.metadata,
    Column('patient_id', Integer, ForeignKey('patients.id'), primary_key=True),
    Column('provider_id', Integer, ForeignKey('medical_providers.id'), primary_key=True)
)

class MedicalRecord(Base):#(db.Model):#(Base):
    __tablename__ = 'medical_records'
    id = Column(Integer, primary_key=True)
    medication_or_procedure = Column(String)
    dose = Column(String)
    date = Column(Date)
    #link to one patient, medical provider
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    provider_id = Column(Integer, ForeignKey('medical_providers.id'), nullable=False)

    patient = relationship("Patient", back_populates="records")
    #Many-to-One relationship
    provider = relationship("MedicalProvider", back_populates="records")

class MedicalProvider(Base):#(db.Model):#(Base):
    __tablename__ = 'medical_providers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    patients = relationship("Patient", secondary=patient_providers, back_populates="providers")
    # One-to-many
    records = relationship("MedicalRecord", back_populates="provider")


# Database setup
engine = create_engine('sqlite:///medical.db', echo=False)
Base.metadata.create_all(engine)  # This ensures that the database tables are created
Session = sessionmaker(bind=engine)
session = Session()

# Tkinter Setup
root = tk.Tk()
root.title("Livewell - Medical Records")
root.geometry("180x60")

# New Provider Popup
def new_provider_popup():
    popup = tk.Toplevel(root)
    popup.title("New Provider")
    popup.geometry("400x200")

    tk.Label(popup, text="Provider Name:").pack(pady=10)
    provider_name_entry = tk.Entry(popup)
    provider_name_entry.pack(pady=5)

    tk.Label(popup, text="Specialty:").pack(pady=10)
    specialty_entry = tk.Entry(popup)
    specialty_entry.pack(pady=5)

    def add_new_provider():
        provider_name = provider_name_entry.get().strip()
        specialty = specialty_entry.get().strip()

        if not provider_name or not specialty:
            messagebox.showwarning("Input Error", "All fields are required.")
            return

        # Create a new provider
        provider = MedicalProvider(name=provider_name, specialty=specialty)
        session.add(provider)
        session.commit()

        popup.destroy()

        # Open provider window
        open_provider_window(provider)

    tk.Button(popup, text="Create Provider", command=add_new_provider).pack(pady=10)

# New Patient Popup
'''def new_patient_popup():
    popup = tk.Toplevel(root)
    popup.title("New Patient")
    popup.geometry("400x200")

    tk.Label(popup, text="Patient Name:").pack(pady=10)
    patient_name_entry = tk.Entry(popup)
    patient_name_entry.pack(pady=5)

    def add_new_patient():
        patient_name = patient_name_entry.get().strip()
        if not patient_name:
            messagebox.showwarning("Input Error", "Patient name is required.")
            return

        # Create a new patient and add to the session
        patient = Patient(name=patient_name)
        session.add(patient)
        session.commit()

        # Close the popup window
        popup.destroy()

        # Open the new patient window
        open_patient_window(patient)

    tk.Button(popup, text="Create Patient", command=add_new_patient).pack(pady=10)'''

# Open a New Window for the Patient
def open_patient_window(patient):
    patient_window = tk.Toplevel(root)
    patient_window.title(f"Patient: {patient.name}")
    patient_window.geometry("800x600")

    # Create Table to Display Records
    patient_table_frame = tk.Frame(patient_window)
    patient_table_frame.pack(fill=tk.BOTH, expand=True)

    patient_columns = ("Medication/Procedure", "Dose", "Date", "Provider(s)")
    patient_table = ttk.Treeview(patient_table_frame, columns=patient_columns, show="headings")
    for col in patient_columns:
        patient_table.heading(col, text=col)
        patient_table.column(col, anchor=tk.CENTER)
    patient_table.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(patient_window, orient="vertical", command=patient_table.yview)
    patient_table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Track open patient windows
    open_patient_tables[patient.id] = (patient, patient_table)
    
    # Load patient-specific records
    load_patient_table(patient, patient_table)

    # Leave Provider Functionality
    def leave_provider():
        leave_popup = tk.Toplevel(patient_window)
        leave_popup.title("Leave Provider")
        leave_popup.geometry("400x200")

        tk.Label(leave_popup, text="Provider Name:").pack(pady=10)
        provider_name_entry = tk.Entry(leave_popup)
        provider_name_entry.pack(pady=5)

        def continue_leave():
            provider_name = provider_name_entry.get().strip()
            if not provider_name:
                messagebox.showwarning("Input Error", "Provider name is required.")
                return

            provider = session.query(MedicalProvider).filter_by(name=provider_name).first()
            if not provider:
                messagebox.showwarning("Provider Not Found", f"No provider found with the name {provider_name}.")
                return

            # Get records shared between this patient and provider
            records = session.query(MedicalRecord).filter(
                MedicalRecord.patient_id == patient.id,
                MedicalRecord.provider_id==provider.id
            ).all()

            if not records:
                messagebox.showinfo("No Records", f"No records found for {provider_name}.")
                leave_popup.destroy()
                return

            # Export records before deletion
            with open(f"{patient.name}_records_with_{provider_name}.csv", mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Medication/Procedure", "Dose", "Date"])
                for record in records:
                    writer.writerow([record.medication_or_procedure, record.dose, record.date])

            # Delete records linked to this provider
            for record in records:
                session.delete(record)
            session.commit()

            # After deleting records, check if the patient still has records with this provider
            remaining = session.query(MedicalRecord).filter(
                MedicalRecord.patient_id == patient.id,
                MedicalRecord.provider_id==provider.id
            ).count()

            if remaining == 0 and provider in patient.providers:
                patient.providers.remove(provider)
                session.commit()

            messagebox.showinfo("Success", f"Records with {provider_name} have been saved and deleted.")
    
            # Refresh patient window
            load_patient_table(patient, patient_table)

            # Refresh provider window if open
            if provider.id in open_provider_tables:
                _, provider_table = open_provider_tables[provider.id]
                load_provider_table(provider, provider_table)

            leave_popup.destroy()


        tk.Button(leave_popup, text="Continue", command=continue_leave).pack(pady=10)

    # Add Leave Provider Button
    tk.Button(patient_window, text="Leave Provider", command=leave_provider).pack(pady=10)

# Function to Reload Patient Table (to show added records)
def load_patient_table(patient, patient_table):
    for item in patient_table.get_children():
        patient_table.delete(item)

    records = session.query(MedicalRecord).filter(MedicalRecord.patient_id == patient.id).all()
    for r in records:
        provider_names = r.provider.name if r.provider else "None"
        patient_table.insert("", "end", values=(r.medication_or_procedure, r.dose, r.date, provider_names))


# Function to Reload Provider Table (to show added records)
def load_provider_table(provider, provider_table):
    for item in provider_table.get_children():
        provider_table.delete(item)

    records = session.query(MedicalRecord).filter(MedicalRecord.provider_id == provider.id).all()
    for r in records:
        patient_name = session.query(Patient).filter_by(id=r.patient_id).first().name
        provider_table.insert("", "end", values=(patient_name, r.medication_or_procedure, r.dose, r.date))

# Open Provider Window for each provider
def open_provider_window(provider):
    provider_window = tk.Toplevel(root)
    provider_window.title(f"Provider: {provider.name}")
    provider_window.geometry("800x600")
    
    # Create Table to Display Records for the Provider
    provider_table_frame = tk.Frame(provider_window)
    provider_table_frame.pack(fill=tk.BOTH, expand=True)

    provider_columns = ("Patient Name", "Medication/Procedure", "Dose", "Date")
    provider_table = ttk.Treeview(provider_table_frame, columns=provider_columns, show="headings")
    for col in provider_columns:
        provider_table.heading(col, text=col)
        provider_table.column(col, anchor=tk.CENTER)
    provider_table.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(provider_window, orient="vertical", command=provider_table.yview)
    provider_table.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Track open provider windows
    open_provider_tables[provider.id] = (provider, provider_table)
    
    # Load provider-specific records
    load_provider_table(provider, provider_table)

    # Add Add Record Button
    input_frame = tk.Frame(provider_window)
    input_frame.pack(pady=10)

    tk.Label(input_frame, text="Patient Name:").grid(row=0, column=0, padx=5, pady=5)
    patient_name_entry = tk.Entry(input_frame)
    patient_name_entry.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(input_frame, text="Medication/Procedure:").grid(row=1, column=0, padx=5, pady=5)
    med_proc_entry = tk.Entry(input_frame)
    med_proc_entry.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(input_frame, text="Dose:").grid(row=2, column=0, padx=5, pady=5)
    dose_entry = tk.Entry(input_frame)
    dose_entry.grid(row=2, column=1, padx=5, pady=5)

    tk.Label(input_frame, text="Date:").grid(row=3, column=0, padx=5, pady=5)
    date_entry = DateEntry(input_frame, width=18, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
    date_entry.grid(row=3, column=1, padx=5, pady=5)

    def add_provider_record():
        pname = patient_name_entry.get().strip()
        med_proc = med_proc_entry.get().strip()
        dose = dose_entry.get().strip()
        date_val = date_entry.get_date()

        if not pname or not med_proc or not dose:
            messagebox.showwarning("Input Error", "All fields are required.")
            return

        # Get or create patient
        patient = session.query(Patient).filter_by(name=pname).first()
        if not patient:
            patient = Patient(name=pname)
            session.add(patient)
            session.commit()

        record = MedicalRecord(
            medication_or_procedure=med_proc,
            dose=dose,
            date=date_val,
            patient=patient,
            provider=provider  # Link this record to the provider
        )
        
        # Associate the provider with the medical record
        record.provider_id = provider.id # Provider linked to the record
        session.add(record)
        session.commit()
        load_provider_table(provider, provider_table) #Reload the provider table
        #open_patient_window(patient) #open if not already open
        #Refresh
        if patient.id in open_patient_tables:
            _, patient_table = open_patient_tables[patient.id]
            load_patient_table(patient, patient_table)
        else:
            open_patient_window(patient)

    tk.Button(provider_window, text="Add Record", command=add_provider_record).pack(pady=10)

# Main Window
tk.Button(root, text="New Provider", command=new_provider_popup).pack(pady=10)

# Open all provider windows
def open_all_provider_windows():
    providers = session.query(MedicalProvider).all()
    for provider in providers:
        open_provider_window(provider)

# Open all patient windows
def open_all_patient_windows():
    patients = session.query(Patient).all()
    for patient in patients:
        open_patient_window(patient)

open_all_provider_windows()
open_all_patient_windows()

# Start the Tkinter GUI
root.mainloop()
