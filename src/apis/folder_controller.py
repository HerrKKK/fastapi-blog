import pickle

from fastapi import APIRouter, Depends
from redis import Redis

from dao import AsyncDatabase, AsyncRedis
from models import Content, Folder, Resource
from schemas import (
    FolderInput,
    FolderOutput,
    ResourcePreview,
    ResourceQuery,
    UserOutput
)
from service import RoleRequired, ResourceService, SecurityService


folder_router = APIRouter(
    prefix="/folder",
    tags=["folder"],
    dependencies=[Depends(AsyncDatabase.open_session)]
)


@folder_router.post("", response_model=FolderOutput)
async def add_folder(
    folder_input: FolderInput,
    cur_user: UserOutput = Depends(RoleRequired('admin'))
):

    folder = Folder(**folder_input.dict())
    folder.owner_id = cur_user.id
    folder.permission = 701  # owner all, group 0, public read
    return FolderOutput.init(
        await ResourceService.add_resource(folder)
    )


@folder_router.get("/count/{url:path}", response_model=int)
async def get_sub_count(
    url: str = None,
    resource_query: ResourceQuery = Depends(),
    cur_user: UserOutput = Depends(SecurityService.optional_login_required),
    redis: Redis = Depends(AsyncRedis.get_connection)
):
    if len(url) > 0 and url[0] != '/':
        url = f'/{url}'

    folder_str = await redis.get(f'folder:url:{url}')
    if folder_str is not None:
        folders = [pickle.loads(folder_str)]
    else:
        folders = await ResourceService.find_resources(Folder(url=url))
        await redis.set(f'folder:url:{url}', pickle.dumps(folders[0]))
    assert len(folders) == 1
    ResourceService.check_permission(folders[0], cur_user, 1)

    count = await redis.get(
        'count:url:{}:category_name:{}:tag_name:{}:page_idx:{}:page_size{}'
        .format(
            url,
            resource_query.category_name,
            resource_query.tag_name,
            resource_query.page_idx,
            resource_query.page_size
        )
    )
    need_refresh = await redis.get('count_need_refresh')
    if count is None or need_refresh is not None:
        count = await ResourceService.find_sub_count(
            folders[0].url,
            resource_query,
            Content
        )
        await redis.delete('count_need_refresh')
        await redis.set(
            'count:url:{}:category_name:{}:tag_name:{}:page_idx:{}:page_size{}'
            .format(
                url,
                resource_query.category_name,
                resource_query.tag_name,
                resource_query.page_idx,
                resource_query.page_size
            ),
            count
        )
    return count


@folder_router.get(
    "/sub_content/{url:path}", response_model=list[ResourcePreview]
)
async def get_folder(
    url: str = '',
    resource_query: ResourceQuery = Depends(),
    cur_user: UserOutput = Depends(SecurityService.optional_login_required),
    redis: Redis = Depends(AsyncRedis.get_connection)
):
    if len(url) > 0 and url[0] != '/':
        url = f'/{url}'

    folder_str = await redis.get(f'folder:url:{url}')
    if folder_str is not None:
        folders = [pickle.loads(folder_str)]
    else:
        folders = await ResourceService.find_resources(Folder(url=url))
        await redis.set(f'folder:url:{url}', pickle.dumps(folders[0]))

    assert len(folders) == 1
    ResourceService.check_permission(folders[0], cur_user, 1)

    preview_str = await redis.get(
        'preview:url:{}:category_name:{}:tag_name:{}:page_idx:{}:page_size{}'
        .format(
            url,
            resource_query.category_name,
            resource_query.tag_name,
            resource_query.page_idx,
            resource_query.page_size
        )
    )
    need_refresh = await redis.get('preview_need_refresh')
    if preview_str is not None and need_refresh is None:
        sub_resources = pickle.loads(preview_str)
    else:
        sub_resources = await ResourceService.find_sub_resources(
            url, resource_query, Content
        )
        await redis.delete('preview_need_refresh')
        await redis.set(
            'preview:url:{}:category_name:{}:tag_name:{}:page_idx:{}:page_size{}'
            .format(
                url,
                resource_query.category_name,
                resource_query.tag_name,
                resource_query.page_idx,
                resource_query.page_size
            ),
            pickle.dumps(sub_resources)
        )

    return [ResourcePreview.init(x) for x in sub_resources]


@folder_router.put(
    "", response_model=FolderOutput,
    dependencies=[Depends(RoleRequired('admin'))]
)
async def modify_folder(folder_input: FolderInput):
    return FolderOutput.init(
        await ResourceService.modify_resource(
            Folder(**folder_input.dict())
        )
    )


@folder_router.delete(
    "/{folder_id}", response_model=int,
    dependencies=[Depends(RoleRequired('admin'))]
)
async def delete_folder(folder_id: int = 0):
    return await ResourceService.remove_resource(Resource(id=folder_id))
