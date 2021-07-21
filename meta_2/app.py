import datetime
import logging
import threading

from datetime import time

import psycopg2
import psycopg2.extensions
import os
import atexit

from flask import Flask, jsonify, request
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route("/get_auction/", methods=['GET'], strict_slashes=True)
def get_auction():
    ##logger.info("###              DEMO: GET /departments              ###");

    payload = request.get_json()
    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    statement = """SELECT auctionid, auction.title, description.text FROM auction, description
                WHERE auction.auctionid = description.auction_auctionid
                ORDER BY descriptiondate DESC LIMIT 1"""

    cur.execute(statement)
    rows = cur.fetchall()

    payload = []
    ##logger.debug("---- auction  ----")
    for row in rows:
        ##logger.debug(row)
        content = {'auction.auctionid': row[0], 'auction.title': row[1]}
        payload.append(content)  # appending to the payload to be returned

    conn.close()
    return jsonify(payload)


@app.route("/post_auction/", methods=['POST'])
def add_auction():
    ##logger.info("###              DEMO: POST /action              ###")
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    if "minimumprice" not in payload:
        return "We need a minimum price"
    elif "begindate" not in payload:
        return "We need a begin date"
    elif "enddate" not in payload:
        return "We need a end date"
    elif "title" not in payload:
        return "We need a title"
    elif "description" not in payload:
        return "Your product needs a description"



    conn = db_connection()
    cur = conn.cursor()

    date = datetime.datetime.now()


    cur.execute("SELECT uuid_generate_v4();")
    auctionID = cur.fetchone()[0]


    statement_auction = """
                          INSERT INTO auction (auctionid, minimumprice, begindate, enddate, title, canceled, person_userid, admin_person_userid)
                          VALUES ( %s,  %s ,  %s  ,  %s  ,  %s  , %s , %s , %s )
                          """

    values_auction = (auctionID, payload["minimumprice"], payload["begindate"], payload["enddate"], payload["title"],
              'False', payload["person_userid"], payload["admin_person_userid"])

    cur.execute("SELECT uuid_generate_v4();")
    descID = cur.fetchone()[0]

    statement_desc = """
                    INSERT INTO description (descriptionid,auction_auctionid,descriptiondate,text)
                    VALUES (   %s ,  %s  ,  %s  ,  %s  )
    """

    values_desc = (descID, auctionID, date, payload["description"])


    cur.execute("SELECT uuid_generate_v4();")
    unitID = cur.fetchone()[0]

    statement_unit = """
                    INSERT INTO unit (unitid,description_unit,person_userid,auction_auctionid)
                    VALUES (   %s ,  %s  ,  %s  ,  %s  )
    """

    values_unit = (unitID, payload["description_unit"], payload["person_userid"],auctionID)


    update_statement = '''
                        UPDATE auction SET description_descriptionid = %s 
                        WHERE auctionid = %s;
                    '''

    update_values = (descID, auctionID)

    #update person created auctions count
    get_count = """
                SELECT count(*) FROM auction
                WHERE auction.person_userid = %s AND auction.admin_person_userid = %s
    """

    userid = (payload["person_userid"],payload["person_userid"])

    cur.execute(get_count, userid)

    count = cur.fetchone()[0]
    count+=1


    update_count = """
                UPDATE person
                SET createdauctions = %s
                WHERE userid = %s                
    """

    values_update = (count, userid[0])

    try:
        #add action
        cur.execute(statement_auction, values_auction)
        cur.execute("commit")
        #add description
        cur.execute(statement_desc, values_desc)
        cur.execute("commit")
        #add unity
        cur.execute(statement_unit, values_unit)
        cur.execute("commit")
        #update auction with last description ID
        cur.execute(update_statement, update_values)
        cur.execute("commit")
        #update createdauctions count in person
        cur.execute(update_count, values_update)
        cur.execute("commit")

        result = 'Inserted! auctionID = ' + auctionID
    except (Exception, psycopg2.DatabaseError) as error:
        ##logger.error(error)
        print(error)
        result = 'Failed!'
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)


@app.route("/dbproj/user", methods=['POST'])
def register():

    payload = request.get_json()

    if "username" not in payload:
        return "We need a username, password and email"
    elif "password" not in payload:
        return "We need a password"
    elif "email" not in payload:
        return "We need your email"

    conn = db_connection()
    cur = conn.cursor()

    json_req = request.json
    username = json_req['username']
    password = json_req['password']
    email = json_req['email']
    admin = json_req['admin']
    createdAuctions = 0
    wonAuctions = 0
    cur.execute("SELECT uuid_generate_v4();")
    userID = cur.fetchone()[0]

    #logger.warning("userID value = " + str(userID))
    #logger.info("userID value = " + str(userID))

    statement = '''
                INSERT INTO person(userid, username, password, email, createdauctions, wonauctions)
                VALUES(%s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s)
                '''

    values = (userID, payload["username"], payload["password"], payload["email"], createdAuctions, wonAuctions)

    if payload['admin'] == 'True':
        cur.execute('''
                    SELECT person.userid FROM person WHERE person.username = %s AND person.password = crypt(%s, person.password)
                    ''',
                    (payload['username'], payload['password'])
                    )

        user_uuid = cur.fetchone()[0]
        statement = """
                    INSERT INTO admin(person_userid)
                    VALUES(%s)
                    """
        values = (user_uuid,)

        try:
            cur.execute(statement, values)
            conn.commit()
            result = 'Inserted an admin with userID = ' + str(user_uuid) + "!!"
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
            #logger.error(error)
            #logger.warning(error)
            result = "Failed to insert into admin"
        finally:
            if conn is not None:
                conn.close()
        return jsonify(result)

    try:
        cur.execute(statement, values)
        conn.commit()
        response = 'Inserted user with uuid --> ' + userID + '.'
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
        #logger.error(error)
        #logger.warning(error)
        response = 'Failed to insert :('
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


@app.route("/dbproj/user", methods=['PUT'])
def login():

    payload = request.get_json()

    if "username" not in payload:
        return "Please insert your username."
    elif "password" not in payload:
        return "Please insert your password."

    conn = db_connection()
    cur = conn.cursor()


    statement = """
                SELECT userid FROM person WHERE username = %s AND password = crypt(%s, password);
                """

    values = (payload['username'], payload['password'])

    try:
        cur.execute(statement, values)
        value = 0
        found_user = cur.fetchone()
        if(found_user != None):
            user_uuid = found_user[0]
            value = 1
            print("Found the user.")
        if value > 0:
            cur.execute("SELECT uuid_generate_v4();")
            token = cur.fetchone()[0]
            statement = '''
                        UPDATE person SET access_token = %s WHERE userid = %s;
                        '''
            values = (token, user_uuid)
            cur.execute(statement, values)
            conn.commit()
            result = token
        else:
            result = "User credentials don't match."
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
        result = "Error in SQL instruction execution."
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)


@app.route("/search_auction/", methods=['GET'])
def search_auction():

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()


    #create random uuid to be compared in the db
    cur.execute("SELECT uuid_generate_v4();")
    unitID = cur.fetchone()[0]
    description = "0"

    if "unitid" in payload:
        unitID = payload["unitid"]
    elif "description_unit" in payload:
        description = payload["description_unit"]
    else:
        return jsonify("We need a unitID or a description")



    statement = """SELECT auction.auctionid, description.text, unit.unitid ,unit.description_unit FROM auction, description, unit
                    WHERE (unitid = %s AND description.descriptionid = auction.description_descriptionid AND auction.auctionid = unit.auction_auctionid )
                    OR (description_unit = %s AND description.descriptionid = auction.description_descriptionid  AND auction.auctionid = unit.auction_auctionid)
                    ORDER BY descriptiondate DESC LIMIT 1
    """

    values = (unitID,description)

    cur.execute(statement,values)
    # cur.execute(statement1,(values,))
    rows = cur.fetchall()

    payload = []
    ##logger.debug("---- auction  ----")
    for row in rows:
        ##logger.debug(row)
        content = {'auctionid': row[0], 'auction_description': str(row[1]), 'unit_id': row[2], 'unit_description': str(row[3])}
        payload.append(content)  # appending to the payload to be returned

    conn.close()
    return jsonify(payload)

@app.route("/get_description/", methods=['GET'], strict_slashes=True)
def get_description():

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned")

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM description")
    rows = cur.fetchall()

    payload = []

    for row in rows:

        content = {'auction number': row[3], 'description': row[2], 'description.descriptiondate': str(row[1])}
        payload.append(content) # appending to the payload to be returned

    conn.close()
    return jsonify(payload)


@app.route("/dbproj/leilao", methods=['PUT'])
def update_auction():
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    if "auctionid" not in payload:
        result = 'We need a auctionID'

    #check if auctionid is not canceled
    cur.execute("SELECT count(*) from auction WHERE canceled = false AND auctionid=%s", (payload["auctionid"],))

    active = int(cur.fetchone()[0])
    if active == 0:
        return 'Auction is CANCELED'


    if "title" not in payload or "description" not in payload:
        result = 'We need a title or a description'

    if "title" in payload:
        statement_title = """UPDATE auction SET title = %s 
                            WHERE auction.auctionid = %s;
        """
        values_title = (payload["title"],payload["auctionid"])
        try:
            cur.execute(statement_title, values_title)
            conn.commit()
            result = 'Title updated'
        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
            # logger.error(error)
            # logger.warning(error)
            result = 'Failed to update :('
        finally:
            if conn is not None:
                conn.close()

    if "description" in payload:
        date = datetime.datetime.now()

        cur.execute("SELECT uuid_generate_v4();")
        descID = cur.fetchone()[0]

        statement_desc = """
                            INSERT INTO description (descriptionid,auction_auctionid,descriptiondate,text)
                            VALUES (   %s ,  %s  ,  %s  ,  %s  )
            """

        values_desc = (descID, payload["auctionid"], date, payload["description"])

        try:
            cur.execute(statement_desc, values_desc)
            conn.commit()
            result = 'Description updated!!'

            #if description is updated we have to change auction descriptionid
            statement_auction = """
                                UPDATE auction
                                SET description_descriptionid = %s
                                WHERE auction.auctionid = %s
            """

            values_auction = (descID, payload["auctionid"])
            cur.execute(statement_auction, values_auction)
            conn.commit()

            result += ' (descriptionid updated in auction too!!)'

        except(Exception, psycopg2.DatabaseError) as error:
            print(error)
            # logger.error(error)
            # logger.warning(error)
            result = "Failed to update description"
        finally:
            if conn is not None:
                conn.close()



    return jsonify(result)

@app.route("/post_mesg/", methods=['POST'])
def add_mesg():
    ##logger.info("###              DEMO: POST /bid              ###")
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    if "auction_auctionid" not in payload:
        return jsonify("We need a auctionID")

    # check if auctionid is not canceled
    cur.execute("SELECT count(*) from auction WHERE canceled = false AND auctionid=%s", (payload["auction_auctionid"],))

    active = int(cur.fetchone()[0])
    if active == 0:
        return jsonify('Auction is CANCELED')

    if "text" not in payload:
        return jsonify('We need a description')

    if "person_userid" not in payload:
        return jsonify('We need your personID')

    cur.execute("SELECT uuid_generate_v4();")
    messageID = cur.fetchone()[0]

    statement = """
                  INSERT INTO message (messageid, text, person_userid, auction_auctionid)
                          VALUES ( %s,  %s ,  %s, %s )"""

    values = (messageID, payload["text"], payload["person_userid"], payload["auction_auctionid"])

    try:
        cur.execute(statement, values)
        conn.commit()
        result = 'Inserted messageID = ' + str(messageID) + "!!"
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
        #logger.error(error)
        #logger.warning(error)
        result = 'Failed to insert :('
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)

@app.route("/dbproj/mural/<auctionid>", methods=['GET'])
def get_mural(auctionid):

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    statement = """
                SELECT person.username, message.text FROM person, message
                WHERE person.userid = person_userid AND message.auction_auctionid = %s
    """

    cur.execute(statement,(auctionid,))
    rows = cur.fetchall()

    payload = []

    for row in rows:
        content = {'username': str(row[0]), 'message': str(row[1])}
        payload.append(content)  # appending to the payload to be returned

    conn.close()
    return jsonify(payload)

@app.route("/dbproj/cancel/<auctionid>", methods=['POST'])
def cancel_auction(auctionid):
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to log in first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    if not check_if_admin(payload):
        return jsonify("You're not admin.")

    conn = db_connection()
    cur = conn.cursor()

    statement = """
                UPDATE auction
                SET canceled = true
                WHERE auctionid = %s
    """

    try:
        cur.execute(statement, (auctionid,))
        conn.commit()
        result = 'Auction ' + auctionid + ' is canceled!! (#AuctionIsOverParty)'
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
        #logger.error(error)
        #logger.warning(error)
        result = 'Failed to cancel the auction'
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)


@app.route("/dbproj/auctions", methods=['GET'])
def get_auctions():

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to login first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    statement = """
                SELECT auction.auctionid, description.text FROM auction, description
                WHERE (description.descriptionid = auction.description_descriptionid AND auction.canceled = false )
    """

    cur.execute(statement)
    rows = cur.fetchall()

    payload = []

    for row in rows:
        content = {'auctionid': row[0], 'description': str(row[1])}
        payload.append(content)  # appending to the payload to be returned

    conn.close()
    return jsonify(payload)

@app.route("/dbproj/bid/<auctionId>/<bid>", methods=['POST'])
def add_bid(auctionId,bid):

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to login first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    cur.execute("SELECT uuid_generate_v4();")
    bidID = cur.fetchone()[0]

    date = datetime.datetime.now()

    #check if auction is active
    cur.execute("SELECT count(*) from auction WHERE canceled = false AND auctionid=%s",(auctionId,))

    active = int(cur.fetchone()[0])
    if active == 0:
        return 'Auction is CANCELED'


    statement_auction = """
                        SELECT count(*) from auction
                        WHERE auctionid= %s AND minimumprice < %s
    """


    values_auction = (auctionId,bid)
    cur.execute(statement_auction, values_auction)


    auction = int(cur.fetchone()[0])
    if auction == 0:
        return 'you are pooooooor (your bid is lower than the minimum price)'


    #check if bid is ok
    statement = """
                SELECT count(*) from bid
                WHERE  bid.auction_auctionid= %s AND bidvalue > %s
    """
    values = (auctionId,bid)
    cur.execute(statement, values)

    bid_value = int(cur.fetchone()[0])
    if bid_value >= 1:
        return 'Your bid is too low lol'


    statement_bid = """
                  INSERT INTO bid (bidid, bidvalue, biddate, person_userid, auction_auctionid)
                          VALUES ( %s,  %s ,  %s, %s ,  %s)"""

    values_bid = (bidID, bid, date, payload["person_userid"], auctionId)

    try:
        cur.execute(statement_bid, values_bid)
        conn.commit()
        result = 'Inserted bidID = ' + str(bidID) + "!!"
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
        #logger.error(error)
        #logger.warning(error)
        result = 'Failed to insert :('
    finally:
        if conn is not None:
            conn.close()

    return jsonify(result)

@app.route("/dbproj/stats/", methods=['GET'])
def get_stats():
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to login first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")
    
    if not check_if_admin(payload):
        return jsonify("You're not admin")

    conn = db_connection()
    cur = conn.cursor()


    payload = []

    aux = {'top 10 users with most created auctions': [],'top 10 users with most won auctions': [],'total number of auctions in the last 10 days': []}

    #top 10 useres with most created auctions

    statement = """
                    SELECT userid, username ,createdauctions FROM person
                    ORDER BY createdauctions DESC LIMIT 10
        """

    cur.execute(statement)
    rows = cur.fetchall()

    for row in rows:
        content = {'userid': str(row[0]), 'username': str(row[1]) ,'created auctions': int(row[2])}
        aux['top 10 users with most created auctions'].append(content)


    #top 10 users with most won auctions
    statement = """
                        SELECT userid, username ,wonauctions FROM person
                        ORDER BY wonauctions DESC LIMIT 10
            """

    cur.execute(statement)
    rows = cur.fetchall()

    for row in rows:
        content = {'userid': str(row[0]), 'username': str(row[1]), 'won auctions': int(row[2])}
        aux['top 10 users with most won auctions'].append(content)

    date = str(datetime.datetime.now() - datetime.timedelta(10))
    print(date)

    # total number of auctions in the last 10 days
    statement = """
                            SELECT count(*) FROM auction
                            WHERE auction.begindate > %s
                            GROUP BY auction.begindate
                            ORDER BY auction.begindate DESC LIMIT 10
                """

    cur.execute(statement,(date,))
    count = cur.fetchall()[0]
    aux['total number of auctions in the last 10 days'].append(count)

    payload.append(aux)  # appending to the payload to be returned

    conn.close()
    return jsonify(payload)



@app.route("/dbproj/auction/details/<auctionid>", methods=['GET'])
def get_auction_details(auctionid):

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to login first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    #get unit description / get auction end date
    statement = """
                SELECT unit.description_unit, auction.enddate  FROM auction, unit
                WHERE (unit.auction_auctionid = %s AND auction.auctionid = %s)
    """

    cur.execute(statement,(auctionid,auctionid))
    row = cur.fetchall()


    aux = {'auctionid': auctionid, 'end date': str(row[0][1]), 'messages': [], 'bids':[]}

    #get mural
    statement = """
                    SELECT person.username, message.text  FROM message, person
                    WHERE message.auction_auctionid = %s AND person.userid = message.person_userid
        """

    cur.execute(statement, (auctionid,))
    rows = cur.fetchall()

    for row in rows:
        content = {'user': row[0], 'message': str(row[1])}
        aux['messages'].append(content)  # appending to the payload to be returned

    #get bids history
    statement = """
                        SELECT person.username, bid.bidvalue, bid.biddate  FROM bid, person
                        WHERE bid.auction_auctionid = %s AND person.userid = bid.person_userid
            """

    cur.execute(statement, (auctionid,))
    rows = cur.fetchall()

    for row in rows:
        content = {'user': row[0], 'bid value': str(row[1]), 'bid date': str(row[2])}
        aux['bids'].append(content)  # appending to the payload to be returned



    conn.close()
    return jsonify(aux)

@app.route("/dbproj/active/<userid>", methods=['GET'])
def active_auctions(userid):
    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify("You need to login first.")
    elif check_token(payload) == 2:
        return jsonify("You are banned.")

    conn = db_connection()
    cur = conn.cursor()

    #get created auctions
    statement = """
                SELECT DISTINCT auction.title, description.text ,auction.begindate, auction.enddate, auction.person_userid FROM auction, description
                WHERE auction.person_userid = %s AND auction.description_descriptionid = description.descriptionid
    """

    cur.execute(statement, (userid,))
    rows = cur.fetchall()

    payload={'created':[],'bided':[]}

    for row in rows:
        content = {'title': row[0], 'begin date': str(row[1]), 'end date': str(row[2]),'creator': str(row[3])}
        payload['created'].append(content)  # appending to the payload to be returned


    #get bids activity
    statement = """
                SELECT DISTINCT auction.title, description.text ,auction.begindate, auction.enddate, auction.person_userid
                FROM auction, description, bid
                WHERE bid.person_userid = %s AND bid.auction_auctionid = auction.auctionid
                AND auction.description_descriptionid = description.descriptionid
    """

    cur.execute(statement, (userid,))
    rows = cur.fetchall()


    for row in rows:
        content = {'title': row[0], 'begin date': str(row[1]), 'end date': str(row[2]), 'creator': str(row[3])}
        payload['bided'].append(content)  # appending to the payload to be returned


    return jsonify(payload)

@app.route('/dbproj/ban/<userid>', methods=['POST'])
def ban_user(userid):

    payload = request.get_json()

    if check_token(payload) == 0:
        return jsonify('You need to log in first.')

    if not check_if_admin(payload):
        return jsonify('You are not an admin.')

    conn = db_connection()
    cur = conn.cursor()

    cur.execute('''
                    SELECT count(*) FROM person WHERE person.userid = %(userid)s;
                ''', {'userid':userid}    
    )

    count = cur.fetchone

    if count is not None:
        cur.execute('''
                        UPDATE person SET banned = 'true' WHERE userid = %(userid)s;
                    ''', {'userid':userid} 
        )
        conn.commit()
        return jsonify('Banned user with uuid: ', userid)
    else:
        return jsonify('Coudln\'t find a user with that uuid.')


def db_connection():
    db = psycopg2.connect(user="postgres",
                          password="",
                          host="localhost",
                          port="5432",
                          database="project")
    return db

def check_if_admin(payload):

    conn = db_connection()
    cur = conn.cursor()

    if "admin_person_userid" in payload:
        cur.execute("SELECT count(*) FROM admin WHERE admin.person_userid = %(admin_person_userid)s;", {'admin_person_userid':payload['admin_person_userid']})
        count = cur.fetchone
        if count is not None:
            if conn is not None:
                conn.close()
            return True

    if conn is not None:
        conn.close()
    return False

def check_token(payload):

    conn = db_connection()
    cur = conn.cursor()

    if "token" in payload:
        if len(payload["token"]) == 36:
            cur.execute("SELECT banned, access_token FROM person WHERE access_token = %s;", (payload["token"],))
            validation = cur.fetchone()
            if validation is not None:
                if validation[0] == True:
                    return 2
                if conn is not None:
                    conn.close()
                return 1

    if conn is not None:
        conn.close()
    return 0

def time_thread(stop_event):
    with app.app_context():
        while not stop_event.is_set():

            lock.acquire()

            conn = db_connection()
            cur = conn.cursor()

            date = datetime.datetime.now()

            cur.execute('''
                            SELECT auction.auctionid FROM auction WHERE (%s > auction.enddate AND auction.canceled = 'false');
                        ''', (date,)
            )

            rows = cur.fetchall()

            print("Running to check whether auction ended or not.")

            for row in rows:
                cur.execute('''
                                UPDATE auction SET canceled = true WHERE auction.auctionid = %s;
                            ''', (row,)
                )
                conn.commit()
                print("Auction with uuid " + str(row[0]) + " has ended.")
                cur.execute('''
                                SELECT bid.person_userid, bid.bidvalue FROM bid WHERE bid.auction_auctionid = %s ORDER BY bid.bidvalue DESC;
                            ''', (row,)
                )
                
                fetch_result = cur.fetchone()
                
                if fetch_result is None:
                    error_message = "Auction with uuid " + row[0] + " ended without any bid."
                    print(error_message)
                    return jsonify(error_message)

                highest_bidder = fetch_result[0]
                max_bid = fetch_result[1]

                print('Highest bidder --> ', highest_bidder, '\nMax bid --> ', max_bid)

                cur.execute('''
                                UPDATE auction SET winner = %s WHERE auctionid = %s;
                            ''', (highest_bidder, row)
                )
                conn.commit()

                print("The winner of auction with uuid ", row[0],  " is the user with uuid ", highest_bidder, "!!")

            if conn is not None:
                conn.close()

            lock.release()
            
            stop_event.wait(60)

def thread_shutdown():
    thread_stop.set()
    thread.join()
    print("Time thread is shutdown.")

if __name__ == '__main__':
    # Set up the logging
    # logging.basicConfig(filename="logs/log_file.log", encoding='utf-8', level=logging.DEBUG)
    ##logger = logging.getLogger('logger')
    ##logger.setLevel(logging.DEBUG)

    # ch = logging.StreamHandler()
    # ch.setLevel(logging.DEBUG)

    ##logger.info("\n---------------------------------------------------------------\n" +
    #           "API v1.0 online: http://localhost:8080/departments/\n\n")
    
    thread_stop = threading.Event()
    thread = threading.Thread(target = time_thread, args=(thread_stop,))
    lock = threading.Lock()
    thread.start()

    atexit.register(thread_shutdown)

    app.run(host="127.0.0.1", debug=True, threaded=True, port=5000)
