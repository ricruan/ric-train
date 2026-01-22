import logging

logger = logging.getLogger(__name__)

class WorkFlowBaseException(Exception):
    def __init__(self, message, *args):
        super().__init__(message, *args)
        logger.error(f"工作流异常: {message}")