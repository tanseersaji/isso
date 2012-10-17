
import tempfile
import unittest

from werkzeug.test import Client
from werkzeug.wrappers import Response

from isso import Isso, json
from isso.models import Comment


def comment(**kw):
    return Comment.fromjson(json.dumps(kw))


class TestComments(unittest.TestCase):

    get = lambda self, *x, **z: Client(self.app, Response).get(*x, **z)
    put = lambda self, *x, **z: Client(self.app, Response).put(*x, **z)
    post = lambda self, *x, **z: Client(self.app, Response).post(*x, **z)
    delete = lambda self, *x, **z: Client(self.app, Response).delete(*x, **z)

    def setUp(self):
        fd, self.path = tempfile.mkstemp()
        self.app = Isso({'SQLITE': self.path})

    def testGet(self):

        self.post('/comment/path/new', data=json.dumps(comment(text='Lorem ipsum ...')))
        r = self.get('/comment/path/1')
        assert r.status_code == 200

        rv = json.loads(r.data)

        assert rv['id'] == 1
        assert rv['text'] == 'Lorem ipsum ...'

    def testCreate(self):

        rv = self.post('/comment/path/new', data=json.dumps(comment(text='Lorem ipsum ...')))

        assert rv.status_code == 201
        # XXX assert cookie

        c = Comment.fromjson(rv.data)

        assert not c.pending
        assert not c.deleted
        assert c.text == 'Lorem ipsum ...'

    def testCreateAndGetMultiple(self):

        for i in range(100):
            self.post('/comment/path/new', data=json.dumps(comment(text='Spam')))

        r = self.get('/comment/path/')
        assert r.status_code == 200

        rv = json.loads(r.data)
        assert len(rv) == 20
        # XXX limit=100

    def testGetInvalid(self):

        assert self.get('/comment/path/123').status_code == 404
        assert self.get('/comment/path/spam').status_code == 404
        assert self.get('/comment/foo/').status_code == 404

    def testUpdate(self):

        self.post('/comment/path/new', data=json.dumps(comment(text='Lorem ipsum ...')))
        self.put('/comment/path/1', data=json.dumps(comment(
            text='Hello World', author='me', website='http://example.com/')))

        r = self.get('/comment/path/1')
        assert r.status_code == 200

        rv = json.loads(r.data)
        assert rv['text'] == 'Hello World'
        assert rv['author'] == 'me'
        assert rv['website'] == 'http://example.com/'
        assert 'modified' in rv

    def testDelete(self):

        self.post('/comment/path/new', data=json.dumps(comment(text='Lorem ipsum ...')))
        assert self.delete('/comment/path/1').status_code == 200
        assert self.get('/comment/path/1').status_code == 404

    def testDeleteWithReference(self):

        self.post('/comment/path/new', data=json.dumps(comment(text='First')))
        self.post('/comment/path/new', data=json.dumps(comment(text='Second', parent=1)))

        r = self.delete('/comment/path/2')
        assert r.status_code == 200
        assert Comment(**json.loads(r.data)).deleted
