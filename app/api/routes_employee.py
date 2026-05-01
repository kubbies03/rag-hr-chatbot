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
    from app.db.models import Employee

    query = db.query(Employee)
    if status:
        query = query.filter(Employee.status == status)
    if department:
        query = query.filter(Employee.department == department)

    employees = query.all()
    return [emp.to_dict() for emp in employees]


@router.get("/api/employees/{employee_code}/status")
async def get_employee_status(
    employee_code: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single employee's status by code."""
    data = employee_service.get_employee_by_code(db, employee_code)
    if not data:
        raise HTTPException(status_code=404, detail="Employee not found")
    return data


@router.get("/api/employees/on-leave")
async def get_on_leave(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List employees currently on leave today."""
    return employee_service.get_employees_on_leave(db)


@router.get("/api/employees/expiring-contracts")
async def get_expiring(
    days: int = 30,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List contracts expiring soon."""
    return employee_service.get_expiring_contracts(db, within_days=days)


@router.get("/api/employees/stats")
async def get_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """HR overview statistics."""
    if user["role"] not in ["hr", "manager", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return employee_service.get_all_stats(db)
