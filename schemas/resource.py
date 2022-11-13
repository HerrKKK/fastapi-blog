from pydantic import BaseModel
from datetime import datetime
from models import Folder, Content


class ResourceBase(BaseModel):
    id: int = None
    title: str = None
    parent_id: int = None


class FolderInput(ResourceBase):
    pass


class ContentInput(FolderInput):
    sub_title: str = None
    status: str = None
    content: str = None


class FolderOutput(ResourceBase):
    @classmethod
    def init(cls, folder: Folder):
        return FolderOutput(id=folder.id,
                            url=folder.url,
                            title=folder.title,
                            parent_id=folder.parent_id,
                            created_time=folder.created_time,
                            modified_time=folder.modified_time)

    url: str = None
    created_time: datetime = None
    modified_time: datetime = None


class ContentOutput(FolderOutput):
    @classmethod
    def init(cls, content: Content):
        return ContentOutput(id=content.id,
                             url=content.url,
                             parent_id=content.parent_id,
                             created_time=content.created_time,
                             modified_time=content.modified_time,
                             sub_title=content.sub_title,
                             status=content.status,
                             content=content.content)

    sub_title: str = None
    status: str = None
    content: str = None
