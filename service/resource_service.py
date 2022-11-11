import uuid

from models import Folder
from dao import BaseDao


class ResourceService:
    @staticmethod
    def add_resource(resource):
        if resource.parent_id is None or resource.parent_id == 0:
            resource.parent_id = 1

        # parent = BaseDao.select(Resource(id=resource.parent_id),
        #                         Resource)[0]
        #
        # if isinstance(resource, Folder):
        #     resource.url = parent.url + '/' + resource.title
        # else:
        #     resource.url = parent.url + '/' + uuid.uuid4()

        return BaseDao.insert(resource)

    @staticmethod
    def find_resources(resource):
        return BaseDao.select(resource, resource.__class__)

    @staticmethod
    def modify_resource(resource):
        BaseDao.update(resource, resource.__class__)
        return resource

    @staticmethod
    def remove_resource(resource):
        BaseDao.delete(resource, resource.__class__)
