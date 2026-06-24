from Base.Ai.agents import NL2CypherAgent
from Base.Ai.middlewares import LoggingMiddleware, MetricsMiddleware, SafetyMiddleware
from Base.Client.neo4jClient import Neo4jClient

agent = NL2CypherAgent(client=Neo4jClient(), middlewares=[LoggingMiddleware(),
                                                          MetricsMiddleware(),
                                                          SafetyMiddleware(), ])





if __name__ == '__main__':
    agent.run("张三和李四都是王五的好闺蜜")