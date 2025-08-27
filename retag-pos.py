"""
Commented by: Seungjae, Lee
Date: 2025-08-27 (Wed)
"""


import sqlite3
import shutil
from datetime import datetime
import spacy

# ========== 설정 ==========
DB_PATH = "word_cefr_minified.db"
BACKUP_PATH = f"{DB_PATH}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"

# Penn Treebank 태그 설명 사전
POS_DESCRIPTIONS = {
    'CC': 'Coordinating conjunction',
    'CD': 'Cardinal number',
    'DT': 'Determiner',
    'EX': 'Existential there',
    'FW': 'Foreign word',
    'IN': 'Preposition or subordinating conjunction',
    'JJ': 'Adjective',
    'JJR': 'Adjective, comparative',
    'JJS': 'Adjective, superlative',
    'LS': 'List item marker',
    'MD': 'Modal',
    'NN': 'Noun, singular or mass',
    'NNS': 'Noun, plural',
    'NNP': 'Proper noun, singular',
    'NNPS': 'Proper noun, plural',
    'PDT': 'Predeterminer',
    'POS': 'Possessive ending',
    'PRP': 'Personal pronoun',
    'PRP$': 'Possessive pronoun',
    'RB': 'Adverb',
    'RBR': 'Adverb, comparative',
    'RBS': 'Adverb, superlative',
    'RP': 'Particle',
    'SYM': 'Symbol',
    'TO': 'To',
    'UH': 'Interjection',
    'VB': 'Verb, base form',
    'VBD': 'Verb, past tense',
    'VBG': 'Verb, gerund or present participle',
    'VBN': 'Verb, past participle',
    'VBP': 'Verb, non-3rd person singular present',
    'VBZ': 'Verb, 3rd person singular present',
    'WDT': 'Wh-determiner',
    'WP': 'Wh-pronoun',
    'WP$': 'Possessive wh-pronoun',
    'WRB': 'Wh-adverb',
}

# ========== 준비 ==========
# 0) DB 백업
shutil.copy2(DB_PATH, BACKUP_PATH)
print(f"[backup] DB backed up to {BACKUP_PATH}")

# 1) spaCy 로드 (tagger만 사용)
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])

def guess_ptb_tag(word: str) -> str:
    """단어 하나를 spaCy로 태깅"""
    doc = nlp(word)
    if not doc or not doc[0]:
        return "NN"
    return doc[0].tag_

# ========== DB 연결 ==========
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 2) pos_tags 캐시
cur.execute("SELECT tag_id, tag FROM pos_tags")
tag_rows = cur.fetchall()
tag2id = {t: i for (i, t) in tag_rows}
id2tag = {i: t for (i, t) in tag_rows}

def ensure_tag_id(tag: str) -> int:
    """pos_tags에 없으면 (tag, description) 함께 INSERT"""
    if tag in tag2id:
        return tag2id[tag]
    desc = POS_DESCRIPTIONS.get(tag, "Other/Unknown")
    try:
        cur.execute(
            "INSERT INTO pos_tags(tag, description) VALUES (?, ?)",
            (tag, desc)
        )
        conn.commit()
        new_id = cur.lastrowid
        tag2id[tag] = new_id
        id2tag[new_id] = tag
        return new_id
    except sqlite3.IntegrityError:
        cur.execute("SELECT tag_id FROM pos_tags WHERE tag = ?", (tag,))
        row = cur.fetchone()
        if row:
            tag2id[tag] = row[0]
            id2tag[row[0]] = tag
            return row[0]
        raise

# 3) word_pos에 새 컬럼 추가 (이미 있으면 무시)
try:
    cur.execute("ALTER TABLE word_pos ADD COLUMN pos_tag_id_new INTEGER")
    conn.commit()
    print("[schema] Added column word_pos.pos_tag_id_new")
except sqlite3.OperationalError:
    print("[schema] Column word_pos.pos_tag_id_new already exists")

# 4) words 테이블 읽기
cur.execute("SELECT word_id, word FROM words")
wordid2word = dict(cur.fetchall())

# 5) word_pos 전체 행에 대해 재태깅
cur.execute("SELECT rowid, word_id FROM word_pos")
rows = cur.fetchall()

updates = []
for rowid, word_id in rows:
    word = wordid2word.get(word_id, "")
    if not word:
        continue
    new_tag = guess_ptb_tag(word)
    new_tag_id = ensure_tag_id(new_tag)
    updates.append((new_tag_id, rowid))

cur.executemany(
    "UPDATE word_pos SET pos_tag_id_new = ? WHERE rowid = ?",
    updates
)
conn.commit()
print(f"[retag] Updated {len(updates)} rows with new POS tags (pos_tag_id_new)")

# 6) 검수: 기존 vs 새 태그 불일치 샘플
cur.execute("""
SELECT w.word, oldt.tag AS old_tag, newt.tag AS new_tag, COUNT(*) AS cnt
FROM word_pos AS wp
JOIN words AS w ON w.word_id = wp.word_id
LEFT JOIN pos_tags AS oldt ON oldt.tag_id = wp.pos_tag_id
LEFT JOIN pos_tags AS newt ON newt.tag_id = wp.pos_tag_id_new
WHERE wp.pos_tag_id IS NOT newt.tag_id
GROUP BY w.word, old_tag, new_tag
ORDER BY cnt DESC
LIMIT 30
""")
diff_samples = cur.fetchall()
print("[diff] sample mismatches (word, old_tag, new_tag, cnt):")
for r in diff_samples:
    print("   ", r)

# 7) (선택) 실제 교체 (검수 후 주석 해제)
# cur.execute("UPDATE word_pos SET pos_tag_id = pos_tag_id_new WHERE pos_tag_id_new IS NOT NULL")
# conn.commit()
# print("[swap] pos_tag_id <- pos_tag_id_new completed")

conn.close()
print("[done]")
