from models import SysUser
from service import alchemy_session


class UserDao:
    @staticmethod
    @alchemy_session
    def insert_user(sys_user: SysUser, db):
        db.add(sys_user)
        db.flush()
        db.commit()

        return sys_user

    @staticmethod
    @alchemy_session
    def query_users(sys_user: SysUser, db):
        res = db.query(SysUser)

        if sys_user.id != 0:
            res = res.filter(SysUser.id == sys_user.id)
        if sys_user.username is not None:
            res = res.filter(SysUser.username == sys_user.username)
        if sys_user.email is not None:
            res = res.filter(SysUser.email == sys_user.email)

        return res.all()