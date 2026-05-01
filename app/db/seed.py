"""
seed.py — Generate sample data for demo.

Creates 20 employees, attendance records, and leave requests.
Run: python -m app.db.seed
"""

from datetime import date, timedelta
from app.db.session import engine, SessionLocal, init_db
from app.db.models import Base, Employee, Attendance, LeaveRequest


def seed_employees(db):
    """Create 20 sample employees."""
    employees = [
        # Engineering
        Employee(employee_code="EMP001", name="Nguyễn Văn An", email="an@company.com", phone="0901000001", department="engineering", position="Backend Developer", status="active", contract_type="full_time", contract_start=date(2023, 3, 1), contract_end=None),
        Employee(employee_code="EMP002", name="Trần Thị Bảo", email="bao@company.com", phone="0901000002", department="engineering", position="Frontend Developer", status="active", contract_type="full_time", contract_start=date(2023, 6, 15), contract_end=None),
        Employee(employee_code="EMP003", name="Lê Hoàng Cường", email="cuong@company.com", phone="0901000003", department="engineering", position="Mobile Developer", status="on_leave", contract_type="full_time", contract_start=date(2024, 1, 10), contract_end=None),
        Employee(employee_code="EMP004", name="Phạm Minh Dũng", email="dung@company.com", phone="0901000004", department="engineering", position="DevOps Engineer", status="active", contract_type="full_time", contract_start=date(2022, 9, 1), contract_end=None),
        Employee(employee_code="EMP005", name="Hoàng Thị Em", email="em@company.com", phone="0901000005", department="engineering", position="QA Engineer", status="probation", contract_type="full_time", contract_start=date(2026, 3, 1), contract_end=date(2026, 6, 1)),

        # HR
        Employee(employee_code="EMP006", name="Vũ Thị Phương", email="phuong@company.com", phone="0901000006", department="hr", position="HR Manager", status="active", contract_type="full_time", contract_start=date(2021, 5, 1), contract_end=None),
        Employee(employee_code="EMP007", name="Đỗ Văn Giang", email="giang@company.com", phone="0901000007", department="hr", position="HR Specialist", status="active", contract_type="full_time", contract_start=date(2023, 8, 15), contract_end=None),

        # Sales
        Employee(employee_code="EMP008", name="Ngô Thị Hà", email="ha@company.com", phone="0901000008", department="sales", position="Sales Manager", status="active", contract_type="full_time", contract_start=date(2022, 1, 10), contract_end=None),
        Employee(employee_code="EMP009", name="Bùi Văn Inh", email="inh@company.com", phone="0901000009", department="sales", position="Sales Executive", status="active", contract_type="full_time", contract_start=date(2024, 4, 1), contract_end=None),
        Employee(employee_code="EMP010", name="Đặng Thị Kim", email="kim@company.com", phone="0901000010", department="sales", position="Sales Executive", status="on_leave", contract_type="full_time", contract_start=date(2023, 11, 1), contract_end=None),

        # Marketing
        Employee(employee_code="EMP011", name="Cao Văn Lâm", email="lam@company.com", phone="0901000011", department="marketing", position="Marketing Manager", status="active", contract_type="full_time", contract_start=date(2022, 6, 1), contract_end=None),
        Employee(employee_code="EMP012", name="Lý Thị Mai", email="mai@company.com", phone="0901000012", department="marketing", position="Content Creator", status="active", contract_type="part_time", contract_start=date(2025, 1, 15), contract_end=date(2026, 7, 15)),

        # Finance
        Employee(employee_code="EMP013", name="Trịnh Văn Nam", email="nam@company.com", phone="0901000013", department="finance", position="Finance Manager", status="active", contract_type="full_time", contract_start=date(2021, 3, 1), contract_end=None),
        Employee(employee_code="EMP014", name="Phan Thị Oanh", email="oanh@company.com", phone="0901000014", department="finance", position="Accountant", status="active", contract_type="full_time", contract_start=date(2023, 2, 1), contract_end=None),

        # Management
        Employee(employee_code="EMP015", name="Hồ Văn Phúc", email="phuc@company.com", phone="0901000015", department="management", position="CEO", status="active", contract_type="full_time", contract_start=date(2020, 1, 1), contract_end=None),
        Employee(employee_code="EMP016", name="Mai Thị Quỳnh", email="quynh@company.com", phone="0901000016", department="management", position="CTO", status="active", contract_type="full_time", contract_start=date(2020, 1, 1), contract_end=None),

        # Interns
        Employee(employee_code="EMP017", name="Tô Văn Rồng", email="rong@company.com", phone="0901000017", department="engineering", position="Intern Developer", status="probation", contract_type="intern", contract_start=date(2026, 4, 1), contract_end=date(2026, 7, 1)),
        Employee(employee_code="EMP018", name="Châu Thị Sen", email="sen@company.com", phone="0901000018", department="marketing", position="Intern Designer", status="active", contract_type="intern", contract_start=date(2026, 3, 15), contract_end=date(2026, 6, 15)),

        # Resigned
        Employee(employee_code="EMP019", name="Lương Văn Tài", email="tai@company.com", phone="0901000019", department="engineering", position="Frontend Developer", status="resigned", contract_type="full_time", contract_start=date(2022, 5, 1), contract_end=date(2026, 2, 28)),
        Employee(employee_code="EMP020", name="Ung Thị Uyên", email="uyen@company.com", phone="0901000020", department="sales", position="Sales Executive", status="resigned", contract_type="full_time", contract_start=date(2023, 7, 1), contract_end=date(2026, 1, 31)),
    ]
    db.add_all(employees)
    db.commit()
    print(f"Created {len(employees)} employees")


def seed_attendance(db):
    """Create attendance records for the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    records = []
    for day_offset in range(min(today.weekday() + 1, 5)):  # Weekdays only
        current_date = monday + timedelta(days=day_offset)
        for emp_id in range(1, 17):  # 16 active employees
            if emp_id == 3 and day_offset >= 2:  # EMP003 on leave from Wednesday
                att_type, check_in, check_out = "absent", None, None
            elif emp_id == 10:  # EMP010 on leave
                att_type, check_in, check_out = "absent", None, None
            elif emp_id % 5 == 0:  # Some employees work remote
                att_type, check_in, check_out = "remote", "08:30", "17:30"
            elif emp_id % 7 == 0 and day_offset == 0:  # Late on Monday
                att_type, check_in, check_out = "office", "09:15", "18:00"
            else:
                att_type, check_in, check_out = "office", "08:30", "17:30"

            records.append(Attendance(
                employee_id=emp_id,
                date=current_date,
                check_in=check_in,
                check_out=check_out,
                type=att_type,
            ))

    db.add_all(records)
    db.commit()
    print(f"Created {len(records)} attendance records")


def seed_leave_requests(db):
    """Create sample leave requests."""
    today = date.today()
    leaves = [
        LeaveRequest(employee_id=3, start_date=today - timedelta(days=2), end_date=today + timedelta(days=3), type="annual", status="approved", reason="Annual leave, family vacation"),
        LeaveRequest(employee_id=10, start_date=today - timedelta(days=5), end_date=today + timedelta(days=5), type="sick", status="approved", reason="Medical treatment"),
        LeaveRequest(employee_id=1, start_date=today + timedelta(days=7), end_date=today + timedelta(days=9), type="annual", status="pending", reason="Personal leave"),
        LeaveRequest(employee_id=8, start_date=today + timedelta(days=14), end_date=today + timedelta(days=16), type="personal", status="pending", reason="Family matter"),
        LeaveRequest(employee_id=12, start_date=today - timedelta(days=10), end_date=today - timedelta(days=8), type="sick", status="approved", reason="Sick leave"),
    ]
    db.add_all(leaves)
    db.commit()
    print(f"Created {len(leaves)} leave requests")


def run_seed():
    """Run full database seed."""
    print("Starting sample data generation...\n")

    import os
    from app.core.config import settings
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "sqlite"), exist_ok=True)
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "chroma"), exist_ok=True)
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "docs"), exist_ok=True)
    print("Created data/ directories\n")

    init_db()
    print("Created database tables\n")

    db = SessionLocal()
    try:
        db.query(LeaveRequest).delete()
        db.query(Attendance).delete()
        db.query(Employee).delete()
        db.commit()

        seed_employees(db)
        seed_attendance(db)
        seed_leave_requests(db)
        print("\nDone! Database is ready for demo.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
