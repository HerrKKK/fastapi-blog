import asyncio
import jwt
import secrets
from datetime import datetime, timedelta
from typing import cast, Coroutine

import bcrypt
from fastapi import Body, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis

from .mail_service import MailService
from .render_service import RenderService
from config import Config, logger, Status
from dao import AsyncRedis, BaseDao
from models import SysUser
from schemas import TokenResponse, UserInput, UserOutput


oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl='auth', auto_error=False
)


async def optional_login_required(
    response: Response,
    access_token: str = Depends(oauth2_scheme_optional),
    refresh_token: str | None = Header(default=None)
) -> UserOutput | None:
    if access_token is None:
        return None
    try:
        data = SecurityService.verify_jwt_token(
            access_token, Config.jwt.key
        )
    except jwt.ExpiredSignatureError:
        data = SecurityService.verify_jwt_token(
            refresh_token, Config.jwt.key
        )
        response.headers['X-token-need-refresh'] = 'true'
    except Exception as e:
        logger.warn(e)
        return None
    return UserOutput(**data)


async def login_required(
    result: UserOutput = Depends(optional_login_required)
) -> UserOutput:
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='unauthenticated'
        )
    return result


async def verify_2fa_token(
    two_fa_token: str | None = Header(default=None)
) -> UserOutput | None:
    if two_fa_token is None:
        return None
    try:
        data = SecurityService.verify_jwt_token(
            two_fa_token, Config.jwt.key
        )
    except Exception as e:
        logger.warn(e)
        return None
    return UserOutput(**data)


async def check_2fa_code(
    two_fa_code: str = Body(),
    user_output: UserOutput = Depends(verify_2fa_token),
    redis: Redis = Depends(AsyncRedis.get_connection)
):
    existed_code = await redis.get(
        f'2fa_code:username:{user_output.username}'
    )
    if existed_code.decode() != two_fa_code:
        raise HTTPException(
            status_code=Status.HTTP_441_2FA_FAILED,
            detail='otp mismatch, please try again'
        )
    asyncio.create_task(cast(Coroutine, redis.delete(
        f'need_2fa:username:{user_output.username}'
    )))
    asyncio.create_task(cast(Coroutine, redis.delete(
        f'2fa_code:username:{user_output.username}'
    )))
    return user_output


class SecurityService:
    ACCESS_TIMEOUT_HOUR, REFRESH_TIMEOUT_HOUR = 1, 24 * 7

    optional_login_required: callable = optional_login_required
    login_required: callable = login_required
    check_2fa_code: callable = check_2fa_code
    verify_2fa_token: callable = verify_2fa_token

    @staticmethod
    def get_password_hash(plain_password: bytes) -> bytes | None:
        if plain_password is None:
            return None
        return bcrypt.hashpw(plain_password, bcrypt.gensalt())

    @classmethod
    def verify_password(
        cls,
        plain_password: bytes,
        password_hash: bytes
    ) -> bool:
        return bcrypt.checkpw(plain_password, password_hash)

    @staticmethod
    def verify_jwt_token(jwt_token: str | bytes, key: str) -> dict[str, any]:
        return jwt.decode(
            jwt=jwt_token,
            key=key,
            algorithms=[Config.jwt.algorithm]
        )

    @staticmethod
    def create_jwt_token(
        user_info: UserOutput,
        key: str,
        **kwargs,   # default for access_token
    ) -> bytes:
        data = user_info.dict()
        delta = timedelta(**kwargs)
        data.update({'exp': datetime.utcnow() + delta})
        return jwt.encode(
            payload=data,
            key=key,
            algorithm=Config.jwt.algorithm,
            headers=Config.jwt.headers
        )

    @classmethod
    def create_access_tokens(cls, user_output: UserOutput) -> TokenResponse:
        return TokenResponse(
            access_token=cls.create_jwt_token(
                user_output,
                Config.jwt.key,
                hours=cls.ACCESS_TIMEOUT_HOUR
            ),
            refresh_token=cls.create_jwt_token(
                user_output,
                Config.jwt.key,
                hours=cls.REFRESH_TIMEOUT_HOUR
            )
        )

    @classmethod
    async def generate_2fa_code(
        cls,
        user_output: UserOutput,
        redis: Redis
    ):
        two_fa_code = str(secrets.randbelow(1000000)).zfill(6)
        logger.info(f'2fa code for {user_output.username} is {two_fa_code}')
        two_fa_page = RenderService.two_fa_code(two_fa_code)
        asyncio.create_task(MailService.send_mail_async(
            [user_output.email],
            subject=f'verification code for {user_output.username}',
            message=two_fa_page
        ))
        '''
        2fa_code and 2fa_token both has an expiration of 5 minutes
        users can refresh 2fa_code one time per 30 seconds according
        to api throttle imposed on /login, total expiration is 10min. 
        '''
        asyncio.create_task(cast(Coroutine, redis.set(
            f'2fa_code:username:{user_output.username}',
            two_fa_code, ex=300
        )))

    @classmethod
    def user_input_validation(cls, username: str, password: bytes):
        try:
            assert isinstance(username, str) and 3 <= len(username) <= 12
            assert isinstance(password, bytes) and len(password) == 64
        except AssertionError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='invalid username or password'
            )

    @classmethod
    async def user_login(
        cls,
        username: str,
        password: bytes,
    ) -> UserOutput:
        cls.user_input_validation(username, password)

        redis = await AsyncRedis.get_connection()
        sys_user, need_2fa = await asyncio.gather(
            BaseDao.select(UserInput(username=username), SysUser),
            redis.get(f'need_2fa:username:{username}'),
        )
        if len(sys_user) != 1:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'no such user: {username}'
            )
        sys_user = sys_user[0]

        if cls.verify_password(password, sys_user.password_hash) is False:
            await cast(Coroutine, redis.set(
                f'need_2fa:username:{username}', 'True'
            ))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='password mismatch'
            )
        '''
        1. First login success, nothing happens
        2. Login failed, set need_2fa
        3. Login success, after a failure (need_2fa set)
            if no 2fa code then generate and send it
            else raise exception
        4. IP throttle controlled by another dependency
        '''
        user_output = UserOutput.init(sys_user)
        if need_2fa is None and Config.two_fa.enforcement is False:
            return UserOutput.init(sys_user)
        # 2fa enforced below
        # if not isinstance(existed_code, bytes):
            # no 2fa code, generate 6 digits and return
        await cls.generate_2fa_code(user_output, redis)
        raise HTTPException(
            status_code=Status.HTTP_440_2FA_NEEDED,
            detail='please check the otp sent to {email}'.format(
                email=f'{sys_user.email[:2]}****{sys_user.email[-2:]}'
            ),
            headers={'X-2fa-token': cls.create_jwt_token(
                user_output, Config.two_fa.jwt_key, minutes=5
            )}
        )


class RoleRequired:
    def __init__(self, required_role: str):
        self.required_role = required_role

    async def __call__(
        self,
        user_output: UserOutput = Depends(SecurityService.login_required)
    ) -> UserOutput:

        for role in user_output.roles:
            if role.name == 'admin' or self.required_role == role.name:
                return user_output

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='no permission'
        )


class APIThrottle:
    def __init__(self, throttle: int | None = 30):
        self.throttle = throttle

    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(AsyncRedis.get_connection)
    ):
        key = 'throttle:url:{path}:method:{method}:ip:{ip}'.format(
            path=request.url.path,
            method=request.method,
            ip=request.client.host
        )
        if await redis.get(key) is not None:
            message = 'too frequent {method} to {path} from {host}'.format(
                method=request.method,
                path=request.url.path,
                host=request.client.host
            )
            # HTTP 429 Too Many Requests
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=message
            )
        asyncio.create_task(cast(
            Coroutine, redis.set(key, '0', ex=self.throttle)
        ))
