USE doc_llm;

ALTER TABLE task_doc_llm
    MODIFY COLUMN status ENUM('pending','processing','success','failed')
    NOT NULL DEFAULT 'pending'
    COMMENT '任务状态';
