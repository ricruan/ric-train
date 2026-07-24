from typing import Optional, List

from pydantic import Field

from Base.Repository.base.baseVDB import BaseVDBModel


class VdbStudent(BaseVDBModel):
    """
    学生信息向量数据库模型
    """
    collection_alias = "student"
    description = "学生信息表"

    id: Optional[int] = Field(
        default=0,
        json_schema_extra={
            'is_primary': True,
            'auto_id': True
        }
    )

    db_id: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 50
        }
    )

    student_no: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 30
        }
    )

    name: Optional[str] = Field(
        default='',
        json_schema_extra={
            'enable_match': True,
            'enable_analyzer': True,
            'max_length': 50
        }
    )

    gender: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 10
        }
    )

    grade: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 20
        }
    )

    class_name: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 50
        }
    )

    status: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 20
        }
    )

    semantic_desc: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 65535
        }
    )

    embedding: Optional[List[float]] = Field(
        default_factory=list,
        json_schema_extra={
            'dim': 1024
        }
    )

    # 稀疏向量字段（基于 BM25 文本字段生成）
    content_sparse: Optional[List[float]] = Field(
        default_factory=list,
        json_schema_extra={
            'is_sparse_vector': True,
            'bm25_source_field': 'name'
        }
    )


if __name__ == "__main__":
    VdbStudent()
