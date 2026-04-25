"""
models.py — Database table definitions.

3 main tables:
- employees: employee information
- attendance: daily check-in/out records
- leave_requests: leave request management
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Employee table — stores basic employee information."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_code = Column(String, unique=True, nullable=False)   # "EMP001"
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String)
    department = Column(String, nullable=False)                    # "engineering"
    position = Column(String, nullable=False)                      # "Backend Developer"
    status = Column(String, default="active")                      # active, on_leave, resigned, probation
    contract_type = Column(String, default="full_time")            # full_time, part_time, intern
    contract_start = Column(Date)
    contract_end = Column(Date)                                    # NULL = indefinite
    created_at = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")

    def to_dict(self) -> dict:
        """Convert to dict for use in LLM prompts."""
        return {
            "employee_code": self.employee_code,
            "name": self.name,
            "department": self.department,
            "position": self.position,
            "status": self.status,
            "contract_type": self.contract_type,
            "contract_start": str(self.contract_start) if self.contract_start else None,
            "contract_end": str(self.contract_end) if self.contract_end else None,
        }


class Attendance(Base):
    """Attendance table — daily check-in/out records."""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(String)      # "08:30"
    check_out = Column(String)     # "17:30"
    type = Column(String, default="office")  # office, remote, onsite, absent
    note = Column(String)

    employee = relationship("Employee", back_populates="attendances")

    def to_dict(self) -> dict:
        return {
            "employee_name": self.employee.name if self.employee else None,
            "date": str(self.date),
            "check_in": self.check_in,
            "check_out": self.check_out,
            "type": self.type,
            "note": self.note,
        }


class LeaveRequest(Base):
    """Leave request table — manages leave applications."""

    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    type = Column(String, nullable=False)        # annual, sick, personal, maternity
    status = Column(String, default="pending")   # pending, approved, rejected
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")

    def to_dict(self) -> dict:
        return {
            "employee_name": self.employee.name if self.employee else None,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "type": self.type,
            "status": self.status,
            "reason": self.reason,
        }
