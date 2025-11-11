import threading
import time
import queue
import concurrent.futures
import random
from typing import Any, Optional


class MultiThreadTaskProcessor:
    """
    多线程任务处理
    存在一个主线程池，支持指定数量的最大工作线程
    主线程可以持续添加新的任务进入任务队列
    当指定时间段内没有新的任务需要处理时，自动销毁主线程池
    """
    def __init__(self, max_workers: int = 3, idle_timeout: float = 60.0):
        """
        初始化多线程任务处理器

        :param max_workers: 线程池最大工作线程数
        :param idle_timeout: 多久没有新任务（从 add_task 调用算起）就自动关闭线程池（秒）
        """
        self.task_queue = queue.Queue()
        self.max_workers = max_workers
        self.idle_timeout = idle_timeout

        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._consumer_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._last_task_submit_time = 0.0  # 上次 add_task 的时间
        self._lock = threading.Lock()

        # 启动监控线程（用于检测长时间无新任务）
        self._start_watchdog()

    def add_task(self, task_data: Any):
        """外部调用：添加一个任务到队列"""
        self.task_queue.put(task_data)
        self._last_task_submit_time = time.time()

        with self._lock:
            if self._executor is None or self._executor._shutdown:
                self._start_executor()

    def _start_executor(self):
        """启动线程池和消费者线程"""
        if self._executor is not None and not self._executor._shutdown:
            return

        self._shutdown_event.clear()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self._consumer_thread = threading.Thread(
            target=self._task_consumer_worker,
            daemon=True
        )
        self._consumer_thread.start()
        print("[FileTaskProcessor] 🟢 启动线程池和消费者线程")

    def _task_consumer_worker(self):
        """消费者线程：持续提交任务给线程池"""
        print("[消费者线程] 🟢 启动任务消费者，监听任务队列...")
        while not self._shutdown_event.is_set():
            try:
                task = self.task_queue.get(timeout=1.0)  # 短超时，快速响应 shutdown
                print(f"[消费者线程] 📥 获取任务: {task}")
                if self._executor and not self._executor._shutdown:
                    self._executor.submit(self._process_task, task)
            except queue.Empty:
                continue

    def _process_task(self, task_data: Any):
        """实际任务处理函数（可被子类重写）"""
        print(f"🔧 [线程池] 开始处理任务: {task_data}")
        time.sleep(random.uniform(1, 3))
        print(f"✅ [线程池] 完成任务: {task_data}")

    def _start_watchdog(self):
        """启动后台监控线程，检测长时间无新任务"""
        self._watchdog_thread = threading.Thread(target=self._watchdog_worker, daemon=True)
        self._watchdog_thread.start()

    def _watchdog_worker(self):
        """监控线程：每秒检查是否超时未收到新任务"""
        print(f"[Watchdog] 🕵️ 启动监控线程，空闲超时设为 {self.idle_timeout} 秒")
        while not self._shutdown_event.is_set():
            time.sleep(60.0)
            now = time.time()
            last_time = self._last_task_submit_time
            if last_time > 0 and (now - last_time) > self.idle_timeout:
                with self._lock:
                    # 再次确认：可能刚有新任务进来
                    if self._last_task_submit_time == last_time and self._executor and not self._executor._shutdown:
                        print(f"[Watchdog] ⏳ 超过 {self.idle_timeout} 秒无新任务，正在关闭线程池...")
                        self._shutdown_executor()

    def _shutdown_executor(self):
        """安全关闭线程池"""
        if self._executor and not self._executor._shutdown:
            # 先停止消费者线程
            self._shutdown_event.set()
            if self._consumer_thread and self._consumer_thread.is_alive():
                self._consumer_thread.join(timeout=2)

            # 关闭线程池（等待现有任务完成）
            self._executor.shutdown(wait=True)
            self._executor = None
            self._consumer_thread = None
            print("[FileTaskProcessor] 🔴 线程池已关闭")

    def shutdown(self, wait: bool = True):
        """手动关闭所有资源（程序退出时调用）"""
        self._shutdown_event.set()
        if self._watchdog_thread and self._watchdog_thread.is_alive() and wait:
            self._watchdog_thread.join(timeout=2)
        self._shutdown_executor()


# ======================
# 示例使用：模拟间歇性任务流
# ======================
def demo():
    processor = MultiThreadTaskProcessor(max_workers=3, idle_timeout=30.0)  # 30秒无新任务就关闭（演示方便）

    # 第一批任务
    for i in range(1, 40):
        processor.add_task({'id': i})
        time.sleep(0.5)

    print("\n[主线程] 💤 睡眠 35 秒，模拟长时间无新任务...\n")
    time.sleep(35)  # 超过 idle_timeout，线程池应自动关闭

    print("\n[主线程] ➕ 新任务来了！应自动重启线程池\n")
    processor.add_task({'id': 'new_batch_1'})
    processor.add_task({'id': 'new_batch_2'})

    time.sleep(10)
    processor.shutdown(wait=True)
    print("[主线程] 🔵 程序结束")


if __name__ == "__main__":
    demo()