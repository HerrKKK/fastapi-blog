from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from .relations import UserRole, RolePermission


class SysUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: Optional[str]
    email: Optional[str]
    password_hash: Optional[str]
    salt: Optional[str]

    roles: List["SysRole"] = Relationship(back_populates="users",
                                          link_model=UserRole)


class SysRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str]
    description: Optional[str]

    users: List["SysUser"] = Relationship(back_populates="roles",
                                          link_model=UserRole)
    permissions: List["SysPermission"]\
        = Relationship(back_populates="roles",
                       link_model=RolePermission)


class SysPermission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str]
    description: Optional[str]

    roles: List["SysRole"] = Relationship(back_populates="permissions",
                                          link_model=RolePermission)
