import mysql.connector
import psycopg2

from roschat import constants


class DbAdmin():
    """ Connect to MySQL database """

    def __init__(self):
        self.conn = mysql.connector.connect(
            host=constants.HOST,
            database='shs_tss',
            user=constants.DB_USER,
            password=constants.DB_PASSWORD
        )
        self.cursor = self.conn.cursor()

    def select_person(self, username):
        self.cursor.execute("""SELECT Name, IdPerson FROM shs_tss.persons WHERE Name LIKE %s LIMIT 1""", (username+"%",))
        return self.cursor.fetchall()

    def select_person_status(self, user_id):
        self.cursor.execute("""SELECT CurDate, Command FROM shs_tss.roomreg WHERE IdPerson = %s order by CurDate DESC LIMIT 1""", (user_id,))
        return self.cursor.fetchone()

    def close(self):
        self.cursor.close()
        self.conn.close()

class DbAdmin2:

    def __init__(self):
        self.connection = psycopg2.connect(
            database='skud',
            user=constants.POSTGRE_USER,
            password=constants.POSTGRE_PASSWORD,
            host='192.168.254.118',
            port=5432
        )
        self.cursor = self.connection.cursor()

    def start_transaction(self):
        return self.cursor.execute("START TRANSACTION;")

    def commit_transaction(self):
        return self.connection.commit()

    def update(self, status, user):
        self.cursor.execute("UPDATE statuses SET status=%s WHERE user_id=%s", (status, user,))

    def select(self):
        self.cursor.execute("""SELECT user_id, username, status, roschat_id FROM statuses""")
        return self.cursor.fetchall()
    
    def select_cid(self, username):
        self.cursor.execute("""SELECT roschat_id FROM statuses WHERE username=%s""", (username,))
        return self.cursor.fetchone()

    def select2(self, user_id):
        self.cursor.execute("""SELECT observer FROM connections WHERE user_id=%s""", (user_id,))
        return self.cursor.fetchall()

    def list_select(self, observer):
        self.cursor.execute("""SELECT username, roschat_id FROM connections WHERE observer=%s""", (observer,))
        return self.cursor.fetchall()

    def insert(self, observer, user, username, roschat_id):
        try:
            self.cursor.execute("""INSERT INTO connections (observer, user_id, username, roschat_id) VALUES (%s, %s, %s, %s)""", (observer, user, username, roschat_id,))
        except psycopg2.errors.UniqueViolation:
            pass
        
    def insert2(self, user, username, status, roschat_id):
        try:
            self.cursor.execute("""INSERT INTO statuses (user_id, username, status, roschat_id) VALUES (%s, %s, %s, %s)""", (user, username, status, roschat_id,))
        except psycopg2.errors.UniqueViolation:
            pass

    def delete(self, observer, username):
        self.cursor.execute("""DELETE FROM connections WHERE observer=%s and username=%s""", (observer, username,))

    def close(self):
        return self.connection.close()


# grant all on schema public to dbuser ;
# grant all on all sequences in schema public to dbuser ;
# grant select, insert, update, delete on all tables in schema public to dbuser ;