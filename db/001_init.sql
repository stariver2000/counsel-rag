-- 초기 스키마 (설계문서 §6). DB는 knowledge/ md 파일에서 재구축 가능한 인덱스다.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
    id          serial PRIMARY KEY,
    slug        text UNIQUE NOT NULL,      -- 불투명 코드 (예: src-004)
    type        text NOT NULL,             -- youtube | public | book
    name        text NOT NULL,
    url         text,
    license     text,                      -- kogl-1 등
    trust_level int NOT NULL DEFAULT 3     -- 1=공공검증 2=전문가 3=일반
);

CREATE TABLE raw_items (
    id           serial PRIMARY KEY,
    source_id    int REFERENCES sources(id),
    external_id  text,
    title        text,
    file_path    text,
    collected_at timestamptz DEFAULT now()
);

CREATE TABLE documents (
    id         serial PRIMARY KEY,
    slug       text UNIQUE NOT NULL,
    title      text NOT NULL,
    targets    text[] NOT NULL,            -- boy | teen_male | common
    category   text NOT NULL,
    age_min    int,
    age_max    int,
    is_crisis  boolean NOT NULL DEFAULT false,
    reviewed   boolean NOT NULL DEFAULT false,  -- true만 검색에 노출
    file_path  text NOT NULL,
    version    int NOT NULL DEFAULT 1,
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE doc_sources (
    document_id int REFERENCES documents(id) ON DELETE CASCADE,
    raw_item_id int REFERENCES raw_items(id),
    PRIMARY KEY (document_id, raw_item_id)
);

CREATE TABLE chunks (
    id             serial PRIMARY KEY,
    document_id    int REFERENCES documents(id) ON DELETE CASCADE,
    seq            int NOT NULL,
    heading        text NOT NULL,
    text           text NOT NULL,
    embedding      vector(1024),            -- BGE-M3 dense
    sparse_weights jsonb                    -- BGE-M3 lexical weights {token_id: weight}
);

CREATE TABLE edges (
    id         serial PRIMARY KEY,
    src_doc_id int REFERENCES documents(id) ON DELETE CASCADE,
    dst_doc_id int REFERENCES documents(id) ON DELETE CASCADE,
    rel_type   text NOT NULL  -- related | prerequisite | escalates_to | differentiates_to
);

CREATE TABLE query_log (
    id            serial PRIMARY KEY,
    ts            timestamptz DEFAULT now(),
    target_filter text[],
    query_text    text,       -- 운영자 사용 단계: 원문 저장(코퍼스 구멍 발견용). 챗봇 공개 시 익명화 정책 전환
    top_chunks    jsonb,
    max_score     real
);

CREATE TABLE crisis_events (
    id               serial PRIMARY KEY,
    ts               timestamptz DEFAULT now(),
    trigger_category text NOT NULL   -- 사실+시각만. 대화 원문 저장 금지 (설계문서 §8)
);
