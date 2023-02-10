import asyncio
import time

from fastapi import Depends, HTTPException
from redis.asyncio import Redis

from dao import AsyncRedis, BaseDao
from models import SysUser
from schemas import UserInput, UserOutput
from service.security_service import SecurityService


class UserService:
    @staticmethod
    async def user_login(
        user_input: UserInput,
        redis: Redis = Depends(AsyncRedis.get_connection)
    ) -> UserOutput:
        last_fail_time = await redis.get(
            f'login_failure:username:{user_input.username}'
        )
        if (
            last_fail_time is not None
            and int(time.time()) - last_fail_time < 30
        ):
            raise HTTPException(
                status_code=403,
                detail=f'too frequent attempt for {user_input.username}'
            )
        sys_user = (await BaseDao.select(user_input, SysUser))[0]

        if not SecurityService.verify_password(
            user_input.password,
            sys_user.salt,
            sys_user.password_hash
        ):
            # await here for possable dense requests.
            await redis.set(
                f'login_failure:username:{user_input.username}',
                int(time.time())
            )
            raise HTTPException(status_code=401, detail='password mismatch')

        asyncio.create_task(
            redis.delete(f'login_failure:username:{user_input.username}')
        )
        return UserOutput.init(sys_user)

    @staticmethod
    async def add_user(user_input: UserInput) -> UserOutput:
        sys_user = SysUser(
            id=user_input.id,
            username=user_input.username,
            email=user_input.email
        )

        sys_user.salt = SecurityService.generate_salt()
        sys_user.password_hash = SecurityService.get_password_hash(
            user_input.password, sys_user.salt
        )

        return UserOutput.init(await BaseDao.insert(sys_user))

    @staticmethod
    async def find_user(user_input: UserInput) -> list[UserOutput]:
        return list(map(
            lambda it: UserOutput.init(it),
            await BaseDao.select(user_input, SysUser)
        ))

    @staticmethod
    async def modify_user(user_input: UserInput) -> UserOutput:
        sys_user = (await BaseDao.select(
            SysUser(id=user_input.id), SysUser
        ))[0]

        if user_input.username is not None:
            sys_user.username = user_input.username
        if user_input.email is not None:
            sys_user.email = user_input.email
        if user_input.password is not None:
            sys_user.password_hash = SecurityService.get_password_hash(
                user_input.password, sys_user.salt
            )

        asyncio.create_task(BaseDao.update(sys_user, SysUser))
        return UserOutput.init(sys_user)

    @staticmethod
    async def remove_user(user_input: UserInput) -> int:
        return await BaseDao.delete(SysUser(id=user_input.id), SysUser)
