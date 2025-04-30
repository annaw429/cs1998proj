import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import pandas as pd
import os

# -db setup
Base = declarative_base()

class Patient(Base):
    __tablename__ = 'patients'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")

class MedicalRecord(Base):
    __tablename__ = 'medical_records'
    id = Column(Integer, primary_key=True)
    medication_or_procedure = Column(String)
    dose = Column(String)
    date = Column(Date)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    patient = relationship("Patient", back_populates="records")

engine = create_engine('sqlite:///medical.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# GUI Setup
root = tk.Tk()
root.title("livewell.aah.org")
root.geometry("800x600")

# Input Fields
input_frame = tk.Frame(root)
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

# Add Record Function
def add_record():
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
        patient=patient
    )
    session.add(record)
    session.commit()
    load_table()
    clear_inputs()

def clear_inputs():
    patient_name_entry.delete(0, tk.END)
    med_proc_entry.delete(0, tk.END)
    dose_entry.delete(0, tk.END)
    date_entry.set_date(datetime.today())

# Search Bar
search_frame = tk.Frame(root)
search_frame.pack(pady=5)

tk.Label(search_frame, text="Search by Patient Name:").pack(side=tk.LEFT)
search_entry = tk.Entry(search_frame)
search_entry.pack(side=tk.LEFT, padx=5)

def filter_table():
    keyword = search_entry.get().strip().lower()
    for item in table.get_children():
        table.delete(item)
    results = session.query(MedicalRecord).join(Patient).filter(Patient.name.ilike(f"%{keyword}%")).all()
    for r in results:
        table.insert("", "end", values=(r.patient.name, r.medication_or_procedure, r.dose, r.date))

def reset_filter():
    search_entry.delete(0, tk.END)
    load_table()

tk.Button(search_frame, text="Search", command=filter_table).pack(side=tk.LEFT, padx=5)
tk.Button(search_frame, text="Reset", command=reset_filter).pack(side=tk.LEFT)

# Export and Delete
export_frame = tk.Frame(root)
export_frame.pack(pady=5)

tk.Label(export_frame, text="Export Patient Records:").pack(side=tk.LEFT)
export_entry = tk.Entry(export_frame)
export_entry.pack(side=tk.LEFT, padx=5)

def export_and_delete():
    name = export_entry.get().strip()
    if not name:
        messagebox.showwarning("Input Error", "Please enter a patient name.")
        return

    patient = session.query(Patient).filter_by(name=name).first()
    if not patient or not patient.records:
        messagebox.showinfo("Not Found", f"No records found for {name}.")
        return

    # Export records
    data = [{
        "Patient Name": patient.name,
        "Medication/Procedure": r.medication_or_procedure,
        "Dose": r.dose,
        "Date": r.date.strftime('%Y-%m-%d')
    } for r in patient.records]

    df = pd.DataFrame(data)
    filename = f"{name.replace(' ', '_')}.csv"
    df.to_csv(filename, index=False)

    # Delete records
    session.delete(patient)
    session.commit()

    messagebox.showinfo("Exported", f"Exported and deleted records for {name} to {filename}")
    export_entry.delete(0, tk.END)
    load_table()

tk.Button(export_frame, text="Export & Delete", command=export_and_delete).pack(side=tk.LEFT, padx=5)

# Upload CSV
def upload_csv():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return
    try:
        df = pd.read_csv(file_path)
        required_columns = {"Patient Name", "Medication/Procedure", "Dose", "Date"}
        if not required_columns.issubset(df.columns):
            messagebox.showerror("Invalid CSV", f"CSV must contain columns: {', '.join(required_columns)}")
            return

        for _, row in df.iterrows():
            pname = str(row["Patient Name"]).strip()
            med = str(row["Medication/Procedure"]).strip()
            dose = str(row["Dose"]).strip()
            try:
                date_val = pd.to_datetime(row["Date"]).date()
            except:
                continue

            patient = session.query(Patient).filter_by(name=pname).first()
            if not patient:
                patient = Patient(name=pname)
                session.add(patient)
                session.commit()

            record = MedicalRecord(
                medication_or_procedure=med,
                dose=dose,
                date=date_val,
                patient=patient
            )
            session.add(record)
        session.commit()
        messagebox.showinfo("Import Success", f"Imported records from {os.path.basename(file_path)}")
        load_table()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load CSV: {e}")

tk.Button(root, text="Upload CSV", command=upload_csv).pack(pady=10)

# Table Display
table_frame = tk.Frame(root)
table_frame.pack(fill=tk.BOTH, expand=True)

columns = ("Patient Name", "Medication/Procedure", "Dose", "Date")
table = ttk.Treeview(table_frame, columns=columns, show="headings")
for col in columns:
    table.heading(col, text=col)
    table.column(col, anchor=tk.CENTER)
table.pack(fill=tk.BOTH, expand=True)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
table.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Load Records into Table
def load_table():
    for item in table.get_children():
        table.delete(item)
    records = session.query(MedicalRecord).all()
    for r in records:
        table.insert("", "end", values=(r.patient.name, r.medication_or_procedure, r.dose, r.date))

# Submit Button
submit_button = tk.Button(root, text="Add Record", command=add_record)
submit_button.pack(pady=10)

# Load existing data
load_table()

# Start
root.mainloop()
