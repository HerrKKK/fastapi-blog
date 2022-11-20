import uuid

from models import Resource, Folder, ContentTag
from dao import BaseDao


class ResourceService:
    @staticmethod
    def add_resource(resource: Resource, db):
        resource.url = ''
        if resource.parent_id is not None and resource.parent_id != 0:
            parent = BaseDao.select(Resource(id=resource.parent_id),
                                    Resource, db)[0]
            resource.url = parent.url

        if isinstance(resource, Folder):
            resource.url += '/' + resource.title
        else:
            resource.url += '/' + str(uuid.uuid4())

        return BaseDao.insert(resource, db)

    @staticmethod
    def find_resources(resource: Resource, db):
        return BaseDao.select(resource, resource.__class__, db)

    @staticmethod
    def modify_resource(resource: Resource, db):
        return BaseDao.update(resource, resource.__class__, db)

    @staticmethod
    def remove_resource(resource: Resource, db):
        BaseDao.delete(resource, Resource, db)

    @staticmethod
    def modify_content_tags(resource_id: int,
                            add_tag_ids: list[int],
                            remove_tag_ids: list[int],
                            db):
        if add_tag_ids is not None and len(add_tag_ids) != 0:
            add_content_tags = [ContentTag(content_id=resource_id,
                                           tag_id=x)
                                for x in add_tag_ids]
            BaseDao.insert_all(add_content_tags, db)

        if remove_tag_ids is not None and len(remove_tag_ids) != 0:
            remove_content_tags = [ContentTag(content_id=resource_id,
                                              tag_id=x)
                                   for x in remove_tag_ids]

            BaseDao.delete_all(remove_content_tags, ContentTag, db)
