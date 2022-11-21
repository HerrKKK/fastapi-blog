from fastapi import APIRouter, Response, Depends
from sqlalchemy.orm import Session

import dao
from models import Content
from schemas import ContentInput, ContentOutput, ContentPreview, ContentTags
from service import ResourceService
from core.dependency import get_db


content_router = APIRouter(prefix="/content", tags=["content"])


@content_router.post("", response_model=ContentOutput)
async def add_content(content: ContentInput,
                      db: Session = Depends(get_db)):
    return ContentOutput.init(ResourceService
                              .add_resource(Content.init(content),
                                            db))


@content_router.get("",  response_model=list[ContentOutput])
async def get_content(content_id: int = None,
                      url: str = None,
                      parent_id: int = None,
                      author_id: int = None,
                      db: Session = Depends(get_db)):

    contents = ResourceService.find_resources(Content(id=content_id,
                                                      url=url,
                                                      parent_id=parent_id,
                                                      author_id=author_id),
                                              db)
    return [ContentOutput.init(x) for x in contents]


@content_router.get("/preview",  response_model=list[ContentPreview])
async def get_preview(parent_id: int = 0,
                      status: str = None,
                      tag_id: int = 0,
                      page_idx: int = 0,
                      page_size: int = 0,
                      db: Session = Depends(get_db)):

    contents = ResourceService.find_preview(db,
                                            parent_id,
                                            status,
                                            tag_id,
                                            page_idx,
                                            page_size)
    return [ContentPreview.init(x) for x in contents]


@content_router.put("", response_model=ContentOutput)
async def modify_content(content: ContentInput,
                         db: Session = Depends(get_db)):
    return ContentOutput.init(ResourceService
                              .modify_resource(Content.init(content), db))


@content_router.delete("/{content_id}")
async def delete_content(content_id: int,
                         db: Session = Depends(get_db)):
    ResourceService.remove_resource(Content(id=content_id), db)
    return Response(status_code=200)


@content_router.put("/tag", response_model=ContentOutput)
async def modify_content_tag(content_tags: ContentTags,
                             db: Session = Depends(get_db)):
    ResourceService.modify_content_tags(content_tags.content_id,
                                        content_tags.add_tag_ids,
                                        content_tags.remove_tag_ids,
                                        db)
    return "success"
