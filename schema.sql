CREATE TABLE words (
        word_id INTEGER PRIMARY KEY AUTOINCREMENT,
        word VARCHAR(25) UNIQUE NOT NULL,
        stem_word_id INTEGER,

        FOREIGN KEY (stem_word_id) REFERENCES words (word_id)
    );

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE pos_tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag VARCHAR(4) UNIQUE NOT NULL,
            description VARCHAR(40) NOT NULL
        );

CREATE TABLE word_pos (
        word_pos_id INTEGER PRIMARY KEY AUTOINCREMENT,
        word_id INTEGER NOT NULL,
        pos_tag_id INTEGER NOT NULL,
        lemma_word_id INTEGER,
        frequency_count INTEGER NOT NULL,
        level REAL NOT NULL,

        UNIQUE (word_id, pos_tag_id),
        FOREIGN KEY (word_id) REFERENCES words(word_id),
        FOREIGN KEY (pos_tag_id) REFERENCES pos_tags(tag_id),
        FOREIGN KEY (lemma_word_id) REFERENCES words(word_id)
    );

CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_title VARCHAR(255) NOT NULL
    );

CREATE TABLE word_categories (
        word_pos_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,

        UNIQUE (word_pos_id, category_id),
        FOREIGN KEY (word_pos_id) REFERENCES word_pos(word_pos_id),
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    );

CREATE INDEX idx_word ON words (word)
    ;

CREATE INDEX idx_pos_tag ON pos_tags (tag)
    ;

CREATE INDEX idx_word_pos_lemma ON word_pos (lemma_word_id)
    ;

CREATE INDEX idx_word_categories_word_pos_id ON word_categories (word_pos_id)
    ;

