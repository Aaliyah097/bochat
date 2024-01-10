from typing import TypeVar, Generic, Any, Tuple, Type, Dict
from pydantic import BaseModel
from database import Base
from sqlalchemy.orm import sessionmaker
from database import SessionFactory


DBO = TypeVar('DBO', bound=Base)
DTO = TypeVar('DTO', bound=BaseModel)


class Repository(Generic[DBO, DTO]):
    def __init__(self):
        self.session_factory: sessionmaker = SessionFactory

    @staticmethod
    def struct_from_tuple(keys: Tuple[str, ...], values: Tuple[Any, ...]) -> Dict:
        return dict(zip(keys, values))

    @staticmethod
    def dto_from_struct(struct: Dict, dto_cls: Type[DTO]) -> DTO:
        return dto_cls.model_validate(struct)

    @staticmethod
    def dto_from_dbo(dbo: DBO, dto_cls: Type[DTO]) -> DTO:
        payload = {}
        for column in dbo.__table__.columns:
            payload[column.name] = getattr(dbo, column.name)
        return dto_cls.model_validate(payload)
