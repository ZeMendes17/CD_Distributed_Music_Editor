broker_url = 'amqp://guest:guest@localhost:5672//'
result_backend = 'rpc://'
worker_concurrency = 1
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1
task_acks_late = True
consumer_timeout = 3600 * 5 # 5 hours