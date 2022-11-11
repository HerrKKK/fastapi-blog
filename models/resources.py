from datetime import datetime

from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


class Folder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str]
    url: Optional[str]

    # created_time = Column(DateTime,
    #                       default=datetime.now,
    #                       comment="create time")
    #
    # modified_time = Column(DateTime,
    #                        default=datetime.now,
    #                        onupdate=datetime.now,
    #                        comment="update time")

    content_id: Optional[int] = Field(default=None, foreign_key="content.id")
    content: Optional["Content"] = Relationship(back_populates="folder")

    parent_id: Optional[int] = Field(default=None, foreign_key="folder.id")
    parent: Optional["Resource"] = Relationship(back_populates="sub_folders")

    sub_folders: List["Resource"] = Relationship(back_populates="parent")


class Content(SQLModel, table=True):
    id: Optional[int] = Field(default=None,
                              primary_key=True)
    folder: Optional["Content"] = Relationship(back_populates="content")

    sub_title: Optional[str]
    status: Optional[str]
    content: Optional[str]
