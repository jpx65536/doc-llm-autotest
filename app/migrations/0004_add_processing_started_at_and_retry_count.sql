USE doc_llm;

ALTER TABLE task_doc_llm
    ADD COLUMN processing_started_at DATETIME NULL COMMENT '任务开始处理的时间' AFTER status,
    ADD COLUMN retry_count INT NOT NULL DEFAULT 0 COMMENT '任务重试次数' AFTER processing_started_at;
