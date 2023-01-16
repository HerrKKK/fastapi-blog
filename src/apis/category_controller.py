from fastapi import APIRouter, Depends

from schemas import TagSchema
from service import TagService, DatabaseService
from models import PostCategory, Tag
from .auth_controller import RequiresRoles


category_router = APIRouter(prefix="/category",
                            tags=["category"],
                            dependencies=[Depends(DatabaseService.open_session)])


@category_router.post("",
                      dependencies=[Depends(RequiresRoles('admin'))],
                      response_model=TagSchema)
async def add_category(category: TagSchema):
    return TagSchema.init(TagService.add_tag(PostCategory(name=category.name)))


@category_router.get("", response_model=list[TagSchema])
async def get_category(category: TagSchema = Depends()):
    tags = TagService.find_tag(PostCategory(id=category.id,
                                            name=category.name))
    return [TagSchema.init(x) for x in tags]


@category_router.put("",
                     dependencies=[Depends(RequiresRoles('admin'))],
                     response_model=TagSchema)
async def rename_category(category: TagSchema):
    return TagSchema.init(TagService.rename_tag(
        PostCategory(id=category.id, name=category.name)
    ))


@category_router.delete("/{category_id}",
                        dependencies=[Depends(RequiresRoles('admin'))],
                        response_model=int)
async def remove_tag(category_id: int):
    return TagService.remove_tag(Tag(id=category_id))
