from typing import List, Dict
from dataclasses import dataclass
import dataclasses


@dataclass
class ZoteroCreator:
    creatorType: str
    firstName: str
    lastName: str


@dataclass
class ZoteroTag:
    tag: str
    type: int


@dataclass(init=True)
class ZoteroOutput:
    key: str
    version: int
    library: Dict[str, str]
    itemType: str
    title: str
    creators: List[ZoteroCreator]
    abstractNote: str
    genre: str
    repository: str
    archiveID: str
    place: str
    date: str
    series: str
    seriesNumber: str
    DOI: str
    citationKey: str
    url: str
    accessDate: str
    archive: str
    archiveLocation: str
    shortTitle: str
    language: str
    libraryCatalog: str
    callNumber: str
    rights: str
    extra: str
    tags: List[ZoteroTag]
    collections: List[str]
    relations: Dict[str, str]
    dateAdded: str
    dateModified: str

    def __init__(self, **kwargs):
        names = set([f.name for f in dataclasses.fields(self)])
        for k, v in kwargs.items():
            if k in names:
                setattr(self, k, v)
