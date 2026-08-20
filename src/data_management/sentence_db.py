from __future__ import annotations

import os
from typing import Optional
import sys, os
import time
import ipdb
from pathlib import Path
import functools

from dataclasses import dataclass
from sqlite3 import connect, Connection, Cursor
from util.util import get_basic_logger

_logger = get_basic_logger(__name__)


@dataclass(frozen=True)
class DBSentence:
    text: str
    file_path: str
    module: str
    sentence_type: str
    line: int


class SentenceDB:
    TABLE_NAME = "sentence"

    def __init__(self, connection: Connection, cursor: Cursor,
                 db_path: "Path | None" = None) -> None:
        self.__connection = connection
        self.__cursor = cursor
        self.__db_path = db_path
        self.__owner_pid = os.getpid()
        self.__found_cache: dict[DBSentence, int] = {}
        self.__contains_cache: dict[int, bool] = {}

    # ── ★ fork 안전성 ────────────────────────────────────────────────────────
    #  SQLite 연결은 **fork() 를 넘어 공유하면 안 된다**(공식 문서 명시). 그런데
    #  `SentenceDB.load` 는 연결 하나를 만들고, 그게 dataloader 워커가 fork 되기
    #  **전**에 생성된다. 워커 12개가 커서 하나를 함께 쓰면 조회가 **직렬화**되고
    #  락 경합이 난다.
    #
    #  실측: 같은 코드가 단일 프로세스 벤치마크로는 예제당 0.38초인데, 워커 12개인
    #  실제 학습에서는 step(32예제) 당 80초였다 — 병렬이 전혀 안 되고 있었다.
    #
    #  고치는 법은 간단하다. **프로세스가 바뀌면 자기 연결을 새로 연다.**
    #  쿼리도 결과도 그대로이고, 달라지는 것은 어느 연결로 읽느냐뿐이다.
    def __ensure_own_conn(self) -> None:
        pid = os.getpid()
        if pid == self.__owner_pid:
            return
        if self.__db_path is None:
            # 경로를 모르면 재연결할 수 없다 — 기존 동작을 유지한다(안전한 쪽).
            self.__owner_pid = pid
            return
        con = connect(self.__db_path)
        self.__connection = con
        self.__cursor = con.cursor()
        self.__owner_pid = pid
        # 캐시는 프로세스마다 새로 채운다(값은 같지만 메모리를 공유하지 않게)
        self.__found_cache = {}
        self.__contains_cache = {}

    @property
    def connection(self) -> Connection:
        self.__ensure_own_conn()
        return self.__connection

    @property
    def cursor(self) -> Cursor:
        self.__ensure_own_conn()
        return self.__cursor

    def contains_id(self, id: int) -> bool:
        if id in self.__contains_cache:
            return self.__contains_cache[id]
        result = self.cursor.execute(
            f"""
            SELECT * FROM {self.TABLE_NAME} WHERE id={id}
                            """
        ).fetchall()
        if 0 == len(result):
            return False
        else:
            self.__contains_cache[id] = True
            return True

    def find_sentence(self, sentence: DBSentence) -> Optional[int]:
        if sentence in self.__found_cache:
            return self.__found_cache[sentence]

        result = self.cursor.execute(
            f"""
            SELECT id FROM {self.TABLE_NAME}
            WHERE
            text=? AND
            file_path=? AND
            module=? AND
            sentence_type=? AND
            line=?""",
            (
                sentence.text,
                sentence.file_path,
                sentence.module,
                sentence.sentence_type,
                sentence.line,
            ),
        ).fetchall()
        if 0 == len(result):
            return None
        if 1 == len(result):
            (resulting_id,) = result[0]
            self.__found_cache[sentence] = resulting_id
            return resulting_id
        raise ValueError(f"DB has more than one instance of {sentence}")

    @functools.cache
    def insert_sentence(self, sentence: DBSentence) -> int:
        found_id = self.find_sentence(sentence)
        if found_id is not None:
            return found_id

        result = self.cursor.execute(
            f"""
            INSERT INTO {self.TABLE_NAME}  (text, file_path, module, sentence_type, line) VALUES
            (?, ?, ?, ?, ?)
            RETURNING id""",
            (
                sentence.text,
                sentence.file_path,
                sentence.module,
                sentence.sentence_type,
                sentence.line,
            ),
        ).fetchall()
        self.connection.commit()

        if len(result) != 1:
            raise ValueError(
                f"Something went wrong in query. Got {len(result)} after insert."
            )
        (resulting_id,) = result[0]
        return resulting_id

    def size(self) -> int:
        result = self.cursor.execute(
            f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
                            """
        ).fetchall()
        if len(result) != 1:
            raise ValueError("Problem executing size query.")
        (count,) = result[0]
        return count

    @functools.cache
    def retrieve(self, id: int) -> DBSentence:
        result = self.cursor.execute(
            f"""
            SELECT * FROM {self.TABLE_NAME} WHERE id=?
                            """,
            (id,),
        ).fetchall()
        if len(result) != 1:
            raise ValueError(
                f"Expected single result from sentence db. Got {len(result)}"
            )
        _, text, file_path, module, sentence_type, line = result[0]
        return DBSentence(text, file_path, module, sentence_type, line)

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.cursor.close()
        self.connection.close()

    @classmethod
    def load(cls, db_path: Path) -> SentenceDB:
        if not db_path.exists():
            raise ValueError(f"Database {db_path} does not exis does not exist.")
        name = db_path.name
        fast_db_path = Path("/tmp") / name
        if fast_db_path.exists():
            _logger.debug(f"Using local sentence db at {fast_db_path}")
            db_path = fast_db_path
        else:
            _logger.debug(f"Not using local db. {fast_db_path} does not exist.")

        con = connect(
            db_path,
        )
        cur = con.cursor()
        # ★ 경로를 함께 넘긴다 — 워커에서 자기 연결을 새로 열 때 필요하다.
        return cls(con, cur, db_path)

    @classmethod
    def create(cls, db_path: Path) -> SentenceDB:
        if db_path.exists():
            raise ValueError(f"DB {db_path} already exists")
        con = connect(db_path)
        cur = con.cursor()
        cur.execute(
            f"""
            CREATE TABLE {cls.TABLE_NAME} (
                id INTEGER PRIMARY KEY, 
                text TEXT, 
                file_path TEXT, 
                module TEXT, 
                sentence_type TEXT, 
                line INTEGER)
        """
        )
        cur.execute(
            f"""
            CREATE INDEX text_index ON {cls.TABLE_NAME}(text)
        """
        )
        return cls(con, cur)
