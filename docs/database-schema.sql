-- Current SQLite structure; no data included.

CREATE TABLE books (
	id INTEGER NOT NULL,
	name VARCHAR NOT NULL,
	author VARCHAR NOT NULL,
	publish_date DATE NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE validation_acces (
	id INTEGER NOT NULL,
	validation_id VARCHAR(36) NOT NULL,
	occurred_at DATETIME NOT NULL,
	source_name TEXT NOT NULL,
	schema_path TEXT NOT NULL,
	record_type VARCHAR(30) NOT NULL,
	name TEXT,
	author TEXT,
	publish_date TEXT,
	person_id TEXT,
	full_name TEXT,
	birth_date TEXT,
	email1 TEXT,
	email2 TEXT,
	email3 TEXT,
	phone TEXT,
	university TEXT,
	course INTEGER,
	organization TEXT,
	position TEXT,
	PRIMARY KEY (id)
);

CREATE TABLE validation_errors (
	id INTEGER NOT NULL,
	validation_id VARCHAR(36) NOT NULL,
	occurred_at DATETIME NOT NULL,
	source_name TEXT NOT NULL,
	schema_path TEXT NOT NULL,
	category VARCHAR(50) NOT NULL,
	line INTEGER NOT NULL,
	"column" INTEGER NOT NULL,
	xpath TEXT NOT NULL,
	message TEXT NOT NULL,
	suggestion TEXT NOT NULL,
	PRIMARY KEY (id)
);

CREATE INDEX ix_validation_acces_occurred_at ON validation_acces (occurred_at);

CREATE INDEX ix_validation_acces_validation_id ON validation_acces (validation_id);

CREATE INDEX ix_validation_errors_occurred_at ON validation_errors (occurred_at);

CREATE INDEX ix_validation_errors_validation_id ON validation_errors (validation_id);
