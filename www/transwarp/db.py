#!/usr/bin/python
# coding: utf-8

__author__ = 'Raymond Xiao'

'''
Database operation module.
'''

import time, uuid, functools, threading, logging

# USER DICT
class Dict(dict):
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

# CONNNECT
class _Engine(object):
    def __init__(self, connnect):
        self._connect = connnect
    def connnect(self):
        return self._connect()

# USER_ID
'''
1、uuid1()——基于时间戳
    由MAC地址、当前时间戳、随机数生成。可以保证全球范围内的唯一性，
    但MAC的使用同时带来安全性问题，局域网中可以使用IP来代替MAC。
2、uuid2()——基于分布式计算环境DCE（Python中没有这个函数）
    算法与uuid1相同，不同的是把时间戳的前4位置换为POSIX的UID。
    实际中很少用到该方法。
3、uuid3()——基于名字的MD5散列值
    通过计算名字和命名空间的MD5散列值得到，保证了同一命名空间中不同名字的唯一性，
    和不同命名空间的唯一性，但同一命名空间的同一名字生成相同的uuid。    
4、uuid4()——基于随机数
    由伪随机数得到，有一定的重复概率，该概率可以计算出来。
5、uuid5()——基于名字的SHA-1散列值
    算法与uuid3相同，不同的是使用 Secure Hash Algorithm 1 算法
使用方面：
    首先，Python中没有基于DCE的，所以uuid2可以忽略；
    其次，uuid4存在概率性重复，由无映射性，最好不用；
    再次，若在Global的分布式计算环境下，最好用uuid1；
    最后，若有名字的唯一性要求，最好用uuid3或uuid5。
'''
def next_id(t=None):
    if t is None:
        t = time.time()
    return '%015d%s000' % (int(t * 1000), uuid.uuid4().hex)
    name = "test_name"
    namespace = "test_namespace"

    print uuid.uuid1()  # 带参的方法参见Python Doc
    print uuid.uuid3(namespace, name)
    print uuid.uuid4()
    print uuid.uuid5(namespace, name)

# LOG
def _profiling(start, sql=''): 
    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename='webapp.log',
        filemode='w')
    t = time.time() - start 
    if t > 0.1: 
        logging.warning('[PROFILING] [DB] %s: %s' % (t, sql)) 
    else: 
        logging.info('[PROFILING] [DB] %s: %s' % (t, sql)) 
    
# DBERROR
class DBError(Exception): 
    pass 

class MultiColumnError(DBError): 
    pass 

class _LasyConnection(object):
    def __init__(self): 
        self.connection = None 
 
    def cursor(self): 
        if self.connection is None: 
            connection = engine.connect() 
            logging.info('open connection <%s>...' % hex(id(connection))) 
            self.connection = connection 
        return self.connection.cursor() 
 
    def commit(self): 
        self.connection.commit() 
 
    def rollback(self): 
        self.connection.rollback() 
 
    def cleanup(self): 
        if self.connection: 
            connection = self.connection 
            self.connection = None 
            logging.info('close connection <%s>...' % hex(id(connection))) 
            connection.close() 
 
class _DbCtx(threading.local): 
    ''' 
    Thread local object that holds connection info. 
    ''' 
    def __init__(self): 
        self.connection = None 
        self.transactions = 0 


    def is_init(self): 
        return not self.connection is None 


    def init(self): 
        logging.info('open lazy connection...') 
        self.connection = _LasyConnection() 
        self.transactions = 0 


    def cleanup(self): 
        self.connection.cleanup() 
        self.connection = None 


    def cursor(self): 
        ''' 
        Return cursor 
        ''' 
        return self.connection.cursor() 


# thread-local db context: 
_db_ctx = _DbCtx() 


# global engine object: 
engine = None 


class _Engine(object): 


    def __init__(self, connect): 
        self._connect = connect 


    def connect(self): 
        return self._connect() 


def create_engine(user, password, database, host='127.0.0.1', port=3306, **kw): 
    import mysql.connector 
    global engine 
    if engine is not None: 
        raise DBError('Engine is already initialized.') 
    params = dict(user=user, password=password, database=database, host=host, port=port) 
    defaults = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', autocommit=False) 
    for k, v in defaults.iteritems(): 
        params[k] = kw.pop(k, v) 
    params.update(kw) 
    params['buffered'] = True 
    engine = _Engine(lambda: mysql.connector.connect(**params)) 
    # test connection... 
    logging.info('Init mysql engine <%s> ok.' % hex(id(engine))) 


class _ConnectionCtx(object): 
    ''' 
    _ConnectionCtx object that can open and close connection context. _ConnectionCtx object can be nested and only the most  
    outer connection has effect. 
 
    with connection(): 
        pass 
        with connection(): 
            pass 
    ''' 
    def __enter__(self): 
        global _db_ctx 
        self.should_cleanup = False 
        if not _db_ctx.is_init(): 
            _db_ctx.init() 
            self.should_cleanup = True 
        return self 


    def __exit__(self, exctype, excvalue, traceback): 
        global _db_ctx 
        if self.should_cleanup: 
            _db_ctx.cleanup() 


def connection(): 
    ''' 
    Return _ConnectionCtx object that can be used by 'with' statement: 
 
    with connection(): 
        pass 
    ''' 
    return _ConnectionCtx() 


def with_connection(func): 
    ''' 
    Decorator for reuse connection. 
 
    @with_connection 
    def foo(*args, **kw): 
        f1() 
        f2() 
        f3() 
    ''' 
    @functools.wraps(func) 
    def _wrapper(*args, **kw): 
        with _ConnectionCtx(): 
            return func(*args, **kw) 
    return _wrapper 


class _TransactionCtx(object): 
    ''' 
    _TransactionCtx object that can handle transactions. 
 
    with _TransactionCtx(): 
        pass 
    ''' 


    def __enter__(self): 
        global _db_ctx 
        self.should_close_conn = False 
        if not _db_ctx.is_init(): 
            # needs open a connection first: 
            _db_ctx.init() 
            self.should_close_conn = True 
        _db_ctx.transactions = _db_ctx.transactions + 1 
        logging.info('begin transaction...' if _db_ctx.transactions==1 else 'join current transaction...') 
        return self 


    def __exit__(self, exctype, excvalue, traceback): 
        global _db_ctx 
        _db_ctx.transactions = _db_ctx.transactions - 1 
        try: 
            if _db_ctx.transactions==0: 
                if exctype is None: 
                    self.commit() 
                else: 
                    self.rollback() 
        finally: 
            if self.should_close_conn: 
                _db_ctx.cleanup() 


    def commit(self): 
        global _db_ctx 
        logging.info('commit transaction...') 
        try: 
            _db_ctx.connection.commit() 
            logging.info('commit ok.') 
        except: 
            logging.warning('commit failed. try rollback...') 
            _db_ctx.connection.rollback() 
            logging.warning('rollback ok.') 
            raise 


    def rollback(self): 
        global _db_ctx 
        logging.warning('rollback transaction...') 
        _db_ctx.connection.rollback() 
        logging.info('rollback ok.') 


def transaction(): 
    ''' 
    Create a transaction object so can use with statement: 
 
    with transaction(): 
        pass 
 
    >>> def update_profile(id, name, rollback): 
    ...     u = dict(id=id, name=name, email='%s@test.org' % name, passwd=name, last_modified=time.time()) 
    ...     insert('user', **u) 
    ...     r = update('update user set passwd=? where id=?', name.upper(), id) 
    ...     if rollback: 
    ...         raise StandardError('will cause rollback...') 
    >>> with transaction(): 
    ...     update_profile(900301, 'Python', False) 
    >>> select_one('select * from user where id=?', 900301).name 
    u'Python' 
    >>> with transaction(): 
    ...     update_profile(900302, 'Ruby', True) 
    Traceback (most recent call last): 
      ... 
    StandardError: will cause rollback... 
    >>> select('select * from user where id=?', 900302) 
    [] 
    ''' 
    return _TransactionCtx() 


def with_transaction(func): 
    ''' 
    A decorator that makes function around transaction. 
 
    >>> @with_transaction 
    ... def update_profile(id, name, rollback): 
    ...     u = dict(id=id, name=name, email='%s@test.org' % name, passwd=name, last_modified=time.time()) 
    ...     insert('user', **u) 
    ...     r = update('update user set passwd=? where id=?', name.upper(), id) 
    ...     if rollback: 
    ...         raise StandardError('will cause rollback...') 
    >>> update_profile(8080, 'Julia', False) 
    >>> select_one('select * from user where id=?', 8080).passwd 
    u'JULIA' 
    >>> update_profile(9090, 'Robert', True) 
    Traceback (most recent call last): 
      ... 
    StandardError: will cause rollback... 
    >>> select('select * from user where id=?', 9090) 
    [] 
    ''' 
    @functools.wraps(func) 
    def _wrapper(*args, **kw): 
        _start = time.time() 
        with _TransactionCtx(): 
            return func(*args, **kw) 
        _profiling(_start) 
    return _wrapper 


def _select(sql, first, *args): 
    ' execute select SQL and return unique result or list results.' 
    global _db_ctx 
    cursor = None 
    sql = sql.replace('?', '%s') 
    logging.info('SQL: %s, ARGS: %s' % (sql, args)) 
    try: 
        cursor = _db_ctx.connection.cursor() 
        cursor.execute(sql, args) 
        if cursor.description: 
            names = [x[0] for x in cursor.description] 
        if first: 
            values = cursor.fetchone() 
            if not values: 
                return None 
            return Dict(names, values) 
        return [Dict(names, x) for x in cursor.fetchall()] 
    finally: 
        if cursor: 
            cursor.close() 


@with_connection 
def select_one(sql, *args): 
    ''' 
    Execute select SQL and expected one result.  
    If no result found, return None. 
    If multiple results found, the first one returned. 
 
    >>> u1 = dict(id=100, name='Alice', email='alice@test.org', passwd='ABC-12345', last_modified=time.time()) 
    >>> u2 = dict(id=101, name='Sarah', email='sarah@test.org', passwd='ABC-12345', last_modified=time.time()) 
    >>> insert('user', **u1) 
    1 
    >>> insert('user', **u2) 
    1 
    >>> u = select_one('select * from user where id=?', 100) 
    >>> u.name 
    u'Alice' 
    >>> select_one('select * from user where email=?', 'abc@email.com') 
    >>> u2 = select_one('select * from user where passwd=? order by email', 'ABC-12345') 
    >>> u2.name 
    u'Alice' 
    ''' 
    return _select(sql, True, *args) 


@with_connection 
def select_int(sql, *args): 
    ''' 
    Execute select SQL and expected one int and only one int result.  
 
    >>> n = update('delete from user') 
    >>> u1 = dict(id=96900, name='Ada', email='ada@test.org', passwd='A-12345', last_modified=time.time()) 
    >>> u2 = dict(id=96901, name='Adam', email='adam@test.org', passwd='A-12345', last_modified=time.time()) 
    >>> insert('user', **u1) 
    1 
    >>> insert('user', **u2) 
    1 
    >>> select_int('select count(*) from user') 
    2 
    >>> select_int('select count(*) from user where email=?', 'ada@test.org') 
    1 
    >>> select_int('select count(*) from user where email=?', 'notexist@test.org') 
    0 
    >>> select_int('select id from user where email=?', 'ada@test.org') 
    96900 
    >>> select_int('select id, name from user where email=?', 'ada@test.org') 
    Traceback (most recent call last): 
        ... 
    MultiColumnsError: Expect only one column. 
    ''' 
    d = _select(sql, True, *args) 
    if len(d)!=1: 
        raise MultiColumnsError('Expect only one column.') 
    return d.values()[0] 


@with_connection 
def select(sql, *args): 
    ''' 
    Execute select SQL and return list or empty list if no result. 
 
    >>> u1 = dict(id=200, name='Wall.E', email='wall.e@test.org', passwd='back-to-earth', last_modified=time.time()) 
    >>> u2 = dict(id=201, name='Eva', email='eva@test.org', passwd='back-to-earth', last_modified=time.time()) 
    >>> insert('user', **u1) 
    1 
    >>> insert('user', **u2) 
    1 
    >>> L = select('select * from user where id=?', 900900900) 
    >>> L 
    [] 
    >>> L = select('select * from user where id=?', 200) 
    >>> L[0].email 
    u'wall.e@test.org' 
    >>> L = select('select * from user where passwd=? order by id desc', 'back-to-earth') 
    >>> L[0].name 
    u'Eva' 
    >>> L[1].name 
    u'Wall.E' 
    ''' 
    return _select(sql, False, *args) 


@with_connection 
def _update(sql, *args): 
    global _db_ctx 
    cursor = None 
    sql = sql.replace('?', '%s') 
    logging.info('SQL: %s, ARGS: %s' % (sql, args)) 
    try: 
        cursor = _db_ctx.connection.cursor() 
        cursor.execute(sql, args) 
        r = cursor.rowcount 
        if _db_ctx.transactions==0: 
            # no transaction enviroment: 
            logging.info('auto commit') 
            _db_ctx.connection.commit() 
        return r 
    finally: 
        if cursor: 
            cursor.close() 


def insert(table, **kw): 
    ''' 
    Execute insert SQL. 
 
    >>> u1 = dict(id=2000, name='Bob', email='bob@test.org', passwd='bobobob', last_modified=time.time()) 
    >>> insert('user', **u1) 
    1 
    >>> u2 = select_one('select * from user where id=?', 2000) 
    >>> u2.name 
    u'Bob' 
    >>> insert('user', **u2) 
    Traceback (most recent call last): 
      ... 
    IntegrityError: 1062 (23000): Duplicate entry '2000' for key 'PRIMARY' 
    ''' 
    cols, args = zip(*kw.iteritems()) 
    sql = 'insert into `%s` (%s) values (%s)' % (table, ','.join(['`%s`' % col for col in cols]), ','.join(['?' for i in range(len(cols))])) 
    return _update(sql, *args) 


def update(sql, *args): 
    r''' 
    Execute update SQL. 
 
    >>> u1 = dict(id=1000, name='Michael', email='michael@test.org', passwd='123456', last_modified=time.time()) 
    >>> insert('user', **u1) 
    1 
    >>> u2 = select_one('select * from user where id=?', 1000) 
    >>> u2.email 
    u'michael@test.org' 
    >>> u2.passwd 
    u'123456' 
    >>> update('update user set email=?, passwd=? where id=?', 'michael@example.org', '654321', 1000) 
    1 
    >>> u3 = select_one('select * from user where id=?', 1000) 
    >>> u3.email 
    u'michael@example.org' 
    >>> u3.passwd 
    u'654321' 
    >>> update('update user set passwd=? where id=?', '***', '123\' or id=\'456') 
    0 
    ''' 
    return _update(sql, *args) 


if __name__=='__main__': 
    logging.basicConfig(level=logging.DEBUG) 
    create_engine('www-data', 'www-data', 'test') 
    update('drop table if exists user') 
    update('create table user (id int primary key, name text, email text, passwd text, last_modified real)') 
    import doctest 
    doctest.testmod() 
