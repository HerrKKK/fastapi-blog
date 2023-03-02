import asyncio
import functools
import hashlib
from contextvars import ContextVar

import bcrypt
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError 
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
    create_async_engine
)
from sqlalchemy.orm import close_all_sessions

from config import Config, logger
from models import Base, SysUser, SysRole


ctx_db: ContextVar[AsyncSession | None] = ContextVar('ctx_db', default=None)


class AsyncDatabase:
    __engine: AsyncEngine = None
    __session_maker: async_sessionmaker = None

    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        if not cls.__engine:
            engine = create_async_engine(
                URL.create(**Config.database.__dict__), echo=False
            )
            cls.__engine = engine
            cls.__session_maker = async_sessionmaker(
                engine, expire_on_commit=False
            )
        return cls.__engine

    @classmethod
    async def close(cls):
        close_all_sessions()
        if cls.__engine:
            asyncio.create_task(cls.__engine.dispose())

    @classmethod
    async def open_session(cls) -> AsyncSession:
        async with cls.__session_maker() as session:
            ctx_db.set(session)
            yield session

    @classmethod
    def database_session(cls, method: callable) -> callable:
        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            session = ctx_db.get()
            if session is not None:
                return await method(*args, session=session, **kwargs)
            async with cls.__session_maker() as session:
                return await method(*args, session=session, **kwargs)
        return wrapper

    @classmethod
    async def init_database(cls):
        engine = create_async_engine(
            URL.create(
                drivername=Config.database.drivername,
                username=Config.database.username,
                password=Config.database.password,
                host=Config.database.host,
                port=Config.database.port
            ),
            # CREATE DATABASE cannot in transaction
            isolation_level='AUTOCOMMIT'
        )

        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(f'CREATE DATABASE {Config.database.database}')
                )
        except ProgrammingError:
            # postgres database existed
            pass
        except OperationalError:
            # sqlite dialect error
            pass
        finally:
            await engine.dispose()

        engine = await cls.get_engine()
        logger.info('database connected')
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # await commit() cannot be executed at the same time
        await cls.insert_admin()
        await cls.insert_root_folder()

    @classmethod
    async def insert_admin(cls):
        # wwr:test_password for dev
        session: AsyncSession = cls.__session_maker()
        try:
            admin_role = SysRole(**Config.admin.role)
            password: bytes = hashlib.sha256(
                Config.admin.password.encode()
            ).hexdigest().encode()
            salt: bytes = bcrypt.gensalt()
            password_hash: bytes = bcrypt.hashpw(password, salt)

            admin = SysUser(
                username=Config.admin.username,
                password_hash=password_hash.decode(),
                salt=salt.decode(),
                email=Config.admin.email
            )

            session.add(admin_role)
            session.add(admin)
            admin.roles.append(admin_role)

            await session.commit()
        except IntegrityError:
            pass
        except Exception as e:
            logger.warn(e)
            await session.rollback()
        finally:
            await session.close()

    @classmethod
    async def insert_root_folder(cls):
        session: AsyncSession = cls.__session_maker()
        try:
            for folder in Config.folders:
                session.add(folder)
            await session.commit()
        except IntegrityError:
            pass
        except Exception as e:
            logger.warn(e)
            await session.rollback()
        finally:
            await session.close()
