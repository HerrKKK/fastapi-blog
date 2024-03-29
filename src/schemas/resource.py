from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel

from .tag import TagSchema
from models import Content, Folder, PostCategory, PostTag, Resource


class ResourceBase(BaseModel):
    id: int = None
    title: str = ''  # not null
    parent_url: str = None
    permission: int = None


class FolderInput(ResourceBase):
    pass


class ContentInput(FolderInput):
    category: TagSchema = None
    tags: list[TagSchema] = []
    sub_title: str = None
    files: set = None
    content: bytes = None


class FolderOutput(ResourceBase):
    url: str = None
    created_time: datetime = None
    updated_time: datetime = None

    @classmethod
    def init(cls, folder: Folder) -> FolderOutput | None:
        return FolderOutput(**folder.__dict__) if folder else None


class ResourcePreview(FolderOutput):
    owner_id: int = None
    type: str = None
    tags: list[TagSchema] = None
    category: TagSchema = None

    @classmethod
    def init(cls, resource: Resource) -> ResourcePreview | None:
        return cls.parse(**resource.__dict__) if resource else None

    @classmethod
    def parse(
        cls,
        tags: list[PostTag] = (),
        category: PostCategory | None = None,
        **kwargs
    ) -> ResourcePreview:
        if tags is not None:
            tags = [TagSchema(id=tag.id, name=tag.name) for tag in tags]
        if category is not None:
            category = TagSchema(id=category.id, name=category.name)
        return ResourcePreview(tags=tags, category=category, **kwargs)


class ContentOutput(ResourcePreview):
    content: bytes = None

    @classmethod
    def init(cls, content: Content) -> ContentOutput | None:
        return cls.parse(**content.__dict__) if content else None

    @classmethod
    def parse(
        cls,
        tags: list[PostTag] = (),
        category: PostCategory | None = None,
        **kwargs
    ) -> ContentOutput:
        if tags is not None:
            tags = [TagSchema(id=tag.id, name=tag.name) for tag in tags]
        if category is not None:
            category = TagSchema(id=category.id, name=category.name)
        return ContentOutput(tags=tags, category=category, **kwargs)
