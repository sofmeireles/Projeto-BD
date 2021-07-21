CREATE TABLE person(
	userid		 uuid DEFAULT uuid_generate_v4 (),
	username	 VARCHAR(512) UNIQUE,
	password	 VARCHAR(512),
	email		 VARCHAR(512) UNIQUE,
	access_token	 uuid,
	banned		 BOOL,
	createdauctions	 BIGINT,
	wonauctions	 BIGINT,
	admin_person_userid uuid,
	PRIMARY KEY(userid)
);

CREATE TABLE admin (
	person_userid uuid,
	PRIMARY KEY(person_userid)
);

CREATE TABLE auction (
	auctionid	 		uuid,
	minimumprice	 		FLOAT(8),
	begindate	 		TIMESTAMP,
	enddate		 		TIMESTAMP,
	title		 		VARCHAR(512),
	winner				uuid,
	description_descriptionid	uuid,
	canceled		 	BOOL,
	person_userid	 		uuid NOT NULL,
	admin_person_userid 		uuid NOT NULL,
	PRIMARY KEY(auctionid)
);

CREATE TABLE bid (
	bidid		 uuid,
	bidvalue	 FLOAT(8),
	biddate		 TIMESTAMP,
	auction_auctionid uuid NOT NULL,
	person_userid	 uuid NOT NULL,
	PRIMARY KEY(bidid)
);

CREATE TABLE unit (
	unitid		 uuid,
	description_unit VARCHAR(500),
	person_userid	 uuid NOT NULL,
	auction_auctionid uuid NOT NULL,
	PRIMARY KEY(unitid)
);

CREATE TABLE description (
	descriptionid	 uuid,
	descriptiondate	 TIMESTAMP,
	text		 VARCHAR(512),
	auction_auctionid uuid NOT NULL,
	PRIMARY KEY(descriptionid)
);

CREATE TABLE message (
	messageid	 uuid,
	text		 VARCHAR(512),
	auction_auctionid uuid NOT NULL,
	person_userid	 uuid NOT NULL,
	PRIMARY KEY(messageid)
);

ALTER TABLE person ADD CONSTRAINT person_fk1 FOREIGN KEY (admin_person_userid) REFERENCES admin(person_userid);
ALTER TABLE admin ADD CONSTRAINT admin_fk1 FOREIGN KEY (person_userid) REFERENCES person(userid);
ALTER TABLE auction ADD CONSTRAINT auction_fk1 FOREIGN KEY (person_userid) REFERENCES person(userid);
ALTER TABLE auction ADD CONSTRAINT auction_fk2 FOREIGN KEY (admin_person_userid) REFERENCES admin(person_userid);
ALTER TABLE auction ADD CONSTRAINT auction_fk3 FOREIGN KEY (description_descriptionid) REFERENCES description(descriptionid);
ALTER TABLE auction ADD CONSTRAINT auction_fk4 FOREIGN KEY (winner) REFERENCES person(userid);
ALTER TABLE bid ADD CONSTRAINT bid_fk1 FOREIGN KEY (auction_auctionid) REFERENCES auction(auctionid);
ALTER TABLE bid ADD CONSTRAINT bid_fk2 FOREIGN KEY (person_userid) REFERENCES person(userid);
ALTER TABLE unit ADD CONSTRAINT unit_fk1 FOREIGN KEY (person_userid) REFERENCES person(userid);
ALTER TABLE unit ADD CONSTRAINT unit_fk2 FOREIGN KEY (auction_auctionid) REFERENCES auction(auctionid);
ALTER TABLE description ADD CONSTRAINT description_fk1 FOREIGN KEY (auction_auctionid) REFERENCES auction(auctionid);
ALTER TABLE message ADD CONSTRAINT message_fk1 FOREIGN KEY (auction_auctionid) REFERENCES auction(auctionid);
ALTER TABLE message ADD CONSTRAINT message_fk2 FOREIGN KEY (person_userid) REFERENCES person(userid);
