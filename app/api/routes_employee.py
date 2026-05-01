"""
routes_employee.py — Employee query endpoints.

Direct data endpoints for Android app to fetch employee data
without going through the chatbot (used for UI lists, dashboards).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.services import employee_service

router = APIRouter()

_PRIVILEGED_ROLES = {"hr", "manager", "admin"}
_HR_ADMIN_ROLES = {"hr", "admin"}


def _require_privileged(user: dict):
    if user["role"] not in _PRIVILEGED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _require_hr_admin(user: dict):
    if user["role"] not in _HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _is_own_record(user: dict, employee_code: str) -> bool:
    """Check if the request is for the caller's own record.

    Normalises both IDs (strip underscores, uppercase) to handle the
    demo mapping emp_001 → EMP001 without hard-coding the format.
    """
    uid = user.get("user_id", "").replace("_", "").upper()
    code = employee_code.replace("_", "").upper()
    return uid == code


@router.get("/api/employees")
async def list_employees(
    status: str = None,
    department: str = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List employees.

    Query params:
    - status: active, on_leave, probation, resigned
    - department: engineering, hr, sales, marketing, finance, management
    """
    _require_privileged(user)

    from app.db.models import Employee

    query = db.query(Employee)
    if status:
        query = query.filter(Employee.status == status)
    if department:
        query = query.filter(Employee.department == department)

    employees = query.all()
    return [emp.to_dict() for emp in employees]


@router.get("/api/employees/on-leave")
async def get_on_leave(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List employees currently on leave today."""
    _require_privileged(user)
    return employee_service.get_employees_on_leave(db)


@router.get("/api/employees/expiring-contracts")
async def get_expiring(
    days: int = 30,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List contracts expiring soon."""
    _require_hr_admin(user)
    return employee_service.get_expiring_contracts(db, within_days=days)


@router.get("/api/employees/stats")
async def get_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HR overview statistics."""
    _require_privileged(user)
    return employee_service.get_all_stats(db)


@router.get("/api/employees/{employee_code}/status")
async def get_employee_status(
    employee_code: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single employee's status by code.

    Privileged roles (hr/manager/admin) can query any employee.
    Employees may only query their own record.
    """
    if user["role"] not in _PRIVILEGED_ROLES and not _is_own_record(user, employee_code):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    data = employee_service.get_employee_by_code(db, employee_code)
    if not data:
        raise HTTPException(status_code=404, detail="Employee not found")
    return data
