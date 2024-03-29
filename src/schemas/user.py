from __future__ import annotations

from pydantic import BaseModel

from models import SysUser, SysRole


class RoleSchema(BaseModel):
    @classmethod
    def init(cls, role: SysRole) -> RoleSchema | None:
        if role is None:
            return None
        return RoleSchema(id=role.id, name=role.name)
    id: int = None
    name: str = None


class UserInput(BaseModel):
    id: int = None
    username: str = None
    password: bytes = None
    email: str = None


class UserOutput(BaseModel):
    @classmethod
    def init(cls, sys_user: SysUser) -> UserOutput | None:
        if sys_user is None:
            return None
        return UserOutput(
            id=sys_user.id,
            username=sys_user.username,
            email=sys_user.email,
            roles=[
                RoleSchema.init(role)
                for role in sys_user.roles
            ]
        )

    id: int = None
    username: str = None
    email: str = None
    roles: list[RoleSchema] = None


class TokenResponse(BaseModel):
    access_token: str = None
    refresh_token: str = None
    token_type: str = 'bearer'
