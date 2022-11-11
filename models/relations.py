from typing import Optional
from sqlmodel import Field, SQLModel


class UserRole(SQLModel, table=True):
    user_id: Optional[int] = Field(
        default=None, foreign_key="sysuser.id", primary_key=True
    )
    role_id: Optional[int] = Field(
        default=None, foreign_key="sysrole.id", primary_key=True
    )


class RolePermission(SQLModel, table=True):
    role_id: Optional[int] = Field(
        default=None, foreign_key="sysrole.id", primary_key=True
    )
    permission_id: Optional[int] = Field(
        default=None, foreign_key="syspermission.id", primary_key=True
    )
