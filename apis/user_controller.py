from fastapi import APIRouter, Depends

from schemas import UserInput, UserOutput, Response
from service import UserService, SecurityService
from core.dependency import login_user


user_router = APIRouter(prefix="/user")


@user_router.post("/auth", response_model=Response)
async def login(user_input: UserInput):
    try:
        user_output = UserService.user_login(user_input)
        jwt = SecurityService.create_access_token(user_output)
        return Response(data=[user_output, jwt],
                        status='success')
    except Exception as e:
        return Response(status='failure',
                        message=e.__str__())


@user_router.post("/", response_model=Response)
async def add_user(user_input: UserInput):
    try:
        return Response(data=UserService.add_user(user_input),
                        status='success')
    except Exception as e:
        return Response(status='failure',
                        message=e.__str__())


@user_router.post("/update", response_model=Response)
async def modify_users(user_input: UserInput):
    try:
        return Response(data=UserService
                        .modify_user(user_input),
                        status='success')
    except Exception as e:
        return Response(status='failure',
                        message=e.__str__())


@user_router.get("/{user_id}", response_model=Response)
async def get_users(user_id: int,
                    username: str = None,
                    email: str = None,
                    cur_user: UserOutput = Depends(login_user)):
    try:
        print(cur_user.username)
        return Response(data=UserService
                        .find_user(UserInput(id=user_id,
                                             username=username,
                                             email=email)),
                        status='success')
    except Exception as e:
        return Response(status='failure',
                        message=e.__str__())
