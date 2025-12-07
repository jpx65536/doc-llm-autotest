USE doc_llm;

ALTER TABLE task_doc_llm
    ADD COLUMN product VARCHAR(100) NULL COMMENT '产品名称' AFTER doc,
    ADD COLUMN feature VARCHAR(5000) NULL COMMENT '功能点' AFTER product;
