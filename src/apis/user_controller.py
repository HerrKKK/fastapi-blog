from fastapi import APIRouter, Depends

from dao import AsyncDatabase
from models import SysUser
from schemas import UserInput, UserOutput
from service import RoleRequired, UserService


user_router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[
        Depends(RoleRequired('admin')),
        Depends(AsyncDatabase.open_session)
    ]
)


@user_router.post("", response_model=UserOutput)
async def add_user(user_input: UserInput):
    return await UserService.add_user(user_input)


@user_router.get("/{user_id}", response_model=list[UserOutput])
async def get_users(user_input: UserInput = Depends()):
    return await UserService.find_user(user_input)


@user_router.put("", response_model=UserOutput)
async def modify_users(user_input: UserInput):
    return await UserService.modify_user(SysUser(
        id=user_input.id,
        username=user_input.username,
        password_hash=user_input.password,
        email=user_input.email
    ))


@user_router.delete("/{user_id}", response_model=int)
async def remove_users(user_id: int):
    return await UserService.remove_user(UserInput(id=user_id))
