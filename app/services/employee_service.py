"""
employee_service.py — Query employee data from SQLite.

Handles questions about:
- Employee status (active, on leave, resigned)
- Attendance (late arrivals, remote, absent)
- Leave requests (current leaves, pending approvals)
- Contracts (expiring, probation)
"""

from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.db.models import Employee, Attendance, LeaveRequest


def get_employee_by_name(db: Session, name: str) -> dict | None:
    """Find employee by name (fuzzy match)."""
    employee = db.query(Employee).filter(
        Employee.name.ilike(f"%{name}%")
    ).first()
    return employee.to_dict() if employee else None


def get_employee_by_code(db: Session, code: str) -> dict | None:
    """Find employee by code."""
    employee = db.query(Employee).filter(
        Employee.employee_code == code.upper()
    ).first()
    return employee.to_dict() if employee else None


def get_employees_on_leave(db: Session) -> list[dict]:
    """Get employees currently on approved leave today."""
    today = date.today()
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
        LeaveRequest.status == "approved",
    ).all()

    return [leave.to_dict() for leave in leaves]


def get_employees_by_status(db: Session, status: str) -> list[dict]:
    """Get employees filtered by status."""
    employees = db.query(Employee).filter(
        Employee.status == status
    ).all()
    return [emp.to_dict() for emp in employees]


def get_today_attendance(db: Session) -> list[dict]:
    """Get today's attendance records."""
    today = date.today()
    records = db.query(Attendance).filter(
        Attendance.date == today
    ).all()
    return [record.to_dict() for record in records]


def get_late_employees(db: Session, after_time: str = "09:00") -> list[dict]:
    """Get employees who checked in late today."""
    today = date.today()
    records = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.check_in > after_time,
        Attendance.type == "office",
    ).all()
    return [record.to_dict() for record in records]


def get_expiring_contracts(db: Session, within_days: int = 30) -> list[dict]:
    """Get contracts expiring within the specified period."""
    today = date.today()
    deadline = today + timedelta(days=within_days)
    employees = db.query(Employee).filter(
        Employee.contract_end.isnot(None),
        Employee.contract_end <= deadline,
        Employee.contract_end >= today,
        Employee.status != "resigned",
    ).all()
    return [emp.to_dict() for emp in employees]


def get_pending_leave_requests(db: Session) -> list[dict]:
    """Get leave requests pending approval."""
    requests = db.query(LeaveRequest).filter(
        LeaveRequest.status == "pending"
    ).all()
    return [req.to_dict() for req in requests]


def get_department_summary(db: Session, department: str) -> dict:
    """Get department overview."""
    employees = db.query(Employee).filter(
        Employee.department == department,
        Employee.status != "resigned",
    ).all()

    return {
        "department": department,
        "total": len(employees),
        "active": sum(1 for e in employees if e.status == "active"),
        "on_leave": sum(1 for e in employees if e.status == "on_leave"),
        "probation": sum(1 for e in employees if e.status == "probation"),
        "employees": [emp.to_dict() for emp in employees],
    }


def get_all_stats(db: Session) -> dict:
    """Get company-wide HR statistics."""
    all_emps = db.query(Employee).filter(Employee.status != "resigned").all()
    today_leaves = get_employees_on_leave(db)
    expiring = get_expiring_contracts(db)
    pending = get_pending_leave_requests(db)

    return {
        "total_employees": len(all_emps),
        "active": sum(1 for e in all_emps if e.status == "active"),
        "on_leave_today": len(today_leaves),
        "probation": sum(1 for e in all_emps if e.status == "probation"),
        "contracts_expiring_30d": len(expiring),
        "pending_leave_requests": len(pending),
    }


def format_employee_data(data) -> str:
    """Format employee data into readable text for LLM prompts."""
    if not data:
        return "No employee data found."

    if isinstance(data, dict):
        lines = [f"- {key}: {value}" for key, value in data.items() if value is not None]
        return "\n".join(lines)

    if isinstance(data, list):
        parts = []
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines = [f"  {key}: {value}" for key, value in item.items() if value is not None]
                parts.append(f"[{i}]\n" + "\n".join(lines))
        return "\n\n".join(parts)

    return str(data)
