import sqlite3
import re


class SQLite():

    def __init__(self, db_name):
        # Error Checks
        if not isinstance(db_name, str):
            raise TypeError("The name of the database should be a string")
        if len(db_name) == 0:
            raise ValueError("The database name should not be empty")

        # Create the connection and the cursor
        self.conn = sqlite3.connect(db_name)
        self.c = self.conn.cursor()

        self.tables = {}

    def __valid_input(self, string):
        '''Private function to validate input'''
        for l in string:
            if l in [';', '(', ')', ]:
                raise ValueError("Forbidden character found on the string '%s'" % string)
        return True

    def __fields_not_primary_key(self, fields):
        ''' Private function to determine if the table have a Primary Key'''
        new_fields = []
        for f in fields:
            if not re.match('.*primary key.*', f.lower()):
                new_fields.append(f.split(" ")[0])
        return new_fields

    def __get_primary_key(self, fields):
        ''' Private function to determine the Primary Key field'''
        for f in fields:
            if re.match('.*primary key.*', f.lower()):
                return f.split(" ")[0]

        raise RuntimeError("No primary key on table")

    def create_table(self, table_name, fields):
        """ Create table"""
        # Error Checks
        if not isinstance(table_name, str):
            raise TypeError("The name of the table on database should be a string")
        if type(fields) is not tuple:
           raise TypeError("The fields should be a tuple ('field_name data_type OPTION', ...)")
        if len(table_name) == 0:
            raise ValueError("The table name should not be empty")
        if len(fields) == 0:
            raise ValueError("You need at least one field to create a table")
        for f in fields:
            self.__valid_input(f)

        try:
            self.tables[table_name] = fields
            sql = '''CREATE TABLE IF NOT EXISTS {tbl} ({flds})'''.format(tbl=table_name,
                                                                         flds=",".join(f for f in fields))
            self.c.execute(sql)

        except Exception as e:
            raise e

    def insert(self, table_name, values):
        """ Insert data into table """
        # Error Checks
        if not isinstance(table_name, str):
            raise TypeError("The name of the table on database should be a string")
        if type(values) is not tuple:
           raise TypeError("The values should be a tuple containing the values to insert")
        if len(table_name) == 0:
            raise ValueError("The table name should not be empty")
        if len(values) == 0:
            raise ValueError("You need at least one value to insert on the table")
        for v in values:
            if isinstance(v, str):
                self.__valid_input(v)

        try:
            fields = self.__fields_not_primary_key(self.tables[table_name])
            sql = '''INSERT INTO {tbl}({flds}) VALUES({vals})'''.format(tbl=table_name,
                                                                      flds=",".join(f for f in fields),
                                                                      vals=",".join("?" for i in range(len(values))))
            self.c.execute(sql, values)
            self.conn.commit()

        except Exception as e:
            raise e

    def get_last_n(self, table_name, n=1):
        """ Get the last value on table """
        # Error Checks
        if not isinstance(table_name, str):
            raise TypeError("The name of the table on database should be a string")
        if not isinstance(n, int):
            raise TypeError("The number of records (n) asked should be an integer")
        if len(table_name) == 0:
            raise ValueError("The table name should not be empty")
        if n <= 0:
            raise ValueError("The number of records should be greater than or equal to 1")

        try:
            sql = '''SELECT * FROM {tbl} ORDER by {pk} DESC LIMIT {num}'''.format(tbl=table_name,
                                                                                  pk=self.__get_primary_key(
                                                                                      self.tables[table_name]),
                                                                                  num=n)
            self.c.execute(sql)
            return self.c.fetchall()
        except Exception as e:
            raise e

    def query(self, query, values=None):
        """ Query """
        # Error Checks
        if not isinstance(query, str):
            raise TypeError("The query should be a string")
        if len(query) == 0:
            raise ValueError("The query can't be empty")
        if values is not None:
            if type(values) is not tuple:
                raise ValueError("Values should be a tuple")

        try:
            if values is None:
                self.c.execute(query)
                return self.c.fetchall()
            else:
                self.c.execute(query, values)
                return self.c.fetchall()

        except Exception as e:
            raise e

    def get_columns_from_table(self, table_name):
        """ Get columns from table """
        # Error Checks
        if not isinstance(table_name, str):
            raise TypeError("The table name should be a string")
        if len(table_name) == 0:
            raise ValueError("The table name can't be empty")
        for v in table_name:
            if isinstance(v, str):
                self.__valid_input(v)

        try:
            sql = "SELECT * from {tbl}".format(tbl=table_name)
            self.c.execute(sql)
            return list(map(lambda x: x[0], self.c.description))

        except Exception as e:
            raise e

    def close(self):
        """ Close connection"""
        try:
            self.conn.close()
        except Exception as e:
            raise e