import asyncio
import os
import uuid
from datetime import datetime
from typing import Type, Sequence

from anyio import Path
from fastapi import HTTPException, status

from config import Config
from dao import BaseDao, ResourceDao
from models import Content, Folder, Resource, ResourceTag
from schemas import ResourceQuery, UserOutput


class ResourceService:
    @staticmethod
    async def add_resource(resource: Resource) -> Resource:
        parent_url = ''
        if resource.parent_url is not None:
            parent = (await BaseDao.select(
                Resource(url=resource.parent_url), Resource)
            )[0]
            parent_url = parent.url

        if isinstance(resource, Folder):
            resource.this_url = '/' + resource.title
        else:
            resource.this_url = '/' + str(uuid.uuid4())
        resource.url = parent_url + resource.this_url

        return await BaseDao.insert(resource)

    @staticmethod
    async def find_resources(resource: Resource) -> list[Resource]:
        return await BaseDao.select(resource, resource.__class__)

    @staticmethod
    async def find_sub_resources(
        parent_url: str | None = None,
        resource_query: ResourceQuery | None = ResourceQuery(),
        obj_class: Type | None = Resource
    ) -> Sequence[Resource]:
        return await ResourceDao.get_sub_resources(
            parent_url, resource_query, obj_class
        )

    @staticmethod
    async def find_sub_count(
        parent_url: str | None = None,
        resource_query: ResourceQuery | None = ResourceQuery(),
        obj_class: Type | None = Resource
    ) -> int:
        return await ResourceDao.get_sub_resource_count(
            parent_url, resource_query, obj_class
        )

    @staticmethod
    async def modify_resource(resource: Resource) -> Resource:
        old_resources = await BaseDao.select(
            Resource(id=resource.id), resource.__class__
        )
        assert len(old_resources) == 1
        sub_resources = await ResourceService.find_sub_resources(
            old_resources[0].url
        )

        if resource.__class__ == 'Folder':
            resource.this_url = '/' + resource.title
        else:
            resource.this_url = old_resources[0].this_url

        resource.url = resource.parent_url + resource.this_url

        resource.updated_time = datetime.now()
        res = await BaseDao.update(resource, resource.__class__)

        if resource.url != old_resources[0].url:
            tasks = []
            for sub in sub_resources:
                """
                foreign key restraint here:
                must update parent url to make it existing
                """
                sub.parent_url = resource.url
                tasks.append(ResourceService.modify_resource(sub))
            await asyncio.gather(*tasks)
        return res

    @staticmethod
    async def remove_resource(resource: Resource) -> int:
        return await BaseDao.delete(resource, Resource)

    @staticmethod
    async def reset_content_tags(content: Content):
        await BaseDao.delete_all(
            [ResourceTag(resource_id=content.id)], ResourceTag
        )
        add_content_tags = [
            ResourceTag(resource_id=content.id, tag_id=x.id)
            for x in content.tags
        ]

        if len(add_content_tags) > 0:
            # cannot run async because commit may race with close
            await BaseDao.insert_all(add_content_tags)

    @staticmethod
    async def trim_files(content_id: int, attach_files: set[str]):
        path = Path(f'{Config.static.content_path}/{content_id}')
        if not await Path.exists(path):
            return

        async def handle_files(folder: Path):
            tasks = []
            async for file in folder.iterdir():
                if attach_files is None or file.name not in attach_files:
                    tasks.append(file.unlink(missing_ok=True))
            await asyncio.gather(*tasks)
            if len(os.listdir(folder.__fspath__())) == 0:
                await folder.rmdir()

        asyncio.create_task(handle_files(path))

    @staticmethod
    def check_permission(
        resource: Resource,
        user: UserOutput,
        operation_mask: int
    ):
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='unauthorized'
            )
