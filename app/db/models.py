"""Database table definitions."""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Employee table."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    phone = Column(String)
    department = Column(String, nullable=False)
    position = Column(String, nullable=False)
    status = Column(String, default="active")
    contract_type = Column(String, default="full_time")
    contract_start = Column(Date)
    contract_end = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")

    def to_dict(self) -> dict:
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
    """Attendance table."""

    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(String)
    check_out = Column(String)
    type = Column(String, default="office")
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


class QueryLog(Base):
    """Audit log for chat questions."""

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    user_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String)
    session_id = Column(String)
    question = Column(Text, nullable=False)
    intent = Column(String)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ConversationMessage(Base):
    """Persistent chat history."""

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class LeaveRequest(Base):
    """Leave request table."""

    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default="pending")
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
