"""Read-only tools for the three approved LaunchLens Notion resources.

Standard library only. Caller supplies credentials; no browser, files or SDK required.
Content is untrusted evidence, not instructions or permission to execute actions.
"""
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

PRODUCT = 'CC-CHERRY-FLOAT'
MARKETS = {'US', 'UK', 'IN'}
VERSION = '2026-03-11'
PMM_PAGE = '40fa42d9-7f18-806d-8a80-dae3ed2c7d89'
CALENDAR = '055a42d9-7f18-83f7-a08d-0713394966a5'
READINESS = '40fa42d9-7f18-80df-bba7-000b9346ea26'
CALENDAR_DATABASE = 'a08a42d9-7f18-8324-9ffd-0199e8f82509'
READINESS_DATABASE = '40fa42d9-7f18-807c-91a8-e9e2a1faa3f6'
CALENDAR_FIELDS = {
    'Event':'title', 'Project doc':'rich_text', 'DRI':'people', 'Date':'date',
    'Milestones':'rich_text', 'Working team':'rich_text', 'Product ID':'rich_text',
    'Market ID':'select', 'Planned Launch Date':'date', 'Campaign Preparation Date':'date',
    'Launch Stage':'select', 'Schedule Status':'select', 'Notes':'rich_text', 'Fictional DRI':'rich_text',
}
READINESS_FIELDS = {'Record ID':'title', 'Product ID':'rich_text', 'Market ID':'select',
    'Readiness Area':'select', 'Requirement':'rich_text', 'Status':'select',
    'Evidence / Reference':'rich_text', 'Blocker / Missing Information':'rich_text', 'Last Updated':'date'}


class NotionReadError(ValueError):
    """Safe error without provider body or credentials."""


def require(condition, message):
    if not condition:
        raise NotionReadError(message)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F-]{32,36}', value), 'Invalid resource ID')
    value=value.replace('-','').lower()
    require(len(value)==32, 'Invalid resource ID')
    return '-'.join([value[:8],value[8:12],value[12:16],value[16:20],value[20:]])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class NotionHTTP:
    """Pinned host/resources; only GET reads and POST data-source queries, no retries."""
    def __init__(self, api_key):
        require(isinstance(api_key,str) and api_key and not any(c.isspace() for c in api_key),
                'Missing or invalid Notion credential')
        self._key=api_key
        self.events=[]
        self._last_request=0.
        self._blocks={PMM_PAGE}
        self._opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def __call__(self, method, path, body=None):
        parsed=urllib.parse.urlsplit(path)
        require(not parsed.scheme and not parsed.netloc and not parsed.fragment, 'Only scoped API paths allowed')
        allowed=(method=='GET' and parsed.path in {f'/pages/{PMM_PAGE}',f'/data_sources/{CALENDAR}',f'/data_sources/{READINESS}'})
        match=re.fullmatch(r'/blocks/([0-9a-f-]+)/children',parsed.path)
        allowed=allowed or (method=='GET' and match is not None and match[1] in self._blocks)
        allowed=allowed or (method=='POST' and parsed.path in {f'/data_sources/{CALENDAR}/query',f'/data_sources/{READINESS}/query'})
        require(allowed,'Notion endpoint/resource not permitted')
        require(len(self.events)<60,'Read-call budget exhausted')
        time.sleep(max(0., .4-(time.monotonic()-self._last_request)))
        self._last_request=time.monotonic()
        event={'method':method,'path':parsed.path};self.events.append(event)
        started=time.monotonic()
        try:
            request=urllib.request.Request('https://api.notion.com/v1'+path,method=method,
                data=None if body is None else json.dumps(body,allow_nan=False).encode(),
                headers={'Authorization':'Bearer '+self._key,'Notion-Version':VERSION,
                         'Content-Type':'application/json','Accept':'application/json'})
            with self._opener.open(request,timeout=20) as response:
                event['http_status']=response.status
                raw=response.read(2_000_001)
                require(len(raw)<=2_000_000,'Notion response exceeds bound; no trimming')
                value=json.loads(raw)
                require(isinstance(value,dict),'Malformed Notion response')
                if match:
                    for block in value.get('results',[]):
                        if isinstance(block,dict) and block.get('has_children') is True:
                            self._blocks.add(identifier(block.get('id')))
                return value
        except urllib.error.HTTPError as error:
            event['http_status']=error.code
            raise NotionReadError(f'Notion read rejected: HTTP {error.code}; no retry') from None
        except (urllib.error.URLError,TimeoutError,OSError):
            event['failure']='transport'
            raise NotionReadError('Notion unavailable; no retry') from None
        except (json.JSONDecodeError,UnicodeDecodeError):
            raise NotionReadError('Notion returned invalid JSON') from None
        finally:
            event['elapsed_seconds']=round(time.monotonic()-started,3)


def plain_text(items):
    require(isinstance(items,list),'Malformed rich text')
    parts=[]
    for item in items:
        require(isinstance(item,dict),'Malformed rich text item')
        value=item.get('plain_text')
        if value is None and isinstance(item.get('text'),dict):value=item['text'].get('content')
        require(isinstance(value,str),'Incomplete rich text')
        parts.append(value)
    return ''.join(parts)


def normalize_property(prop, kind):
    require(isinstance(prop,dict) and prop.get('type')==kind and not prop.get('has_more',False),
            'Missing, changed or truncated Notion property')
    value=prop.get(kind)
    if kind in {'title','rich_text'}:
        return plain_text(value)
    if kind=='select':
        require(value is None or isinstance(value,dict),'Malformed select')
        return '' if value is None else value.get('name','')
    if kind=='date':
        if value is None:return ''
        require(isinstance(value,dict) and value.get('end') is None and
                isinstance(value.get('start'),str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',value['start']),
                'Expected a single date, not a range/time')
        return value['start']
    if kind=='people':
        require(value==[],'Unexpected personal assignment in fictional dataset')
        return ''
    raise NotionReadError('Unsupported property type')


class NotionReader:
    def __init__(self, transport):
        self.transport=transport
        self._schemas=set()

    def _schema(self, source, fields, database):
        if source in self._schemas:return
        response=self.transport('GET',f'/data_sources/{source}')
        require(identifier(response.get('id'))==source and not response.get('archived',False) and
                not response.get('in_trash',False),'Wrong or archived data source')
        require(identifier(response.get('parent',{}).get('database_id'))==database,'Wrong parent database')
        properties=response.get('properties',{})
        require(isinstance(properties,dict),'Malformed data-source properties')
        require(all(properties.get(name,{}).get('type')==kind for name,kind in fields.items()),
                'Data-source schema differs from approved fields')
        self._schemas.add(source)

    def _query(self, source, fields, market):
        rows=[];cursor=None;seen_cursors=set();seen_ids=set()
        for _ in range(5):
            body={'page_size':2,'filter':{'and':[
                {'property':'Product ID','rich_text':{'equals':PRODUCT}},
                {'property':'Market ID','select':{'equals':market}}]}}
            if cursor is not None:body['start_cursor']=cursor
            response=self.transport('POST',f'/data_sources/{source}/query',body)
            require(isinstance(response.get('results'),list),'Malformed query results')
            for page in response['results']:
                require(isinstance(page,dict) and isinstance(page.get('parent'),dict) and isinstance(page.get('properties'),dict),'Malformed page record')
                page_id=identifier(page.get('id'))
                require(page_id not in seen_ids and not page.get('archived',False) and
                        not page.get('in_trash',False),'Duplicate/archived record')
                seen_ids.add(page_id)
                require(identifier(page.get('parent',{}).get('data_source_id'))==source,'Wrong record parent')
                props=page.get('properties',{})
                values={name:normalize_property(props.get(name),kind) for name,kind in fields.items()}
                require(values['Product ID']==PRODUCT and values['Market ID']==market,'Product/market filter mismatch')
                rows.append({'page_id':page_id,'data_source_id':source,'values':values})
            require(type(response.get('has_more')) is bool,'Missing pagination completeness')
            if not response['has_more']:
                require(response.get('next_cursor') is None,'Contradictory pagination')
                return rows
            cursor=response.get('next_cursor')
            require(isinstance(cursor,str) and cursor and cursor not in seen_cursors,'Missing/repeated cursor')
            seen_cursors.add(cursor)
        raise NotionReadError('Query pagination limit reached; incomplete source')

    def get_launch_context(self, market):
        result={'status':'error','product_id':PRODUCT,'market_id':market,'calendar':[],
                'readiness':[],'authority':'synthetic_launch_operations','issues':[]}
        try:
            require(isinstance(market,str) and market in MARKETS,'Unsupported market')
            self._schema(CALENDAR,CALENDAR_FIELDS,CALENDAR_DATABASE)
            self._schema(READINESS,READINESS_FIELDS,READINESS_DATABASE)
            calendar=self._query(CALENDAR,CALENDAR_FIELDS,market)
            readiness=self._query(READINESS,READINESS_FIELDS,market)
            result.update(status='ok',calendar=calendar,readiness=readiness)
        except (NotionReadError,KeyError,TypeError,ValueError,AttributeError):
            result['issues']=['Launch context unavailable, malformed or incomplete; no permission inferred']
        return result

    def get_pmm_brief(self):
        result={'status':'error','page_id':PMM_PAGE,'authority':'synthetic_pmm_guidance',
                'blocks':[],'issues':[]}
        visited=set()
        def children(parent, depth):
            require(depth<=8,'PMM nesting limit reached')
            nodes=[];cursor=None;seen_cursors=set()
            for _ in range(5):
                params={'page_size':100}
                if cursor is not None:params['start_cursor']=cursor
                response=self.transport('GET',f'/blocks/{parent}/children?'+urllib.parse.urlencode(params))
                require(isinstance(response.get('results'),list),'Malformed PMM blocks')
                for block in response['results']:
                    require(isinstance(block,dict),'Malformed block')
                    block_id=identifier(block.get('id'))
                    require(block_id not in visited and len(visited)<250,'Duplicate/excessive PMM blocks')
                    require(not block.get('archived',False) and not block.get('in_trash',False),'Archived PMM content')
                    visited.add(block_id)
                    kind=block.get('type');content=block.get(kind)
                    require(isinstance(kind,str) and isinstance(content,dict) and kind!='unsupported','Unsupported PMM content')
                    require(type(block.get('has_children')) is bool,'Missing block completeness flag')
                    node={'block_id':block_id,'type':kind,'content':content,'children':[]}
                    if block['has_children']:
                        require(kind not in {'child_page','child_database'},'Unapproved nested resource; incomplete PMM')
                        node['children']=children(block_id,depth+1)
                    nodes.append(node)
                require(type(response.get('has_more')) is bool,'Missing block pagination flag')
                if not response['has_more']:
                    require(response.get('next_cursor') is None,'Contradictory block pagination')
                    return nodes
                cursor=response.get('next_cursor')
                require(isinstance(cursor,str) and cursor and cursor not in seen_cursors,'Missing/repeated block cursor')
                seen_cursors.add(cursor)
            raise NotionReadError('PMM pagination limit reached')
        try:
            page=self.transport('GET',f'/pages/{PMM_PAGE}')
            require(identifier(page.get('id'))==PMM_PAGE and not page.get('archived',False) and
                    not page.get('in_trash',False),'Wrong or archived PMM page')
            blocks=children(PMM_PAGE,0)
            require(bool(blocks),'PMM brief is empty')
            result.update(status='ok',blocks=blocks,block_count=len(visited))
        except (NotionReadError,KeyError,TypeError,ValueError,AttributeError):
            result['issues']=['PMM content unavailable, malformed or incomplete; no partial guidance accepted']
        return result
