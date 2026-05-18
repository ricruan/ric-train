"""
知识图谱数据模型

定义 Entity, Relation, ExtractionResult 三个 dataclass，
用于 NL2Cypher 抽取结果的数据传输。
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Entity:
    """知识图谱实体"""
    label: str          # 实体类型标签，如 "Person"
    properties: dict    # 实体属性字典，如 {"name": "马云"}


@dataclass
class Relation:
    """知识图谱关系"""
    rel_type: str            # 关系类型，如 "FOUNDED"
    from_entity: Entity      # 起始实体
    to_entity: Entity        # 目标实体
    properties: dict = field(default_factory=dict)  # 关系属性字典（可选）


@dataclass
class ExtractionResult:
    """NL2Cypher 抽取结果"""
    entities_created: int = 0
    relations_created: int = 0
    entities_skipped: List[str] = field(default_factory=list)
    relations_skipped: List[str] = field(default_factory=list)
    error: Optional[str] = None
