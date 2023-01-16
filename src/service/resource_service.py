import os
import uuid
from datetime import datetime
from typing import Type

from models import Resource, Folder, ResourceTag, Content
from dao import BaseDao, ResourceDao
from schemas import UserOutput


class ResourceService:
    @staticmethod
    def add_resource(resource: Resource) -> Resource:
        parent_url = ''
        if resource.parent_url is not None:
            parent = BaseDao.select(Resource(url=resource.parent_url),
                                    Resource)[0]
            parent_url = parent.url

        if isinstance(resource, Folder):
            resource.this_url = '/' + resource.title
        else:
            resource.this_url = '/' + str(uuid.uuid4())
        resource.url = parent_url + resource.this_url

        return BaseDao.insert(resource)

    @staticmethod
    def find_resources(resource: Resource) -> Resource:
        return BaseDao.select(resource, resource.__class__)

    @staticmethod
    def find_sub_resources(obj_class: Type = Resource,
                           parent_url: str = None,
                           category_name: str | None = None,
                           tag_name: str | None = None,
                           page_idx: int | None = 0,
                           page_size: int | None = 0) -> list[Resource]:
        return ResourceDao.get_sub_resources(obj_class,
                                             parent_url,
                                             category_name,
                                             tag_name,
                                             page_idx,
                                             page_size)

    @staticmethod
    def find_sub_count(obj_class: Type = Resource,
                       parent_url: str | None = None,
                       category_name: str | None = None,
                       tag_name: str | None = None) -> int:
        return ResourceDao.get_sub_resource_count(obj_class,
                                                  parent_url,
                                                  category_name,
                                                  tag_name)

    @staticmethod
    def modify_resource(resource: Resource) -> Resource:
        old_resources = BaseDao.select(Resource(id=resource.id),
                                       resource.__class__)
        assert len(old_resources) == 1
        sub_resources = ResourceService.find_sub_resources(
             Resource, parent_url=old_resources[0].url
        )

        if resource.__class__ == 'Folder':
            resource.this_url = '/' + resource.title
        else:
            resource.this_url = old_resources[0].this_url

        resource.url = resource.parent_url + resource.this_url

        resource.updated_time = datetime.now()
        res = BaseDao.update(resource, resource.__class__)
        if resource.url != old_resources[0].url:
            for re in sub_resources:
                # foreign key restraint: must update parent url to make it existing
                re.parent_url = resource.url
                ResourceService.modify_resource(re)

        return res

    @staticmethod
    def remove_resource(resource: Resource) -> int:
        return BaseDao.delete(resource, Resource)

    @staticmethod
    def reset_content_tags(content: Content):
        BaseDao.delete_all([ResourceTag(resource_id=content.id)], ResourceTag)
        add_content_tags = [ResourceTag(resource_id=content.id,
                                        tag_id=x.id)
                            for x in content.tags]

        if len(add_content_tags) > 0:
            BaseDao.insert_all(add_content_tags)

    @staticmethod
    async def trim_files(content_id: int, attach_files: set[str]):
        try:
            path = f'static/content/{content_id}'
            files = os.listdir(path)
            for filename in files:
                if attach_files is None or filename not in attach_files:
                    os.remove(f'{path}/{filename}')
        except Exception as e:
            print(e.__str__())

    @staticmethod
    def check_permission(
            resource: Resource,
            user: UserOutput,
            operation_mask: int) -> bool:

        permission = resource.permission % 10
        if user is not None:
            for role in user.roles:
                if role.name == 'admin':
                    return True
                if role.name == resource.group.name:
                    permission |= (resource.permission // 10) % 10
                    break
            if user.id == resource.owner_id:
                permission |= (resource.permission // 100) % 10

        if operation_mask & permission == 0:
            raise Exception('no permission')
        return True
