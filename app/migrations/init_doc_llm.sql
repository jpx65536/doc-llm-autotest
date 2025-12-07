-- 建库
CREATE DATABASE IF NOT EXISTS doc_llm DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;

USE doc_llm;

-- 建表
CREATE TABLE IF NOT EXISTS task_doc_llm (
    task_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID，自增主键',
    task_name   VARCHAR(255)    NOT NULL COMMENT '任务名称，可重复',
    create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    doc         TEXT            NOT NULL COMMENT '文档内容或文档路径，最长65535字节',
    status      ENUM('pending','success','failed')
                                NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    result      JSON            NULL COMMENT '执行结果，json 格式，pending 时为 NULL',

    PRIMARY KEY (task_id),
    KEY idx_status_ctime (status, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;