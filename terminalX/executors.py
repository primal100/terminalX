from concurrent.futures import ThreadPoolExecutor


executor = ThreadPoolExecutor()


def shutdown():
    executor.shutdown()
