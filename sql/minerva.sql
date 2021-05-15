--create extension if not exists pg_trgm;

create table if not exists FFNLanguage (
	id smallserial primary key,
	name varchar(256) not null
);

create table if not exists FFNGenre (
	id smallserial primary key,
	name varchar(256) not null
);

create table if not exists FFNCategory (
	id smallserial primary key,
	stub varchar(64) not null unique,
	name varchar(64)
);

create table if not exists FFNFandom (
	id bigserial primary key,
	categoryId smallint references FFNCategory(id),
	stub varchar(1024) not null,
	name varchar(2048),
	remoteId bigint,
	hasCrossovers smallint not null default(0),

	unique(categoryId, stub),
	unique(categoryId, remoteId)
);

create table if not exists FFNCharacter (
	id bigint primary key,
	name varchar(256) not null,
	fandomId bigint references FFNFandom(id)
);

create table FFNUser (
	id bigint not null primary key,
	name varchar(256) not null,

	fetched oil_timestamp not null
);

create type FFNFicStatus as enum (
	'broken', 'abandoned', 'complete', 'ongoing',
	'removed', 'userRemoved', 'siteRemoved'
);

create table FFNFic (
	id bigint not null primary key,
	authorId bigint references FFNUser(id),

	fetched oil_timestamp not null,

	title varchar(256) not null,
	ageRating varchar(8) not null,

	chapterCount int not null,
	wordCount int not null,

	reviewCount int not null,
	favoriteCount int not null,
	followCount int not null,

	updated oil_timestamp not null,
	published oil_timestamp not null,

	status FFNFicStatus not null,

	description text,
	fandomId1 bigint references FFNFandom(id),
	fandomId2 bigint references FFNFandom(id)
);

create index FFNUserFic_idx on FFNFic (authorId, id);
create index FFNFicChapterCount_idx on FFNFic (chapterCount, id);

create table FFNFicGraveyard (
	id bigint not null primary key,
	code smallint not null,
	updated oil_timestamp not null
);

create table FFNUserGraveyard (
	id bigint not null primary key,
	code smallint not null,
	updated oil_timestamp not null
);

create table if not exists FFNCommunity (
	id bigint not null primary key,
	stub varchar not null,
	name varchar
);

create table if not exists FFNCommunityGraveyard (
	id bigint not null primary key,
	code smallint,
	updated oil_timestamp not null
);

create table if not exists FFNFandomDeltaResult (
	id bigserial primary key,
	fandomId bigint references FFNFandom(id),
	crossover smallint not null,
	created oil_timestamp not null,
	updated oil_timestamp not null,
	completed oil_timestamp,
	pages int,
	totalPages int,
	minTimestamp oil_timestamp,
	maxTimestamp oil_timestamp
);

create table if not exists FFNFicCrossoverDelayed (
	fid bigint not null primary key,
	stub varchar(1024) not null,
	name varchar(2048),
	fandomId1 bigint,
	fandomId2 bigint
);

create table if not exists FFNFicContent (
	fid bigint not null,
	cid int4 not null,

	wid bigint,

	content bytea,

	primary key(fid, cid)
	-- fetched oil_timestamp not null,
	-- updated oil_timestamp not null,
	-- published oil_timestamp not null,
) tablespace ffn_archive;

