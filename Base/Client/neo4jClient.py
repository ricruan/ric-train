import logging
from typing import Optional, List, Dict, Any

from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError

from Base.Config.logConfig import setup_logging
from Base.Config.setting import settings

setup_logging()
logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j 图数据库客户端，封装基础的增删改查操作。
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        neo4j_conf = settings.neo4j.dict()
        self.uri = uri or neo4j_conf["uri"]
        self.user = user or neo4j_conf["user"]
        self.password = password or neo4j_conf["password"]
        self.database = database or neo4j_conf["database"]

        self._driver = GraphDatabase.driver(
            self.uri, auth=(self.user, self.password)
        )
        logger.info(f"Neo4jClient 已初始化，连接到 {self.uri}")

    def close(self):
        """关闭驱动连接。"""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j 连接已关闭")

    def run(self, cypher: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        执行原生 Cypher 查询，返回结果列表。
        """
        try:
            with self._driver.session(database=self.database) as session:
                result = session.run(cypher, parameters or {})
                return [record.data() for record in result]
        except Neo4jError as e:
            logger.error(f"Cypher 执行失败: {e}\n  cypher: {cypher}\n  params: {parameters}")
            return []

    # ──────────────── 增 ────────────────

    def create_node(self, label: str, properties: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        创建单个节点。
        :param label: 节点标签，如 "Person"
        :param properties: 节点属性字典，如 {"name": "Alice", "age": 30}
        """
        props = properties or {}
        params = {"props": props}
        props_str = "$props" if props else ""
        cypher = f"CREATE (n:{label} {props_str}) RETURN n"
        return self.run(cypher, params)

    def create_relationship(
        self,
        from_label: str, from_props: Dict,
        to_label: str, to_props: Dict,
        rel_type: str, rel_props: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        在两个已有节点之间创建关系。
        :param from_label: 起始节点标签
        :param from_props: 起始节点匹配属性
        :param to_label: 终止节点标签
        :param to_props: 终止节点匹配属性
        :param rel_type: 关系类型，如 "KNOWS"
        :param rel_props: 关系属性字典
        """
        rp = rel_props or {}
        # Neo4j 不支持在 MATCH 中使用参数化属性字典，需展开为 WHERE 子句
        from_where = " AND ".join(f"a.{k} = $from_{k}" for k in from_props)
        to_where = " AND ".join(f"b.{k} = $to_{k}" for k in to_props)

        where_parts = []
        if from_where:
            where_parts.append(from_where)
        if to_where:
            where_parts.append(to_where)
        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""

        rel_props_str = "$rel_props" if rp else ""
        cypher = (
            f"MATCH (a:{from_label}), (b:{to_label}){where_clause} "
            f"CREATE (a)-[r:{rel_type} {rel_props_str}]->(b) RETURN r"
        )
        params = {f"from_{k}": v for k, v in from_props.items()}
        params.update({f"to_{k}": v for k, v in to_props.items()})
        if rp:
            params["rel_props"] = rp
        return self.run(cypher, params)

    # ──────────────── 查 ────────────────

    def get_node(self, label: str, properties: Dict) -> List[Dict[str, Any]]:
        """
        按属性查询节点。
        """
        cypher = f"MATCH (n:{label} $props) RETURN n"
        return self.run(cypher, {"props": properties})

    def get_all_nodes(self, label: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取指定标签的全部节点（带 limit 保护）。
        """
        cypher = f"MATCH (n:{label}) RETURN n LIMIT $limit"
        return self.run(cypher, {"limit": limit})

    def get_relationships(
        self,
        rel_type: Optional[str] = None,
        from_label: Optional[str] = None,
        to_label: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询关系，可过滤关系类型、起始/终止节点标签。
        """
        parts = ["MATCH"]
        from_var = "a"
        to_var = "b"
        from_clause = f"({from_var}:{from_label})" if from_label else f"({from_var})"
        to_clause = f"({to_var}:{to_label})" if to_label else f"({to_var})"
        rel_clause = f"-[r:{rel_type}]->" if rel_type else "-[r]->"
        parts.append(f"{from_clause}{rel_clause}{to_clause}")
        parts.append(f"RETURN a, r, b LIMIT $limit")
        cypher = " ".join(parts)
        return self.run(cypher, {"limit": limit})

    # ──────────────── 改 ────────────────

    def update_node(
        self, label: str, match_props: Dict, update_props: Dict
    ) -> List[Dict[str, Any]]:
        """
        更新节点属性（SET 模式，仅更新传入的字段）。
        :param label: 节点标签
        :param match_props: 用于匹配节点的属性
        :param update_props: 要更新的属性
        """
        cypher = (
            f"MATCH (n:{label} $match_props) "
            f"SET n += $update_props RETURN n"
        )
        return self.run(cypher, {"match_props": match_props, "update_props": update_props})

    # ──────────────── 删 ────────────────

    def delete_node(self, label: str, properties: Dict, detach: bool = True) -> int:
        """
        删除节点。
        :param label: 节点标签
        :param properties: 匹配属性
        :param detach: True 时同时删除关联关系（DETACH DELETE），False 仅删除孤立节点
        """
        keyword = "DETACH DELETE" if detach else "DELETE"
        cypher = f"MATCH (n:{label} $props) {keyword}"
        self.run(cypher, {"props": properties})
        return 1

    def delete_relationship(
        self,
        from_label: str, from_props: Dict,
        to_label: str, to_props: Dict,
        rel_type: Optional[str] = None,
    ) -> int:
        """
        删除两个节点之间的关系。
        """
        rel_clause = f":[r:{rel_type}]" if rel_type else ":[r]"
        cypher = (
            f"MATCH (a:{from_label} $from_props){rel_clause}->(b:{to_label} $to_props) "
            f"DELETE r"
        )
        result = self.run(cypher, {"from_props": from_props, "to_props": to_props})
        return len(result)

    def clear_database(self):
        """
        清空当前数据库的所有节点和关系（危险操作，慎用）。
        """
        self.run("MATCH (n) DETACH DELETE n")
        logger.warning("已清空数据库中的所有节点和关系")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    with Neo4jClient() as client:
        # 增
        client.create_node("Person", {"name": "Alice", "age": 30})
        client.create_node("Person", {"name": "Bob", "age": 25})
        print("✅ 创建节点完成")

        # 查
        alice = client.get_node("Person", {"name": "Alice"})
        print(f"🔍 查询 Alice: {alice}")

        all_persons = client.get_all_nodes("Person")
        print(f"🔍 所有 Person 节点: {len(all_persons)} 条")

        # 改
        client.update_node("Person", {"name": "Alice"}, {"age": 31, "city": "Shanghai"})
        alice_updated = client.get_node("Person", {"name": "Alice"})
        print(f"✏️ 更新后 Alice: {alice_updated}")

        # 删
        client.delete_node("Person", {"name": "Bob"})
        remaining = client.get_all_nodes("Person")
        print(f"🗑️ 删除 Bob 后剩余: {len(remaining)} 条")
